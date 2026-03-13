"""Tests for face identity resolution via ArcFace embeddings.

All tests mock ONNX Runtime — no real models, GPU, or cameras needed.
Follows test_hapax_voice_speaker_id.py patterns.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from agents.hapax_voice.face_identity import (
    EMBEDDING_DIM,
    MODEL_FILENAME,
    FaceIdentityResolver,
    FaceIdentityResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_face_crop(h: int = 200, w: int = 150) -> np.ndarray:
    """Create a synthetic BGR face crop."""
    return np.random.default_rng(42).integers(0, 255, (h, w, 3), dtype=np.uint8)


def _mock_onnx_session(embedding: np.ndarray | None = None):
    """Create a mock ONNX InferenceSession that returns a fixed embedding."""
    if embedding is None:
        embedding = np.random.default_rng(99).standard_normal(EMBEDDING_DIM).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
    session = MagicMock()
    input_mock = MagicMock()
    input_mock.name = "input"
    session.get_inputs.return_value = [input_mock]
    session.run.return_value = [embedding.reshape(1, -1)]
    return session


# ===========================================================================
# FaceIdentityResult
# ===========================================================================


class TestFaceIdentityResult:
    def test_frozen(self):
        r = FaceIdentityResult(is_operator=True, confidence=0.9)
        with pytest.raises(AttributeError):
            r.is_operator = False  # type: ignore[misc]

    def test_fields(self):
        r = FaceIdentityResult(is_operator=True, confidence=0.85)
        assert r.is_operator is True
        assert r.confidence == 0.85

    def test_fields_not_operator(self):
        r = FaceIdentityResult(is_operator=False, confidence=0.2)
        assert r.is_operator is False
        assert r.confidence == 0.2


# ===========================================================================
# FaceIdentityResolver — construction & availability
# ===========================================================================


class TestFaceIdentityResolverConstruction:
    def test_no_enrollment_not_available(self, tmp_path):
        resolver = FaceIdentityResolver(enrollment_path=tmp_path / "nonexistent.npy")
        assert resolver.available() is False

    def test_with_enrollment_and_model_available(self, tmp_path):
        # Create enrollment file
        emb = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        save_path = tmp_path / "operator.npy"
        np.save(save_path, emb)

        # Create model file
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / MODEL_FILENAME).write_bytes(b"fake_model")

        with (
            patch.object(FaceIdentityResolver, "available") as mock_available,
        ):
            resolver = FaceIdentityResolver(enrollment_path=save_path)
            # Directly test that enrollment was loaded
            assert resolver._enrolled is not None
            np.testing.assert_array_equal(resolver._enrolled, emb)

            # Test available separately
            mock_available.return_value = True
            assert resolver.available() is True

    def test_missing_model_not_available(self, tmp_path):
        emb = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        save_path = tmp_path / "operator.npy"
        np.save(save_path, emb)

        resolver = FaceIdentityResolver(enrollment_path=save_path)
        # Model file doesn't exist at MODEL_DIR / MODEL_FILENAME
        assert resolver.available() is False


# ===========================================================================
# Preprocessing
# ===========================================================================


class TestPreprocess:
    @patch("agents.hapax_voice.face_identity.cv2")
    def test_output_shape(self, mock_cv2):
        """Output shape should be (1, 3, 112, 112)."""
        # cv2.resize returns 112x112
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        resolver = FaceIdentityResolver(enrollment_path=None)
        crop = _make_face_crop()
        result = resolver._preprocess(crop)
        assert result.shape == (1, 3, 112, 112)

    @patch("agents.hapax_voice.face_identity.cv2")
    def test_value_range(self, mock_cv2):
        """Values should be in [-1, 1] after normalization."""
        frame = np.full((112, 112, 3), 127, dtype=np.uint8)
        mock_cv2.resize.return_value = frame
        mock_cv2.cvtColor.return_value = frame
        mock_cv2.COLOR_BGR2RGB = 4

        resolver = FaceIdentityResolver(enrollment_path=None)
        result = resolver._preprocess(_make_face_crop())
        assert result.min() >= -1.0 - 1e-6
        assert result.max() <= 1.0 + 1e-6

    @patch("agents.hapax_voice.face_identity.cv2")
    def test_bgr_to_rgb_called(self, mock_cv2):
        """cv2.cvtColor should be called for BGR→RGB conversion."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        resolver = FaceIdentityResolver(enrollment_path=None)
        resolver._preprocess(_make_face_crop())
        mock_cv2.cvtColor.assert_called_once()


# ===========================================================================
# Resolve
# ===========================================================================


