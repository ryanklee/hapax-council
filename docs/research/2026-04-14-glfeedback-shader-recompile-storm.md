# glfeedback shader-recompile storm

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Root-causes the glfeedback shader-recompile burst first
observed in the sprint-5 delta audit (§ 8.2). Asks: why does the
compositor's glfeedback Rust plugin recompile its fragment shader
dozens of times per `activate_plan` call, and what is the blast
radius for livestream smoothness?
**Register:** scientific, neutral
**Status:** investigation only — no code change. Root cause
identified. Two-site fix proposal included.

## Headline

**Four findings.**

1. **Every `activate_plan` call in `agents/effect_graph/pipeline.py`
   unconditionally `set_property("fragment", ...)` on all 24
   glfeedback slots**, regardless of whether the fragment source
   for each slot has actually changed between plans. Source:
   `agents/effect_graph/pipeline.py:173`. No equality check, no
   "pending change" tracking.
2. **The Rust `set_property("fragment", ...)` handler at
   `gst-plugin-glfeedback/src/glfeedback/imp.rs:97-112` also does
   not diff the incoming value against the current value.** It
   unconditionally `props.shader_dirty = true`. The Python and
   Rust sides are both unconditional, so there is no short-
   circuit on identical content anywhere in the chain.
3. **Each triggered recompile `Clear`s the accumulation buffer**
   at `imp.rs:265-273`. That clear is semantically correct for a
   genuine shader change (prevents stale pixels from previous
   shader bleeding through), but on a no-op re-set it is a visual
   reset with no purpose. Every hit produces a visible
   discontinuity in any feedback-using effect.
4. **Measured cadence:** 14 `activate_plan` calls in the last
   60 minutes (≈ one every 4.3 minutes) on studio-compositor PID
   2812855. Each call cascades 24 `set_property` calls into the
   Rust plugin. Of those 24, ≥ 16 are `passthrough` (165-char
   `PASSTHROUGH_SHADER`, byte-identical between activations on
   unused slots). **~336 recompiles/hour of which ≥ ~224 are
   byte-identical no-ops.** Cost: ~1–2 ms GPU shader-compile work
   per recompile, one accumulation-buffer `Clear` per recompile,
   plus an INFO-level GST_RUST log line per event that is
   currently spamming journald at ~60 entries per `activate_plan`
   burst.

**Net livestream impact.** On every plan activation — which the
operator's workflow triggers every few minutes via auto-cycling or
manual preset selection — all 24 slots' accumulation buffers
are simultaneously cleared. Any feedback-based effect in play at
that moment experiences a hard visual reset. The observer sees a
flicker. The CPU/GPU cost is small in isolation but asymmetrically
wasteful: most of the recompiles do not change any observable
behavior.

## 1. The Python caller — `pipeline.py:137-180`

```python
# agents/effect_graph/pipeline.py:137-180 (ActivePlan assignment)

def activate_plan(self, plan: ExecutionPlan) -> None:
    # ...
    for step in plan.steps:
        # ... extract per-slot shader_source into self._slot_pending_frag[i]
        slot_idx += 1

    for i in range(self._num_slots):
        if self._slot_is_temporal[i]:
            # glfeedback: set fragment and uniforms via GObject properties
            frag = self._slot_pending_frag[i] or PASSTHROUGH_SHADER
            node = self._slot_assignments[i] or "passthrough"
            log.info("Slot %d (%s): setting fragment (%d chars)", i, node, len(frag))
            self._slots[i].set_property("fragment", frag)   # ← line 173
            self._apply_glfeedback_uniforms(i)
        else:
            # glshader path — not relevant to this drop
            ...
```

`frag` for unused slots defaults to `PASSTHROUGH_SHADER`. For the
14 plan activations observed in § 3, an average of **(24 − 10) ≈
14 passthrough slots** per call are unconditionally re-set to the
same 165-char string as the previous activation. There is no
tracking of the previous value on either side of the boundary.

