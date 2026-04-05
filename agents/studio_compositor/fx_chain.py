"""Inline GPU effects chain and per-frame tick callback."""

from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)


def build_inline_fx_chain(
    compositor: Any, pipeline: Any, pre_fx_tee: Any, output_tee: Any, fps: int
) -> bool:
    """Build GPU effects chain with switchable camera input.

    Pipeline: input-selector → queue → videoconvert → capsfilter(RGBA) → glupload
      → glcolorconvert → [SlotPipeline: 24 glfeedback slots]
      → glcolorconvert → gldownload → videoconvert → output_tee

    Input sources: tiled composite (default) + individual cameras.
    """
    Gst = compositor._Gst

    # Input selector: switch between tiled composite and individual cameras
    input_sel = Gst.ElementFactory.make("input-selector", "fx-input-selector")
    input_sel.set_property("sync-streams", False)
    pipeline.add(input_sel)

    queue = Gst.ElementFactory.make("queue", "queue-fx")
    queue.set_property("leaky", 2)
    queue.set_property("max-size-buffers", 1)

    convert_rgba = Gst.ElementFactory.make("videoconvert", "fx-convert-rgba")
    rgba_caps = Gst.ElementFactory.make("capsfilter", "fx-rgba-caps")
    rgba_caps.set_property("caps", Gst.Caps.from_string("video/x-raw,format=RGBA"))

    glupload = Gst.ElementFactory.make("glupload", "fx-glupload")
    glcolorconvert_in = Gst.ElementFactory.make("glcolorconvert", "fx-glcc-in")

    from agents.effect_graph.pipeline import SlotPipeline

    registry = compositor._graph_runtime._registry if compositor._graph_runtime else None
    compositor._slot_pipeline = SlotPipeline(registry, num_slots=24)

    glcolorconvert_out = Gst.ElementFactory.make("glcolorconvert", "fx-glcc-out")
    gldownload = Gst.ElementFactory.make("gldownload", "fx-gldownload")
    fx_convert = Gst.ElementFactory.make("videoconvert", "fx-out-convert")

    required = [
        queue,
        convert_rgba,
        rgba_caps,
        glupload,
        glcolorconvert_in,
        glcolorconvert_out,
        gldownload,
        fx_convert,
    ]
    for el in required:
        if el is None:
            log.error("Failed to create required FX element — effects disabled")
            return False

    for el in required:
        pipeline.add(el)

    queue.link(convert_rgba)
    convert_rgba.link(rgba_caps)
    rgba_caps.link(glupload)
    glupload.link(glcolorconvert_in)

    compositor._slot_pipeline.build_chain(pipeline, Gst, glcolorconvert_in, glcolorconvert_out)

    glcolorconvert_out.link(gldownload)
    gldownload.link(fx_convert)
    fx_convert.link(output_tee)

    # Wire input-selector → queue
    input_sel.link(queue)

    # Block RECONFIGURE events from propagating downstream when switching sources.
    # Without this, v4l2sink tries to re-set its format and errors with "device busy".
    def _drop_reconfigure(pad: Any, info: Any) -> Any:
        event = info.get_event()
        if event and event.type == Gst.EventType.RECONFIGURE:
            return Gst.PadProbeReturn.DROP
        return Gst.PadProbeReturn.OK

    input_sel.get_static_pad("src").add_probe(
        Gst.PadProbeType.EVENT_DOWNSTREAM, _drop_reconfigure
    )

    # Pad 0: tiled composite (default source)
    live_pad = input_sel.request_pad(input_sel.get_pad_template("sink_%u"), None, None)
    tee_pad = pre_fx_tee.request_pad(pre_fx_tee.get_pad_template("src_%u"), None, None)
    tee_pad.link(live_pad)
    input_sel.set_property("active-pad", live_pad)

    # Store selector and pad map for runtime source switching
    compositor._fx_input_selector = input_sel
    compositor._fx_input_pads = {"live": live_pad}
    compositor._fx_active_source = "live"
    compositor._fx_camera_branch: list[Any] = []  # elements to tear down on switch
    compositor._fx_switching = False

    log.info(
        "FX chain: %d shader slots, input-selector with tiled composite",
        compositor._slot_pipeline.num_slots,
    )
    return True


