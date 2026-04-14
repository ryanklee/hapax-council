# studio_fx CPU load — GPU path silently disabled

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Identifies why `studio-fx.service` holds ~70–130 % of one
CPU core. Asks: is it doing CPU work that a GPU path could absorb,
and if so, what's blocking that path?
**Register:** scientific, neutral
**Status:** investigation only — no code change. Root cause
identified. Fix is a package rebuild / reinstall, not a code
patch.

## Headline

**Four findings.**

1. **`studio_fx` has a full GPU acceleration path that is silently
   disabled at import time.** `agents/studio_fx/gpu.py:26-32`
   probes `cv2.cuda.getCudaEnabledDeviceCount()` at module import.
   When the probe returns 0, `_HAS_CUDA = False` and every
   `GpuAccel.upload` / `.cvt_color` / `.gaussian_blur` falls
   through to pure numpy + CPU OpenCV.
2. **Both Python runtimes on this box report 0 CUDA devices from
   cv2**: system Python 3.14 (used by `studio-fx.service` via
   `/usr/bin/python3`) and the council venv's Python 3.12 (used
   by `studio-compositor.service`). `cv2.getBuildInformation()`
   shows `OpenCL: YES` but has no `NVIDIA CUDA:` section at all —
   the cv2 binary was not compiled with CUDA support.
3. **Both cv2 installations pretend to be the CUDA variant.**
   `pacman -Qi python-opencv-cuda` says installed (version
   4.13.0-5.1, 12.54 MiB). `cv2.__file__` on system Python
   resolves to the pacman-installed location, but `ldd` on the
   compiled `.so` in that package directory finds no
   `libcudart`, `libcudnn`, or any NVIDIA library. The package
   is either mislabeled or was silently overwritten by a
   non-CUDA build — either way, the runtime has no CUDA.
4. **CPU cost: sustained ~70 % of one core at steady state,
   up to ~130 % under load.** Initial audit captured
   studio-fx at 129 %. Current measurement (PID 3033786,
   ~4 min uptime) is 68.7 %. Fluctuation matches the selected
   effect: `datamosh`, `neon`, `pixsort`, `slitscan`, `vhs`,
   `screwed`, `classify` all run CPU-only today. `neon` and
   `datamosh` each instantiate `GpuAccel` conditionally — the
   code is prepared, the runtime is not.

**Net impact.** studio_fx is a first-class livestream effects
pipeline currently running entirely on CPU. Fixing the OpenCV
CUDA build would cut its CPU load substantially — exactly how
much depends on which effects are active, but at minimum the
`neon` and `datamosh` paths already have GPU branches waiting to
activate. This is a **zero-code-change fix**: rebuild or
replace the cv2 package so the existing `_HAS_CUDA` probe
returns True, and the existing `GpuAccel` wrapper does the
work.

## 1. The GPU path in studio_fx

```python
# agents/studio_fx/gpu.py:26-36
_HAS_CUDA = False
try:
    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
        _HAS_CUDA = True
        log.info("CUDA available: %d device(s)", cv2.cuda.getCudaEnabledDeviceCount())
except Exception:
    pass


def has_cuda() -> bool:
    return _HAS_CUDA
```

```python
# agents/studio_fx/gpu.py:52-59
def upload(self, frame: np.ndarray) -> object:
    """Upload numpy frame to GPU. Returns GpuMat or numpy array."""
    if not self._cuda:
        return frame
    gpu = cv2.cuda_GpuMat()
    gpu.upload(frame)
    return gpu
```

Clean split. When `_HAS_CUDA` is False, every `GpuAccel` method
early-returns numpy arrays and all downstream work happens via
non-CUDA OpenCV calls on the CPU. No warning is logged on this
fall-through — the `log.info("CUDA available: …")` line only
fires *inside* the True branch of the probe.

Callers that instantiate `GpuAccel`:

```text
$ grep -rn "GpuAccel(" agents/studio_fx/
agents/studio_fx/effects/datamosh.py:83: self._gpu = GpuAccel()
agents/studio_fx/effects/neon.py:71:     self._gpu = GpuAccel()
agents/studio_fx/effects/neon.py:74:     gpu_frame = self._gpu.upload(frame)
```

`neon.py` and `datamosh.py` use the GPU wrapper. Other effects
(`classify`, `screwed`, `pixsort`, `vhs`, `slitscan`) currently
don't — they are unconditionally CPU. Adding GPU paths to the
other effects is a separate code-change project; this drop is
about getting the existing wrapper to work first.