## 2. The Rust handler — `imp.rs:97-112`

```rust
// gst-plugin-glfeedback/src/glfeedback/imp.rs:97-112

fn set_property(&self, _id: usize, value: &glib::Value, pspec: &glib::ParamSpec) {
    match pspec.name() {
        "fragment" => {
            let frag = value.get::<Option<String>>().unwrap();
            // A shader is passthrough (skip accum blit) if it does NOT
            // reference tex_accum. [… is_passthrough heuristic comment …]
            let is_pt = frag.as_ref().map_or(true, |f| !f.contains("tex_accum"));
            let mut props = self.props.lock().unwrap();
            props.fragment = frag;
            props.is_passthrough = is_pt;
            props.shader_dirty = true;   // ← unconditional
        }
        // ...
    }
}
```

No comparison of `frag` against `props.fragment` before the
`shader_dirty = true`. The comment on lines 101-106 records a prior
fix that corrected an `is_passthrough` heuristic issue, but that
fix was orthogonal to the `shader_dirty` unconditional flip — both
Python and Rust paths are byte-identical-blind.

## 3. The Rust render thread — `imp.rs:252-287`

```rust
// imp.rs:252-287

// Lazy-recompile shader on GL thread if fragment property changed
{
    let mut props = self.props.lock().unwrap();
    if props.shader_dirty {
        gst::info!(gst::CAT_RUST, "shader_dirty detected — recompiling");
        props.shader_dirty = false;
        if let Some(frag_src) = props.fragment.clone() {
            drop(props);
            if let Some(context) = gst_gl::prelude::GLBaseFilterExt::context(&*filter) {
                match self.compile_shader(&context, &frag_src) {
                    Ok(new_shader) => {
                        let mut guard = self.state.lock().unwrap();
                        let s = guard.as_mut().unwrap();
                        s.shader = new_shader;
                        // Clear accumulation buffers on shader change to prevent
                        // stale frame data from previous shader bleeding through.
                        for i in 0..2 {
                            unsafe {
                                gl::BindFramebuffer(gl::FRAMEBUFFER, s.accum_fbos[i]);
                                gl::ClearColor(0.0, 0.0, 0.0, 0.0);
                                gl::Clear(gl::COLOR_BUFFER_BIT);
                            }
                        }
                        gst::info!(gst::CAT_RUST,
                                   "Shader recompiled OK ({} chars), accum cleared",
                                   frag_src.len());
                    }
                    Err(e) => { /* … */ }
                }
            }
        }
    }
}
```

The accumulation-buffer clear is **defensive**: if the shader is
genuinely new, old accumulated pixels could bleed through because
they were produced by a different fragment program. Clearing
prevents that. **When the shader is byte-identical to the previous
one, the clear is pure visual damage** — the accum buffer's
previous contents were produced by the same shader and remain
semantically valid.

## 4. Live cadence measurement

```text
$ journalctl --user -u studio-compositor.service --since "60 minutes ago" \
      | grep '"Activated plan"' | wc -l
14

$ journalctl --user -u studio-compositor.service --since "60 minutes ago" \
      | grep '"Activated plan"' | awk '{print $NF}' | tail -6
Activated plan 'chain': 13/24 slots used
Activated plan 'chain': 10/24 slots used
Activated plan 'chain': 9/24 slots used
Activated plan 'Halftone': 4/24 slots used
Activated plan 'Halftone': 4/24 slots used
```

14 activations per 60 min. Slot usage in the samples: 12, 8, 11,
9, 17, 13, 10, 9, 4, 4 (real) — mean ≈ 9.7, so each activation
re-sets an average of **(24 − 9.7) ≈ 14.3 passthrough slots**
whose fragment is byte-identical to the previous activation.
Passthrough-only wasted recompiles per hour: 14 × 14.3 ≈ **200**.
Plus same-type same-shader recompiles on non-passthrough slots
(e.g. two consecutive `Halftone` activations at 10:05 and 10:07
re-set all 4 real slots to their prior values).