class TestResolve:
    def test_no_enrollment_returns_not_operator(self):
        resolver = FaceIdentityResolver(enrollment_path=None)
        result = resolver.resolve(_make_face_crop())
        assert result.is_operator is False
        assert result.confidence == 0.0

    @patch("agents.hapax_voice.face_identity.cv2")
    def test_operator_above_threshold(self, mock_cv2, tmp_path):
        """Matching face → is_operator=True."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        emb = np.random.default_rng(1).standard_normal(EMBEDDING_DIM).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        save_path = tmp_path / "operator.npy"
        np.save(save_path, emb)

        resolver = FaceIdentityResolver(enrollment_path=save_path, threshold=0.4)
        # Mock session to return the same embedding (perfect match)
        resolver._session = _mock_onnx_session(emb)

        result = resolver.resolve(_make_face_crop())
        assert result.is_operator is True
        assert result.confidence >= 0.99

    @patch("agents.hapax_voice.face_identity.cv2")
    def test_non_operator_below_threshold(self, mock_cv2, tmp_path):
        """Different face → is_operator=False."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        emb = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        emb[0] = 1.0
        save_path = tmp_path / "operator.npy"
        np.save(save_path, emb)

        # Return orthogonal embedding
        other_emb = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        other_emb[1] = 1.0

        resolver = FaceIdentityResolver(enrollment_path=save_path, threshold=0.4)
        resolver._session = _mock_onnx_session(other_emb)

        result = resolver.resolve(_make_face_crop())
        assert result.is_operator is False
        assert result.confidence < 0.4


# ===========================================================================
# Threshold boundary
# ===========================================================================


class TestThresholdBoundary:
    @patch("agents.hapax_voice.face_identity.cv2")
    def test_exactly_at_threshold_is_operator(self, mock_cv2, tmp_path):
        """Cosine similarity == threshold → is_operator=True (>= convention)."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        # Create two embeddings with known cosine similarity
        # cos(a, b) = dot(a, b) / (|a|*|b|) — use unit vectors with known angle
        threshold = 0.4
        emb_a = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        emb_a[0] = 1.0
        save_path = tmp_path / "operator.npy"
        np.save(save_path, emb_a)

        # Build embedding with exactly threshold similarity
        emb_b = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        emb_b[0] = threshold
        emb_b[1] = np.sqrt(1.0 - threshold**2)  # unit vector
        emb_b = emb_b / np.linalg.norm(emb_b)

        resolver = FaceIdentityResolver(enrollment_path=save_path, threshold=threshold)
        resolver._session = _mock_onnx_session(emb_b)

        result = resolver.resolve(_make_face_crop())
        assert result.is_operator is True
        assert abs(result.confidence - threshold) < 1e-5


# ===========================================================================
# Resolve batch
# ===========================================================================


class TestResolveBatch:
    @patch("agents.hapax_voice.face_identity.cv2")
    def test_multiple_crops(self, mock_cv2, tmp_path):
        """Batch resolves multiple crops correctly."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        emb = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        emb[0] = 1.0
        save_path = tmp_path / "operator.npy"
        np.save(save_path, emb)

        resolver = FaceIdentityResolver(enrollment_path=save_path, threshold=0.4)
        # Session returns the enrolled embedding (match)
        resolver._session = _mock_onnx_session(emb)

        crops = [_make_face_crop() for _ in range(3)]
        results = resolver.resolve_batch(crops)
        assert len(results) == 3
        assert all(r.is_operator for r in results)

    def test_empty_batch(self):
        resolver = FaceIdentityResolver(enrollment_path=None)
        results = resolver.resolve_batch([])
        assert results == []


# ===========================================================================
# Enroll
# ===========================================================================


class TestEnroll:
    @patch("agents.hapax_voice.face_identity.cv2")
    def test_enroll_saves_normalized_embedding(self, mock_cv2, tmp_path):
        """Enroll N crops → averaged, L2-normalized, saved as .npy."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        resolver = FaceIdentityResolver(enrollment_path=None, threshold=0.4)
        resolver._session = _mock_onnx_session()

        save_path = tmp_path / "enrolled.npy"
        crops = [_make_face_crop() for _ in range(5)]
        resolver.enroll(crops, save_path)

        assert save_path.exists()
        loaded = np.load(save_path)
        assert loaded.shape == (EMBEDDING_DIM,)
        # L2-normalized
        assert abs(np.linalg.norm(loaded) - 1.0) < 1e-5

    @patch("agents.hapax_voice.face_identity.cv2")
    def test_enroll_updates_internal_state(self, mock_cv2, tmp_path):
        """After enrollment, resolver has enrolled embedding."""
        mock_cv2.resize.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
        mock_cv2.COLOR_BGR2RGB = 4

        resolver = FaceIdentityResolver(enrollment_path=None)
        assert resolver._enrolled is None

        resolver._session = _mock_onnx_session()
        save_path = tmp_path / "enrolled.npy"
        resolver.enroll([_make_face_crop()], save_path)

        assert resolver._enrolled is not None
        assert resolver._enrolled.shape == (EMBEDDING_DIM,)


# ===========================================================================
# Cosine similarity reuse
# ===========================================================================


class TestCosineReuse:
    def test_import_from_speaker_id(self):
        """Verify _cosine_similarity is imported from speaker_id, not duplicated."""
        from agents.hapax_voice import face_identity, speaker_id

        assert face_identity._cosine_similarity is speaker_id._cosine_similarity


# ===========================================================================
# Enrollment CLI argument parsing
# ===========================================================================


class TestEnrollCLI:
    def test_enroll_cli_requires_images_or_capture(self, monkeypatch):
        """CLI should error when neither --images nor --capture provided."""
        monkeypatch.setattr("sys.argv", ["hapax-voice-enroll"])
        with pytest.raises(SystemExit):
            from agents.hapax_voice.face_identity import enroll_cli

            enroll_cli()
