"""Tests for camera classification metadata (task #135).

``CameraSpec`` carries semantic metadata (``semantic_role``,
``subject_ontology``, ``angle``, ``operator_visible``,
``ambient_priority``) so Hapax (director, reverie, daimonion) can reason
about what each camera points at. The compositor publishes the full
classification dict to ``/dev/shm/hapax-compositor/camera-classifications.json``
so downstream perception (``PerceptualField.camera_classifications``)
can read it.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from agents.studio_compositor.config import _DEFAULT_CAMERAS, _default_config
from agents.studio_compositor.models import CameraSpec
from shared.perceptual_field import PerceptualField


class TestCameraSpecClassificationFields:
    def test_defaults_leave_classification_unspecified(self) -> None:
        cam = CameraSpec(role="test", device="/dev/video0")
        assert cam.semantic_role == "unspecified"
        assert cam.subject_ontology == []
        assert cam.angle == "unspecified"
        assert cam.operator_visible is False
        assert cam.ambient_priority == 5

    def test_explicit_classification(self) -> None:
        cam = CameraSpec(
            role="brio-operator",
            device="/dev/video0",
            semantic_role="operator-face",
            subject_ontology=["person"],
            angle="front",
            operator_visible=True,
            ambient_priority=7,
        )
        assert cam.semantic_role == "operator-face"
        assert cam.subject_ontology == ["person"]
        assert cam.angle == "front"
        assert cam.operator_visible is True
        assert cam.ambient_priority == 7

    def test_subject_ontology_independent_across_instances(self) -> None:
        """Default factory must not share the list across instances."""
        a = CameraSpec(role="a", device="/dev/video0")
        b = CameraSpec(role="b", device="/dev/video1")
        a.subject_ontology.append("person")
        assert b.subject_ontology == []


class TestDefaultLayoutClassifications:
    """The 6 production cameras must all carry non-default metadata."""

    _EXPECTED_SEMANTIC_ROLES = {
        "brio-operator": "operator-face",
        "c920-desk": "operator-hands",
        "c920-room": "room-wide",
        "c920-overhead": "operator-desk-topdown",
        "brio-room": "outboard-gear",
        "brio-synths": "turntables",
    }

    def test_all_six_cameras_carry_classification(self) -> None:
        assert len(_DEFAULT_CAMERAS) == 6
        cfg = _default_config()
        assert len(cfg.cameras) == 6
        for cam in cfg.cameras:
            # Every production camera must have a concrete semantic_role
            # (not the "unspecified" default), and a non-empty ontology.
            assert cam.semantic_role != "unspecified", f"{cam.role} missing semantic_role"
            assert cam.subject_ontology, f"{cam.role} missing subject_ontology"
            assert cam.angle != "unspecified", f"{cam.role} missing angle"

    def test_semantic_roles_match_spec(self) -> None:
        cfg = _default_config()
        by_role = {cam.role: cam for cam in cfg.cameras}
        for role, expected_semantic in self._EXPECTED_SEMANTIC_ROLES.items():
            assert by_role[role].semantic_role == expected_semantic

    def test_operator_visible_cameras(self) -> None:
        """Only operator-face and room-wide see the operator."""
        cfg = _default_config()
        by_role = {cam.role: cam for cam in cfg.cameras}
        assert by_role["brio-operator"].operator_visible is True
        assert by_role["c920-room"].operator_visible is True
        # All others must not expose the operator's face.
        for role in ("c920-desk", "c920-overhead", "brio-room", "brio-synths"):
            assert by_role[role].operator_visible is False, f"{role} wrongly operator-visible"

    def test_ambient_priority_in_range(self) -> None:
        cfg = _default_config()
        for cam in cfg.cameras:
            assert 0 <= cam.ambient_priority <= 10, f"{cam.role} priority out of range"

    def test_room_wide_has_highest_ambient_priority(self) -> None:
        """The wide room shot is the most natural ambient cut (spec: 8)."""
        cfg = _default_config()
        by_role = {cam.role: cam for cam in cfg.cameras}
        assert by_role["c920-room"].ambient_priority == 8
        # All others have a lower ambient_priority.
        max_other = max(cam.ambient_priority for cam in cfg.cameras if cam.role != "c920-room")
        assert max_other < 8


class TestClassificationPublish:
    """``StudioCompositor.publish_camera_classifications`` writes a
    valid, roundtrip-readable JSON dict to /dev/shm under tmp+rename."""

    def _make_compositor(self, tmp_path: Path) -> object:
        # Import locally so the module import doesn't happen at collection.
        from agents.studio_compositor.compositor import StudioCompositor
        from agents.studio_compositor.models import CompositorConfig

        # Two cameras, one with a full classification and one left at
        # defaults — publication must include both.
        cfg = CompositorConfig(
            cameras=[
                CameraSpec(
                    role="brio-operator",
                    device="/dev/video0",
                    semantic_role="operator-face",
                    subject_ontology=["person"],
                    angle="front",
                    operator_visible=True,
                    ambient_priority=7,
                ),
                CameraSpec(role="unnamed", device="/dev/video1"),
            ]
        )

        # Patch SNAPSHOT_DIR on both the module and inside the bound name
        # used by publish_camera_classifications. Avoid touching /dev/shm
        # on the host by writing into tmp_path.
        with patch("agents.studio_compositor.compositor.SNAPSHOT_DIR", tmp_path):
            comp = StudioCompositor.__new__(StudioCompositor)
            # Minimal state for publish_camera_classifications — avoids
            # the full __init__ which wires GStreamer / budget trackers.
            comp.config = cfg
            classifications = comp.publish_camera_classifications()
        return classifications, tmp_path / "camera-classifications.json"

    def test_publish_writes_valid_json(self, tmp_path: Path) -> None:
        classifications, target = self._make_compositor(tmp_path)

        assert target.exists()
        on_disk = json.loads(target.read_text())

        # Both cameras appear.
        assert set(on_disk.keys()) == {"brio-operator", "unnamed"}
        assert on_disk == classifications

    def test_publish_payload_shape(self, tmp_path: Path) -> None:
        classifications, _ = self._make_compositor(tmp_path)

        brio = classifications["brio-operator"]
        assert brio["semantic_role"] == "operator-face"
        assert brio["subject_ontology"] == ["person"]
        assert brio["angle"] == "front"
        assert brio["operator_visible"] is True
        assert brio["ambient_priority"] == 7

        unnamed = classifications["unnamed"]
        assert unnamed["semantic_role"] == "unspecified"
        assert unnamed["subject_ontology"] == []
        assert unnamed["angle"] == "unspecified"
        assert unnamed["operator_visible"] is False
        assert unnamed["ambient_priority"] == 5

    def test_publish_atomic_no_partial_file(self, tmp_path: Path) -> None:
        """The ``.tmp`` shadow must not survive a successful rename."""
        _, target = self._make_compositor(tmp_path)
        assert target.exists()
        assert not target.with_suffix(".tmp").exists()


class TestPerceptualFieldRoundtrip:
    def test_default_empty_dict(self) -> None:
        field = PerceptualField()
        assert field.camera_classifications == {}

    def test_accepts_dict(self) -> None:
        payload = {
            "brio-operator": {
                "semantic_role": "operator-face",
                "subject_ontology": ["person"],
                "angle": "front",
                "operator_visible": True,
                "ambient_priority": 7,
            }
        }
        field = PerceptualField(camera_classifications=payload)
        assert field.camera_classifications == payload

    def test_model_dump_roundtrip(self) -> None:
        payload = {
            "c920-overhead": {
                "semantic_role": "operator-desk-topdown",
                "subject_ontology": ["hands", "mpc", "desk"],
                "angle": "top-down",
                "operator_visible": False,
                "ambient_priority": 6,
            }
        }
        field = PerceptualField(camera_classifications=payload)
        dumped = field.model_dump()
        reconstructed = PerceptualField.model_validate(dumped)
        assert reconstructed.camera_classifications == payload

    def test_build_perceptual_field_reads_shm(self, tmp_path: Path) -> None:
        """``build_perceptual_field`` picks up the published dict."""
        import shared.perceptual_field as pf

        shm_path = tmp_path / "camera-classifications.json"
        payload = {
            "brio-operator": {
                "semantic_role": "operator-face",
                "subject_ontology": ["person"],
                "angle": "front",
                "operator_visible": True,
                "ambient_priority": 7,
            }
        }
        shm_path.write_text(json.dumps(payload))

        with patch.object(pf, "_CAMERA_CLASSIFICATIONS", shm_path):
            field = pf.build_perceptual_field()
        assert field.camera_classifications == payload

    def test_build_perceptual_field_missing_file(self, tmp_path: Path) -> None:
        """A missing SHM file yields an empty dict, not a crash."""
        import shared.perceptual_field as pf

        missing = tmp_path / "does-not-exist.json"
        with patch.object(pf, "_CAMERA_CLASSIFICATIONS", missing):
            field = pf.build_perceptual_field()
        assert field.camera_classifications == {}