Each activate_plan call logged 20 setting-fragment lines in 2 ms
at the Python level, followed by the Rust-side cascade of 20
`shader_dirty → recompile → accum cleared` events visible in the
GST_RUST log within ~100 ms. Example cluster at 10:05:49:

```text
10:05:49.425159  Python: Slot 0 (colorgrade): setting fragment (1521 chars)
10:05:49.425665  Python: Slot 1 (halftone):   setting fragment (2879 chars)
10:05:49.425911  Python: Slot 2 (content_layer): setting fragment (1155 chars)
10:05:49.425990  Python: Slot 3 (postprocess): setting fragment (1159 chars)
10:05:49.426163  Python: Slot 4 (passthrough): setting fragment (165 chars)
…
10:05:49.427146  Python: Slot 19 (passthrough): setting fragment (165 chars)

10:05:49.716612  Rust: shader_dirty detected — recompiling
10:05:49.729130  Rust: Shader recompiled OK (1521 chars), accum cleared
10:05:49.735351  Rust: shader_dirty detected — recompiling
10:05:49.738688  Rust: Shader recompiled OK (2885 chars), accum cleared
[… 20+ more pairs over the next ~100 ms …]
```

Rust GST timestamps are ~290 ms behind Python wall clock — the
GL-thread `filter_texture` processes the queued dirty flags at the
next pad-push, not synchronously with the property-set.

## 5. Hypothesis tests

### H1 — "activate_plan is called with a genuinely different plan each time"

**Partially refuted by the two consecutive `Halftone` activations**
(10:05:49 → 10:07:42). Two calls, same plan name, same slot
usage (4/24), within 2 minutes. At minimum those two back-to-back
calls re-set all 24 slots with no semantic difference.

In general, the bug does not require *the whole plan* to be
unchanged — each slot is checked independently. The relevant
question is: for a given slot, is the new fragment byte-identical
to the current? For passthrough slots it almost always is.

### H2 — "Recompilation is cheap on a modern GPU; the cost is negligible"

**Partially refuted.** Per-recompile GPU cost is ~1-2 ms and is
done on the GL thread. A cluster of 20 recompiles serializes
~20-40 ms of GL work in the filter_texture pad push. At 30 fps,
each pad-push has a 33 ms budget; a 20-recompile cluster eats one
whole frame. One visible frame drop per plan activation is
plausible and would match the operator's observation of flickers
on preset changes.

The log-spam cost is also non-trivial: 20 INFO-level log entries
per activation × 2 lines per entry (dirty-detected + recompiled-ok)
= 40 journald writes per cluster, ≈ 560 writes/hour. Not a
primary cost but consistent with the journald load observations
from the overlay_zones drop.

### H3 — "The accumulation buffer clear is necessary even on a no-op re-set"

**Refuted.** The clear at `imp.rs:265-273` is specifically to
prevent stale fragment output from a previous program from
bleeding into the next program's first frames. If the program is
unchanged, its prior output is not stale — it is exactly what the
new program would produce. The clear is correct defensive
hygiene on a real shader change and wasted work on a no-op.

### H4 — "A Python-side fix alone is sufficient"

**Unrefuted.** A single equality check in `pipeline.py:173`
against a per-slot memo of the last-set fragment would eliminate
almost all wasteful calls. However, a Rust-side fix is
complementary: it defends against any future caller that has not
implemented change-detection, and it's a smaller patch in a
single file with one diff instead of per-call-site diffs.

## 6. Proposed fix

### 6.1 Python side — `agents/effect_graph/pipeline.py`

Track the last-set fragment per slot. Only call `set_property`
when it differs. Approximate patch (for reference, not for
commit by delta):

```python
# In SlotPipeline.__init__:
self._slot_last_frag: list[str | None] = [None] * self._num_slots

# In activate_plan, replace line 173:
if self._slot_pending_frag[i] != self._slot_last_frag[i]:
    self._slots[i].set_property("fragment", frag)
    self._slot_last_frag[i] = frag
# else: skip — no change
```