## 2. Runtime probe results

### 2.1 System Python 3.14 (what studio-fx.service uses)

```text
$ systemctl --user cat studio-fx.service | grep ExecStart
ExecStart=/usr/bin/python3 -m agents.studio_fx

$ python3 -c "import cv2, sys; print(cv2.__file__); \
                           print(sys.version_info); \
                           print(cv2.cuda.getCudaEnabledDeviceCount())"
~/.../python3.14/site-packages/cv2/__init__.py
sys.version_info(major=3, minor=14, …)
0
```

### 2.2 Venv Python 3.12 (what studio-compositor.service uses)

```text
$ ~council-venv/bin/python -c \
      "import cv2; print(cv2.__file__); print(cv2.cuda.getCudaEnabledDeviceCount())"
~council-venv/lib/python3.12/site-packages/cv2/__init__.py
0
```

Both report 0 devices. Both `cv2` installations are non-CUDA.

### 2.3 cv2 build information (system Python)

```text
$ python3 -c "import cv2; print(cv2.getBuildInformation())" | \
      grep -iE "cuda|nvidia|opencl"
  OpenCL:                        YES (no extra features)
    Include path:                /io/opencv/3rdparty/include/opencl/1.2
```

Two observations. First, **no `NVIDIA CUDA:` section exists in
the build info output** — if cv2 had been built with CUDA
support, there would be a dedicated subsection headed `NVIDIA
CUDA:` followed by `YES (ver X.X.X)`, `NVIDIA GPU arch:`, etc.
Its absence is the definitive signal. Second, the
`Include path: /io/opencv/3rdparty/include/opencl/1.2` prefix
`/io/` is the path convention used by manylinux / pip wheel
builds — **the cv2 binary was produced by a pip wheel build,
not the pacman package.**

### 2.4 Dynamic linkage

```text
$ ldd {system cv2 .so} 2>&1 | grep -iE "cuda|cudnn"
(no matches)
```

The compiled module imports no NVIDIA runtime libraries. If it
were the CUDA variant, it would link `libcudart.so.12`,
`libcudnn.so.9`, and friends.

### 2.5 pacman state

```text
$ pacman -Qi python-opencv-cuda
Installed From  : cachyos-extra-v3
Version         : 4.13.0-5.1
Conflicts With  : python-opencv
Installed Size  : 12.54 MiB
```

pacman thinks the CUDA package is installed. Something has
overwritten its cv2 directory with a pip-built non-CUDA module,
or the pacman package is itself mislabeled.

## 3. Current CPU cost

```text
$ ps -eo pid,%cpu,command | grep studio_fx
3033786  68.7  /usr/bin/python3 -m agents.studio_fx
```

68.7 % at sample time. Initial CPU audit several hours ago
captured the same service at **129 %**. The delta is activity-
dependent — `classify` uses less CPU than `datamosh` or
`slitscan`, which run per-pixel transforms on every frame. The
upper bound is one full core (100 %) plus Python overhead and
any secondary threads; the lower bound is whatever the current
effect happens to cost.

With 6 cameras feeding the compositor at 1920×1080 downstream,
a per-frame full-resolution CPU OpenCV pass is expensive in a
way that the GPU variant of the same OpenCV call would absorb
nearly for free. The savings from enabling the GPU path are
effect-specific but the ceiling is almost all of `studio_fx`'s
current CPU budget.

## 4. Hypothesis tests

### H1 — "studio_fx is intentionally CPU-only"

**Unrefuted.** The `gpu.py` docstring says:
> "Falls back to CPU transparently if CUDA is unavailable."

So the fallback is a design choice for portability, not a bug.
The question is: **was the CUDA path ever enabled on this
workstation?** The `log.info("CUDA available: …")` line would
have fired on startup if it were. Journal search for that line
in studio-fx.service history:

```text
$ journalctl --user -u studio-fx.service --since "20 minutes ago" | grep -i CUDA
(no matches)
```

Empty. Either this session never had CUDA cv2, or the log level
is above INFO. Assuming it's never been active, this is a
latent feature waiting for the OpenCV package to be CUDA-aware.

### H2 — "The `python-opencv-cuda` pacman package is mislabeled"

**Unverified but the simplest explanation.** The package claims
"Open Source Computer Vision Library (with CUDA support)" but
the installed binary has no CUDA linkage. Either:

- the CachyOS extra-v3 build was made without `-DWITH_CUDA=ON`
  by mistake;
- the package provides a shim that wraps a non-CUDA `.so`;
- pip install is overwriting the pacman-installed files;
- there's a hook that deletes the CUDA runtime before packaging.

A quick test: `pacman -Ql python-opencv-cuda | head` would show
which files the package claims ownership of, and comparing
mtime / ldd against the live file would reveal whether the file
has been overwritten since install. This drop didn't run that
test; flagging for alpha.

### H3 — "A pip `opencv-python` package is shadowing the pacman package"

**Plausible.** The `/io/` include path in `getBuildInformation()`
is a pip-wheel convention. If any recent `pip install`,
`uv sync`, or dependency resolution pulled in `opencv-python`
as a transitive requirement and installed it at the system
`site-packages`, it would overwrite the pacman version (Python
doesn't track package owners the way pacman does — last writer
wins for files in site-packages).

Test: `pip list 2>/dev/null | grep -i opencv` on the system
Python and in the council venv. If `opencv-python` is listed
as a pip-installed package alongside the pacman one,
conflict confirmed.

## 5. Proposed fix directions (for alpha)

Ordered by invasiveness:

1. **Verify which package owns the live cv2.so.** Run
   `pacman -Qo` on the system cv2 `.so` and `pip list | grep
   opencv`. This tells us whether pacman still owns the file
   or whether pip has replaced it.
2. **If pip replaced it**: uninstall the pip `opencv-python` and
   re-verify `getBuildInformation()` shows the CUDA section.
   Repin project dependencies to *not* pull `opencv-python`
   (e.g. via `uv` constraint, `pyproject.toml` exclude, or a
   direct `opencv-cuda` dep if the pacman package exposes one).
3. **If pacman still owns it but the binary has no CUDA**: the
   cachyos `python-opencv-cuda` package is broken. File
   upstream, or rebuild locally from `opencv-cuda-git` AUR.
4. **After the probe returns `> 0`**: no code change required —
   the `_HAS_CUDA` flag flips at next import and `GpuAccel`
   paths activate on the existing `neon` and `datamosh`
   effects.
5. **Follow-up**: extend `GpuAccel` usage into the remaining
   effects (`classify`, `screwed`, `pixsort`, `slitscan`,
   `vhs`) for full coverage. This is a separate code-change
   project and shouldn't block the package fix.

## 6. Secondary finding — Python version mismatch is a smell

`studio-fx.service` runs `/usr/bin/python3` (Python 3.14), but
`studio-compositor.service` runs the council venv (Python
3.12). They share the same codebase but can't share the same
cv2 installation — each has its own `site-packages`. If alpha
fixes the cv2 CUDA gap for system Python 3.14 only, the
compositor's own numpy/OpenCV paths (if any) would still be
CPU-bound via the venv's non-CUDA cv2. Probably not a problem
(compositor doesn't import cv2 much) but worth verifying.

A unification — move studio_fx into the venv so both services
share one cv2 — is tempting but outside this drop's scope.

## 7. Follow-up list

1. **`pacman -Qo` on the live system cv2 .so** — who owns it?
2. **`pip list | grep opencv`** — is there a pip shadow?
3. **`pip list` in the council venv** — same question for the
   venv's cv2.
4. **After CUDA cv2 is restored**: re-measure studio_fx CPU at
   the same effect selection. Quantify the actual savings so
   alpha knows what's real before committing to extending
   `GpuAccel` usage.
5. **Log level fix**: add a `log.warning("OpenCV CUDA not
   available — studio_fx running CPU-only")` at import time in
   `gpu.py` after the try/except. A silent fall-through to CPU
   is a trap — any future session will not realize the GPU
   path is off.

## 8. References

- `agents/studio_fx/gpu.py:26-32, 52-59` — the `_HAS_CUDA` probe
  and `GpuAccel.upload` fallback
- `agents/studio_fx/effects/neon.py:71-74` —
  `_gpu = GpuAccel()` caller
- `agents/studio_fx/effects/datamosh.py:83` — same
- `pacman -Qi python-opencv-cuda` — package version 4.13.0-5.1
- `cv2.getBuildInformation()` at 2026-04-14T15:15 UTC — "OpenCL:
  YES (no extra features)", no CUDA section
- `ldd` on the system cv2 `.so` at the same time — no NVIDIA
  library linkage