def switch_fx_source(compositor: Any, source: str) -> bool:
    """Switch FX chain input to a different camera or back to tiled composite.

    Uses IDLE pad probe to safely modify the pipeline while PLAYING.
    Creates camera branch on-demand (lazy), tears down old one.
    """
    if not hasattr(compositor, "_fx_input_selector"):
        return False
    if source == getattr(compositor, "_fx_active_source", "live"):
        return True  # already active
    if getattr(compositor, "_fx_switching", False):
        return False  # switch in progress

    Gst = compositor._Gst
    input_sel = compositor._fx_input_selector
    pipeline = compositor.pipeline

    if source == "live":
        # Switch back to tiled composite — just set active pad
        live_pad = compositor._fx_input_pads.get("live")
        if live_pad is None:
            return False
        input_sel.set_property("active-pad", live_pad)
        _teardown_camera_branch(compositor, Gst)
        compositor._fx_active_source = "live"
        log.info("FX source: switched to live (tiled composite)")
        return True

    # Switch to individual camera — need to create branch on-demand
    role = source.replace("-", "_")
    cam_tee = pipeline.get_by_name(f"tee_{role}")
    if cam_tee is None:
        log.warning("FX source: camera tee for %s not found", source)
        return False

    compositor._fx_switching = True

    # Use IDLE probe on input-selector src pad for safe modification
    src_pad = input_sel.get_static_pad("src")

    def _probe_callback(pad: Any, info: Any) -> Any:
        try:
            # Tear down previous camera branch if any
            _teardown_camera_branch(compositor, Gst)

            # Build new branch: queue → videoconvert → videoscale → capsfilter
            # Must match tiled composite caps exactly (BGRA, output res, pipeline fps)
            out_w = compositor.config.output_width
            out_h = compositor.config.output_height
            fps = compositor.config.framerate
            q = Gst.ElementFactory.make("queue", "fxsrc-q")
            q.set_property("leaky", 2)
            q.set_property("max-size-buffers", 1)
            convert = Gst.ElementFactory.make("videoconvert", "fxsrc-convert")
            scale = Gst.ElementFactory.make("videoscale", "fxsrc-scale")
            caps = Gst.ElementFactory.make("capsfilter", "fxsrc-caps")
            caps.set_property(
                "caps",
                Gst.Caps.from_string(
                    f"video/x-raw,format=BGRA,width={out_w},height={out_h},framerate={fps}/1"
                ),
            )

            elements = [q, convert, scale, caps]
            for el in elements:
                pipeline.add(el)
            q.link(convert)
            convert.link(caps)

            # Sync state with parent (transitions NULL→PLAYING)
            for el in elements:
                el.sync_state_with_parent()

            # Link camera tee → queue
            tee_pad = cam_tee.request_pad(cam_tee.get_pad_template("src_%u"), None, None)
            q_sink = q.get_static_pad("sink")
            tee_pad.link(q_sink)

            # Link caps → new input-selector pad
            sel_pad = input_sel.request_pad(input_sel.get_pad_template("sink_%u"), None, None)
            caps.link_pads("src", input_sel, sel_pad.get_name())

            # Switch active pad
            input_sel.set_property("active-pad", sel_pad)

            # Store for teardown
            compositor._fx_camera_branch = elements
            compositor._fx_camera_tee_pad = tee_pad
            compositor._fx_camera_sel_pad = sel_pad
            compositor._fx_active_source = source
            compositor._fx_switching = False

            log.info("FX source: switched to %s (lazy branch created)", source)
        except Exception:
            log.exception("FX source switch failed")
            compositor._fx_switching = False

        return Gst.PadProbeReturn.REMOVE

    src_pad.add_probe(Gst.PadProbeType.IDLE, _probe_callback)
    return True


def _teardown_camera_branch(compositor: Any, Gst: Any) -> None:
    """Remove the previous camera-specific FX source branch."""
    elements = getattr(compositor, "_fx_camera_branch", [])
    if not elements:
        return

    pipeline = compositor.pipeline

    # Unlink camera tee pad
    tee_pad = getattr(compositor, "_fx_camera_tee_pad", None)
    if tee_pad is not None:
        peer = tee_pad.get_peer()
        if peer is not None:
            tee_pad.unlink(peer)

    # Release input-selector pad
    sel_pad = getattr(compositor, "_fx_camera_sel_pad", None)
    if sel_pad is not None:
        compositor._fx_input_selector.release_request_pad(sel_pad)

    # Stop and remove elements
    for el in reversed(elements):
        el.set_state(Gst.State.NULL)
        pipeline.remove(el)

    compositor._fx_camera_branch = []
    compositor._fx_camera_tee_pad = None
    compositor._fx_camera_sel_pad = None


def fx_tick_callback(compositor: Any) -> bool:
    """GLib timeout: update graph shader uniforms at ~30fps."""
    if not compositor._running:
        return False
    if not hasattr(compositor, "_slot_pipeline") or compositor._slot_pipeline is None:
        return False

    from .fx_tick import tick_governance, tick_modulator, tick_slot_pipeline

    if not hasattr(compositor, "_fx_monotonic_start"):
        compositor._fx_monotonic_start = time.monotonic()
    t = time.monotonic() - compositor._fx_monotonic_start

    with compositor._overlay_state._lock:
        energy = compositor._overlay_state._data.audio_energy_rms
    beat = min(energy * 4.0, 1.0)
    if not hasattr(compositor, "_fx_beat_smooth"):
        compositor._fx_beat_smooth = 0.0
    compositor._fx_beat_smooth = max(beat, compositor._fx_beat_smooth * 0.85)
    b = compositor._fx_beat_smooth

    tick_governance(compositor, t)
    tick_modulator(compositor, t, energy, b)
    tick_slot_pipeline(compositor, t)

    return True