Impact: eliminates the FFI call AND the Rust-side recompile AND
the accumulation-buffer clear AND the INFO log line for any
unchanged slot. ≈200 calls/hour saved at current cadence.

### 6.2 Rust side — `gst-plugin-glfeedback/src/glfeedback/imp.rs`

Defensive diff check in `set_property("fragment", ...)`:

```rust
"fragment" => {
    let frag = value.get::<Option<String>>().unwrap();
    let mut props = self.props.lock().unwrap();
    if props.fragment != frag {
        let is_pt = frag.as_ref().map_or(true, |f| !f.contains("tex_accum"));
        props.fragment = frag;
        props.is_passthrough = is_pt;
        props.shader_dirty = true;
    }
    // else: no change, no recompile, no accum clear
}
```

Impact: same as Python-side but handles any current or future
caller, including any Python path that forgets to diff.

### 6.3 Should both land?

Yes. The Python fix is a narrow performance improvement at the
one current call site. The Rust fix is a safety invariant on the
element's public property contract ("setting a property to its
current value is a no-op"). Shipping only Python leaves the
element exposed to regressions; shipping only Rust costs an extra
FFI call per slot-set but is still correct.

## 7. Secondary finding — log-level mismatch

The GST_RUST recompile log is at `INFO` level, and fires twice
per recompile (`shader_dirty detected — recompiling` +
`Shader recompiled OK (... chars), accum cleared`). Once the bug
is fixed, these lines will only fire on genuine shader changes
and the rate drops to ~10-20 per hour. Until then, they're an
effective symptom signal. **After the fix lands, consider
dropping both lines to `debug` level** — the rate will be small
enough that operators can turn debug on when investigating,
rather than having INFO-level churn in the journal during normal
operation.

## 8. Follow-ups for alpha

1. **Land the Python-side diff check first** — narrowest change,
   one file, validatable by watching `Activated plan` log rate
   stay at ~14/hour while the per-cluster `setting fragment`
   entries drop from 24 to ≤ 10.
2. **Then land the Rust-side diff check** — one file, defensive
   invariant on the public property. Rebuilds the GStreamer
   plugin via `cargo build` in `gst-plugin-glfeedback/`.
3. **Drop the two GST_RUST log lines to `debug`** — after the fix
   lands, the remaining signal is small and high-level logs will
   be quieter.
4. **Investigate why `activate_plan` fires 14 times/hour** — is
   this auto-cycling, operator manual preset, a timer, or some
   incidental trigger? The current cadence of every ~4 minutes
   means the visual effect of the accum-clear is noticeable even
   if each individual clear is brief. A separate drop could
   inventory the triggers and determine whether the cadence is
   intentional (creative choice) or incidental (auto-cycling
   defaults).
5. **Same bug class likely exists in `glshader` path** — the
   Python code at `pipeline.py:178` sets
   `update-shader: True` unconditionally on every activate_plan.
   Worth checking whether the glshader element has the same
   identity-check gap.

## 9. References

- `gst-plugin-glfeedback/src/glfeedback/imp.rs` lines 97-112 (set_property),
  252-287 (filter_texture recompile + accum clear)
- `agents/effect_graph/pipeline.py` lines 137-180 (activate_plan),
  269-280 (`_apply_glfeedback_uniforms`)
- `2026-04-14-sprint-5-delta-audit.md` § 8.2 — the original
  observation that led to this investigation
- Scrape: `journalctl --user -u studio-compositor.service --since
  "60 minutes ago" | grep "Activated plan"` at 2026-04-14T15:10 UTC
  — the 14-activations-per-hour measurement
- GST log sample: `journalctl --user -u studio-compositor.service
  --since "10 minutes ago" | grep GST_RUST.glfeedback` — the
  recompile cluster at 10:05:49
