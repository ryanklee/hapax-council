"""Studio Compositor — GStreamer pipeline that tiles camera feeds into a single 1080p output.

Reads N camera feeds via v4l2src, decodes MJPEG on GPU (nvjpegdec),
composites via cudacompositor, encodes with nvh264enc, and outputs to
/dev/video42 (v4l2loopback).

Usage:
    uv run python -m agents.studio_compositor --config PATH
    uv run python -m agents.studio_compositor --default-config
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any

import gi
import yaml
from pydantic import BaseModel, Field

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".cache" / "hapax-compositor"
STATUS_FILE = CACHE_DIR / "status.json"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "hapax-compositor" / "config.yaml"

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080


class CameraSpec(BaseModel):
    """A single camera source."""

    role: str  # e.g. "brio-operator", "c920-hardware", "c920-room", "c920-aux", "ir"
    device: str  # /dev/v4l/by-id/... or /dev/videoN
    width: int = 1280
    height: int = 720
    input_format: str = "mjpeg"  # "mjpeg" or "raw"
    pixel_format: str | None = None  # e.g. "gray" for IR sensor
    hero: bool = False  # hero cam gets 2x tile size


class CompositorConfig(BaseModel):
    """Full compositor configuration."""

    cameras: list[CameraSpec] = Field(default_factory=list)
    output_device: str = "/dev/video42"
    output_width: int = OUTPUT_WIDTH
    output_height: int = OUTPUT_HEIGHT
    framerate: int = 30
    bitrate: int = 8_000_000  # nvh264enc bitrate in bits/sec
    status_interval_s: float = 5.0


# ---------------------------------------------------------------------------
# Default config for the current studio
# ---------------------------------------------------------------------------

_DEFAULT_CAMERAS: list[dict[str, Any]] = [
    {
        "role": "brio-operator",
        "device": "/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0",
        "width": 1920,
        "height": 1080,
        "input_format": "mjpeg",
        "hero": True,
    },
    {
        "role": "c920-hardware",
        "device": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
    {
        "role": "c920-room",
        "device": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_86B6B75F-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
    {
        "role": "c920-aux",
        "device": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_7B88C71F-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
]


def _default_config() -> CompositorConfig:
    return CompositorConfig(cameras=[CameraSpec(**c) for c in _DEFAULT_CAMERAS])


def load_config(path: Path | None = None) -> CompositorConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text()) or {}
            return CompositorConfig(**data)
        except Exception as exc:
            log.warning("Failed to load config from %s: %s — using defaults", config_path, exc)
    return _default_config()


# ---------------------------------------------------------------------------
# Tile layout
# ---------------------------------------------------------------------------


class TileRect(BaseModel):
    x: int
    y: int
    w: int
    h: int


def compute_tile_layout(
    cameras: list[CameraSpec],
    canvas_w: int = OUTPUT_WIDTH,
    canvas_h: int = OUTPUT_HEIGHT,
) -> dict[str, TileRect]:
    """Compute tile positions for each camera on the output canvas.

    Hero camera (if any) gets a 2x tile in the top-left.
    Remaining cameras fill in a grid around it.
    """
    n = len(cameras)
    if n == 0:
        return {}

    heroes = [c for c in cameras if c.hero]
    others = [c for c in cameras if not c.hero]

    layout: dict[str, TileRect] = {}

    if heroes and len(others) >= 1:
        # Hero gets top-left 2x2 block (half canvas width, half canvas height)
        hero = heroes[0]
        hero_w = canvas_w // 2
        hero_h = canvas_h // 2

        layout[hero.role] = TileRect(x=0, y=0, w=hero_w, h=hero_h)

        # Right quadrant: 2-column grid filling same height as hero
        right_count = min(len(others), 4)
        right_cams = others[:right_count]
        remaining = others[right_count:]

        right_cols = 2
        right_rows = (right_count + right_cols - 1) // right_cols
        tile_w = (canvas_w - hero_w) // right_cols
        tile_h = hero_h // max(right_rows, 1)

        for i, cam in enumerate(right_cams):
            col = i % right_cols
            row = i // right_cols
            layout[cam.role] = TileRect(
                x=hero_w + col * tile_w,
                y=row * tile_h,
                w=tile_w,
                h=tile_h,
            )

        # Bottom row: remaining cameras (future BRIOs etc.)
        if remaining:
            bottom_w = canvas_w // len(remaining)
            for i, cam in enumerate(remaining):
                layout[cam.role] = TileRect(
                    x=i * bottom_w,
                    y=hero_h,
                    w=bottom_w,
                    h=canvas_h - hero_h,
                )
    else:
        # No hero: simple grid
        import math

        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        tile_w = canvas_w // cols
        tile_h = canvas_h // rows
        for i, cam in enumerate(cameras):
            layout[cam.role] = TileRect(
                x=(i % cols) * tile_w,
                y=(i // cols) * tile_h,
                w=tile_w,
                h=tile_h,
            )

    return layout


# ---------------------------------------------------------------------------
# GStreamer pipeline builder
# ---------------------------------------------------------------------------


class StudioCompositor:
    """Manages the GStreamer compositing pipeline."""

    def __init__(self, config: CompositorConfig) -> None:
        self.config = config
        self.pipeline: Gst.Pipeline | None = None
        self.loop: GLib.MainLoop | None = None
        self._running = False

    def _build_pipeline(self) -> Gst.Pipeline:
        """Build the full GStreamer pipeline."""
        Gst.init(None)

        pipeline = Gst.Pipeline.new("studio-compositor")
        layout = compute_tile_layout(
            self.config.cameras, self.config.output_width, self.config.output_height
        )

        # Create compositor
        compositor = Gst.ElementFactory.make("cudacompositor", "compositor")
        if compositor is None:
            raise RuntimeError(
                "cudacompositor plugin not available — install gst-plugins-bad with CUDA"
            )
        pipeline.add(compositor)

        fps = self.config.framerate

        # Add camera sources
        for cam in self.config.cameras:
            tile = layout.get(cam.role)
            if tile is None:
                log.warning("No tile for camera %s, skipping", cam.role)
                continue

            self._add_camera_branch(pipeline, compositor, cam, tile, fps)

        # Output chain: compositor → nvh264enc → v4l2sink
        capsfilter = Gst.ElementFactory.make("capsfilter", "comp-caps")
        caps = Gst.Caps.from_string(
            f"video/x-raw(memory:CUDAMemory),width={self.config.output_width},"
            f"height={self.config.output_height},framerate={fps}/1"
        )
        capsfilter.set_property("caps", caps)

        encoder = Gst.ElementFactory.make("nvh264enc", "encoder")
        encoder.set_property("bitrate", self.config.bitrate // 1000)  # nvh264enc uses kbit/s
        encoder.set_property("preset", 4)  # low-latency HP
        encoder.set_property("rc-mode", 2)  # CBR

        parse = Gst.ElementFactory.make("h264parse", "parse")

        # v4l2sink needs raw or encoded; v4l2loopback with exclusive_caps=1
        # needs caps negotiation. Use decode back to raw for v4l2sink compatibility.
        decoder = Gst.ElementFactory.make("avdec_h264", "v4l2-decode")
        convert = Gst.ElementFactory.make("videoconvert", "v4l2-convert")

        sink_caps = Gst.ElementFactory.make("capsfilter", "sink-caps")
        sink_caps.set_property(
            "caps",
            Gst.Caps.from_string(
                f"video/x-raw,format=YUY2,width={self.config.output_width},"
                f"height={self.config.output_height},framerate={fps}/1"
            ),
        )

        sink = Gst.ElementFactory.make("v4l2sink", "output")
        sink.set_property("device", self.config.output_device)

        for el in [capsfilter, encoder, parse, decoder, convert, sink_caps, sink]:
            if el is None:
                raise RuntimeError("Failed to create GStreamer element")
            pipeline.add(el)

        # Link: compositor → caps → encoder → parse → decoder → convert → sink_caps → v4l2sink
        if not compositor.link(capsfilter):
            raise RuntimeError("Failed to link compositor → capsfilter")
        if not capsfilter.link(encoder):
            raise RuntimeError("Failed to link capsfilter → encoder")
        if not encoder.link(parse):
            raise RuntimeError("Failed to link encoder → parse")
        if not parse.link(decoder):
            raise RuntimeError("Failed to link parse → decoder")
        if not decoder.link(convert):
            raise RuntimeError("Failed to link decoder → convert")
        if not convert.link(sink_caps):
            raise RuntimeError("Failed to link convert → sink_caps")
        if not sink_caps.link(sink):
            raise RuntimeError("Failed to link sink_caps → v4l2sink")

        return pipeline

    def _add_camera_branch(
        self,
        pipeline: Gst.Pipeline,
        compositor: Gst.Element,
        cam: CameraSpec,
        tile: TileRect,
        fps: int,
    ) -> None:
        """Add a single camera source branch to the pipeline."""
        role = cam.role.replace("-", "_")

        # Source
        src = Gst.ElementFactory.make("v4l2src", f"src_{role}")
        src.set_property("device", cam.device)

        if cam.input_format == "mjpeg":
            # MJPEG path: v4l2src → capsfilter(mjpeg) → jpegdec → cudaupload → cudaconvert
            # Note: nvjpegdec cannot decode UVC webcam Motion-JPEG, so we use
            # software jpegdec and upload the decoded frames to CUDA.
            src_caps = Gst.ElementFactory.make("capsfilter", f"srccaps_{role}")
            src_caps.set_property(
                "caps",
                Gst.Caps.from_string(
                    f"image/jpeg,width={cam.width},height={cam.height},framerate={fps}/1"
                ),
            )
            decoder = Gst.ElementFactory.make("jpegdec", f"dec_{role}")
            upload = Gst.ElementFactory.make("cudaupload", f"upload_{role}")
            convert = Gst.ElementFactory.make("cudaconvert", f"convert_{role}")
            for el in [src, src_caps, decoder, upload, convert]:
                pipeline.add(el)
            src.link(src_caps)
            src_caps.link(decoder)
            decoder.link(upload)
            upload.link(convert)
            last = convert
        else:
            # Raw path (e.g. IR gray): v4l2src → videoconvert → cudaupload
            src_caps = Gst.ElementFactory.make("capsfilter", f"srccaps_{role}")
            pix_fmt = cam.pixel_format or "GRAY8"
            src_caps.set_property(
                "caps",
                Gst.Caps.from_string(
                    f"video/x-raw,format={pix_fmt},width={cam.width},height={cam.height},"
                    f"framerate={fps}/1"
                ),
            )
            convert = Gst.ElementFactory.make("videoconvert", f"rawconv_{role}")
            upload = Gst.ElementFactory.make("cudaupload", f"upload_{role}")
            for el in [src, src_caps, convert, upload]:
                pipeline.add(el)
            src.link(src_caps)
            src_caps.link(convert)
            convert.link(upload)
            last = upload

        # Scale to tile size before compositor
        scale = Gst.ElementFactory.make("cudascale", f"scale_{role}")
        scale_caps = Gst.ElementFactory.make("capsfilter", f"scalecaps_{role}")
        scale_caps.set_property(
            "caps",
            Gst.Caps.from_string(f"video/x-raw(memory:CUDAMemory),width={tile.w},height={tile.h}"),
        )

        for el in [scale, scale_caps]:
            pipeline.add(el)

        last.link(scale)
        scale.link(scale_caps)

        # Request a sink pad on compositor and set position
        pad_template = compositor.get_pad_template("sink_%u")
        pad = compositor.request_pad(pad_template, None, None)
        if pad is None:
            raise RuntimeError(f"Failed to get compositor sink pad for {cam.role}")

        pad.set_property("xpos", tile.x)
        pad.set_property("ypos", tile.y)
        pad.set_property("width", tile.w)
        pad.set_property("height", tile.h)

        # Link scale_caps src pad to compositor sink pad
        src_pad = scale_caps.get_static_pad("src")
        if src_pad.link(pad) != Gst.PadLinkReturn.OK:
            raise RuntimeError(f"Failed to link {cam.role} to compositor")

    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message) -> bool:
        """Handle pipeline bus messages."""
        t = message.type
        if t == Gst.MessageType.EOS:
            log.info("Pipeline EOS")
            self.stop()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            src_name = message.src.get_name() if message.src else "unknown"
            log.error("Pipeline error from %s: %s (debug: %s)", src_name, err.message, debug)
            self.stop()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            log.warning("Pipeline warning: %s (debug: %s)", err.message, debug)
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old, new, _ = message.parse_state_changed()
                log.debug("Pipeline state: %s → %s", old.value_nick, new.value_nick)
        return True

    def _write_status(self, state: str, cameras: dict[str, str] | None = None) -> None:
        """Write compositor status to cache file."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        status = {
            "state": state,
            "pid": __import__("os").getpid(),
            "cameras": cameras or {},
            "output_device": self.config.output_device,
            "resolution": f"{self.config.output_width}x{self.config.output_height}",
            "timestamp": time.time(),
        }
        tmp = STATUS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(status, indent=2))
        tmp.rename(STATUS_FILE)

    def start(self) -> None:
        """Build and start the pipeline."""
        log.info("Building compositor pipeline with %d cameras", len(self.config.cameras))
        self.pipeline = self._build_pipeline()

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        cam_status = {c.role: "starting" for c in self.config.cameras}
        self._write_status("starting", cam_status)

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self._write_status("error")
            raise RuntimeError("Failed to start pipeline")

        log.info("Pipeline started — output on %s", self.config.output_device)
        cam_status = {c.role: "active" for c in self.config.cameras}
        self._write_status("running", cam_status)

        self._running = True
        self.loop = GLib.MainLoop()

        # Handle signals
        def _shutdown(signum: int, frame: Any) -> None:
            log.info("Signal %d received, shutting down", signum)
            self.stop()

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the pipeline cleanly."""
        if not self._running:
            return
        self._running = False
        log.info("Stopping compositor pipeline")

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        if self.loop and self.loop.is_running():
            self.loop.quit()

        self._write_status("stopped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Studio Compositor — tiled camera output")
    parser.add_argument("--config", type=Path, help="Config YAML path")
    parser.add_argument(
        "--default-config", action="store_true", help="Print default config and exit"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    from shared.log_setup import configure_logging

    configure_logging(agent="studio-compositor", level="DEBUG" if args.verbose else None)

    if args.default_config:
        cfg = _default_config()
        print(yaml.dump(json.loads(cfg.model_dump_json()), default_flow_style=False))
        sys.exit(0)

    cfg = load_config(path=args.config)
    log.info(
        "Config: %d cameras, output=%s, %dx%d@%dfps",
        len(cfg.cameras),
        cfg.output_device,
        cfg.output_width,
        cfg.output_height,
        cfg.framerate,
    )

    compositor = StudioCompositor(cfg)
    compositor.start()


if __name__ == "__main__":
    main()
