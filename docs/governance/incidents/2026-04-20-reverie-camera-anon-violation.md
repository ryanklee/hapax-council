---
date: 2026-04-20
severity: T0 (constitutional axiom violation — interpersonal_transparency)
reporter: operator
handler: delta
status: fixed (commit 65d0a8bd9)
follow-ons: open (treat Reverie as full HOMAGE ward)
---

# Reverie Camera → Visual Surface Anon Violation

## What happened

Operator observed an image of their child rendered by the Reverie visual
surface (`/dev/shm/hapax-visual/frame.jpg`). Reverie's content_layer
was compositing a camera frame that included the child's face.

## Root cause

`agents/reverie/_content_capabilities.py::ContentCapabilityRouter.activate_camera()`
reads camera JPEGs from `/dev/shm/hapax-compositor/{brio,c920}-*.jpg`
and converts them directly to RGBA for Reverie's content_layer protocol.
This bypassed `agents/studio_compositor/face_obscure_integration.py`,
which pixelates faces on the livestream egress tee but was never wired
at the reverie read point.

Reverie is a separate consumer of the compositor camera feeds — it
pulls raw JPEG snapshots via filesystem, not through the face-obscure
gated tee that guards RTMP/HLS/V4L2 egress.

## Fix

Commit `65d0a8bd9`:

- `activate_camera` now routes the loaded PIL frame through
  `obscure_frame_for_camera(bgr_ndarray, camera_role)` before writing
  to `/dev/shm/hapax-imagination/sources/camera-{role}/`.
- Fail-CLOSED: any exception drops the frame entirely rather than leak
  a raw one. The helper itself fails closed to a full-frame Gruvbox
  mask on detector failure; the outer except catches conversion/import
  failures that would otherwise bypass the mask.
- Emergency kill switch `HAPAX_REVERIE_DISABLE_CAMERAS=1` disables the
  camera path entirely (set on the systemd unit if the obscure quality
  is ever insufficient).

## Containment

1. `hapax-imagination.service` + `hapax-imagination-loop.service`
   stopped immediately on incident report.
2. Leaked frames purged: `/dev/shm/hapax-visual/frame.jpg` +
   `/dev/shm/hapax-imagination/sources/camera-*/frame.rgba` +
   manifests.
3. Services restarted only after fix commit deployed.

## Follow-ons (not gated on this incident)

1. **Treat Reverie as a full HOMAGE ward.** Operator directive:
   "Reverie should probably also be subject to the same composite
   effect methods that guarantee anonymity to studio guests and me."
   The current fix obscures camera inputs; a ward-level integration
   would apply the full anti-identification invariant set to Reverie's
   own output regardless of input, providing defense-in-depth for any
   future bypass.
2. **Audit every other filesystem reader of /dev/shm/hapax-compositor/
   camera JPEGs.** Any consumer that reads raw camera snapshots and
   emits them elsewhere must go through the same obscure pipeline.
   Known readers: `director_loop` (LLM vision), `vision_observer`,
   `scripts/calibrate-contact-mic.py` (operator tool, acceptable
   pre-stream), `hapax_daimonion/enrollment.py` (face enrollment —
   MUST NOT obscure the frame it uses, so keep raw-read but audit that
   the result stays in-process).

## Governance

Axiom violated: `interpersonal_transparency` (weight 88).

The consent gate in `shared/governance/consent.py` governs capabilities
that need an active consent contract; the face-obscure pipeline is the
visual-privacy enforcement layer on top of that. This incident reveals
a third locus — content_layer inputs to the visual surface — that was
not previously covered by either the consent gate (no capability
annotated `consent_required`) or the face-obscure tee (filesystem read,
not livestream egress). The fix closes the gap for Reverie specifically;
the follow-on audit closes any remaining gaps.
