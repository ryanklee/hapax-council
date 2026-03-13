"""Face identity resolution via ArcFace embedding cosine similarity.

Follows the speaker_id.py pattern: enrollment → stored embedding → cosine
similarity at inference time. Not an auth mechanism — used for routing
(operator vs guest mode). Never identifies guests (management_governance axiom).
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]

from agents.hapax_voice.speaker_id import _cosine_similarity

log = logging.getLogger(__name__)

MODEL_DIR = Path.home() / ".local" / "share" / "hapax-voice" / "models"
MODEL_FILENAME = "w600k_r50.onnx"
EMBEDDING_PATH = Path.home() / ".local" / "share" / "hapax-voice" / "operator_face_embedding.npy"
INPUT_SIZE = (112, 112)
EMBEDDING_DIM = 512


@dataclass(frozen=True)
class FaceIdentityResult:
    """Result of face identity resolution."""

    is_operator: bool
    confidence: float


class FaceIdentityResolver:
    """Identifies the operator by comparing face embeddings against an enrolled reference.

    Not an auth mechanism — used for routing (operator vs guest mode).
    """

    def __init__(
        self,
        enrollment_path: Path | None = None,
        threshold: float = 0.4,
    ) -> None:
        self._threshold = threshold
        self._enrollment_path = enrollment_path or EMBEDDING_PATH
        self._enrolled: np.ndarray | None = None
        self._session = None  # lazy ONNX session

        if self._enrollment_path.exists():
            self._enrolled = np.load(self._enrollment_path)
            log.info("Loaded face enrollment from %s", self._enrollment_path)

    def available(self) -> bool:
        """Check if model file exists AND embedding file exists AND onnxruntime importable."""
        if self._enrolled is None:
            return False
        model_path = MODEL_DIR / MODEL_FILENAME
        if not model_path.exists():
            return False
        try:
            import onnxruntime  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_session(self) -> None:
        """Lazy-load ONNX inference session."""
        if self._session is not None:
            return
        import onnxruntime as ort

        model_path = MODEL_DIR / MODEL_FILENAME
        self._session = ort.InferenceSession(
            str(model_path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        """Resize to 112x112, BGR→RGB, normalize, transpose to NCHW."""
        resized = cv2.resize(crop, INPUT_SIZE)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = (rgb.astype(np.float32) - 127.5) / 128.0
        # HWC → NCHW
        return normalized.transpose(2, 0, 1)[np.newaxis, ...]

    def _compute_embedding(self, preprocessed: np.ndarray) -> np.ndarray:
        """Run ONNX inference and L2-normalize the output."""
        self._ensure_session()
        input_name = self._session.get_inputs()[0].name
        result = self._session.run(None, {input_name: preprocessed})
        embedding = result[0].flatten()
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def resolve(self, face_crop: np.ndarray) -> FaceIdentityResult:
        """Resolve whether a face crop belongs to the operator."""
        if self._enrolled is None:
            return FaceIdentityResult(is_operator=False, confidence=0.0)
        preprocessed = self._preprocess(face_crop)
        embedding = self._compute_embedding(preprocessed)
        similarity = _cosine_similarity(embedding, self._enrolled)
        return FaceIdentityResult(
            is_operator=similarity >= self._threshold,
            confidence=similarity,
        )

    def resolve_batch(self, crops: list[np.ndarray]) -> list[FaceIdentityResult]:
        """Resolve identity for multiple face crops."""
        return [self.resolve(crop) for crop in crops]

    def enroll(self, face_crops: list[np.ndarray], save_path: Path) -> None:
        """Extract embeddings for each crop, average, L2-normalize, and save."""
        embeddings = []
        for crop in face_crops:
            preprocessed = self._preprocess(crop)
            embedding = self._compute_embedding(preprocessed)
            embeddings.append(embedding)
        averaged = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(averaged)
        if norm > 0:
            averaged = averaged / norm
        save_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(save_path, averaged)
        self._enrolled = averaged
        log.info("Enrolled face embedding to %s (%d crops averaged)", save_path, len(face_crops))


def enroll_cli() -> None:
    """CLI entry point for face enrollment."""
    parser = argparse.ArgumentParser(description="Enroll operator face for identity resolution")
    parser.add_argument(
        "--images",
        nargs="+",
        type=Path,
        help="Paths to face images for enrollment",
    )
    parser.add_argument(
        "--capture",
        type=int,
        default=0,
        help="Capture N frames from webcam instead of using images",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EMBEDDING_PATH,
        help=f"Output path for embedding (default: {EMBEDDING_PATH})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help="Cosine similarity threshold (default: 0.4)",
    )
    args = parser.parse_args()

    if not args.images and args.capture <= 0:
        parser.error("Provide --images or --capture N")

    import cv2
    import mediapipe as mp

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
    )

    crops: list[np.ndarray] = []

    if args.images:
        for img_path in args.images:
            frame = cv2.imread(str(img_path))
            if frame is None:
                print(f"Warning: could not read {img_path}", file=sys.stderr)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            if not results.multi_face_landmarks:
                print(f"Warning: no face found in {img_path}", file=sys.stderr)
                continue
            landmarks = results.multi_face_landmarks[0]
            h, w = frame.shape[:2]
            xs = [lm.x * w for lm in landmarks.landmark]
            ys = [lm.y * h for lm in landmarks.landmark]
            x_min, x_max = int(max(0, min(xs))), int(min(w, max(xs)))
            y_min, y_max = int(max(0, min(ys))), int(min(h, max(ys)))
            if x_max > x_min and y_max > y_min:
                crops.append(frame[y_min:y_max, x_min:x_max])
    else:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: could not open webcam", file=sys.stderr)
            sys.exit(1)
        captured = 0
        while captured < args.capture:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                h, w = frame.shape[:2]
                xs = [lm.x * w for lm in landmarks.landmark]
                ys = [lm.y * h for lm in landmarks.landmark]
                x_min, x_max = int(max(0, min(xs))), int(min(w, max(xs)))
                y_min, y_max = int(max(0, min(ys))), int(min(h, max(ys)))
                if x_max > x_min and y_max > y_min:
                    crops.append(frame[y_min:y_max, x_min:x_max])
                    captured += 1
                    print(f"Captured {captured}/{args.capture}")
        cap.release()

    face_mesh.close()

    if not crops:
        print("Error: no face crops extracted", file=sys.stderr)
        sys.exit(1)

    resolver = FaceIdentityResolver(threshold=args.threshold)
    resolver.enroll(crops, args.output)
    print(f"Enrolled {len(crops)} face crops → {args.output}")
