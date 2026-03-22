from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from perspectivebox.tracking.smoothing import ema_update

# Official Tasks model (same topology as legacy Face Mesh for landmark indices 1, 33, 263).
_FACE_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


def _default_model_path() -> Path:
    d = Path.home() / ".cache" / "perspectivebox"
    d.mkdir(parents=True, exist_ok=True)
    return d / "face_landmarker.task"


def _ensure_face_landmarker_model(path: Path) -> Path:
    if path.is_file() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".download")
    try:
        urllib.request.urlretrieve(_FACE_LANDMARKER_URL, tmp)
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    return path


class FaceTracker:
    """MediaPipe Face Landmarker (Tasks API) → normalized head position (x, y, z proxy)."""

    def __init__(
        self,
        camera_index: int = 0,
        refine_landmarks: bool = True,
        smoothing_alpha: float = 0.25,
        model_path: Path | None = None,
    ) -> None:
        _ = refine_landmarks  # Tasks bundle uses a fixed model; kept for API compatibility.

        self._cap = cv2.VideoCapture(camera_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        mp_path = _ensure_face_landmarker_model(model_path or _default_model_path())

        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        RunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(mp_path)),
            running_mode=RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = FaceLandmarker.create_from_options(options)
        # VIDEO mode requires strictly increasing timestamps; wall ms can repeat within one frame.
        self._video_ts_ms = 0
        self._smooth_alpha = float(smoothing_alpha)
        self._smoothed: np.ndarray | None = None

    def close(self) -> None:
        self._cap.release()
        self._landmarker.close()

    def update(self, smoothing_alpha: float | None = None) -> np.ndarray | None:
        alpha = (
            float(smoothing_alpha)
            if smoothing_alpha is not None
            else self._smooth_alpha
        )
        alpha = float(np.clip(alpha, 0.02, 0.98))
        ok, frame_bgr = self._cap.read()
        if not ok or frame_bgr is None:
            return None
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]

        if not frame_rgb.flags["C_CONTIGUOUS"]:
            frame_rgb = np.ascontiguousarray(frame_rgb)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        self._video_ts_ms += 1
        result = self._landmarker.detect_for_video(mp_image, self._video_ts_ms)
        if not result.face_landmarks:
            return None

        lm = result.face_landmarks[0]
        # Nose tip, outer eye corners (same indices as legacy Face Mesh).
        nose = lm[1]
        left_eye_outer = lm[33]
        right_eye_outer = lm[263]
        face_w = float(
            np.hypot(
                (right_eye_outer.x - left_eye_outer.x) * w,
                (right_eye_outer.y - left_eye_outer.y) * h,
            )
        )
        if face_w < 1e-3:
            return None

        nx = float((nose.x - 0.5) * 2.0)
        ny = float((0.5 - nose.y) * 2.0)

        ref_w = 120.0
        z = float(np.clip(ref_w / face_w, 0.35, 2.0))

        raw = np.array([nx, ny, z], dtype=np.float64)
        self._smoothed = ema_update(self._smoothed, raw, alpha)
        return self._smoothed


def debug_main() -> None:
    tracker = FaceTracker()
    try:
        print("Face tracking debug — Ctrl+C to stop. Values: nx ny z (smoothed)")
        while True:
            p = tracker.update()
            if p is not None:
                print(f"\rnx={p[0]:+.3f} ny={p[1]:+.3f} z={p[2]:.3f}   ", end="", flush=True)
            else:
                print("\r(no face)                    ", end="", flush=True)
            time.sleep(0.03)
    except KeyboardInterrupt:
        print()
    finally:
        tracker.close()


if __name__ == "__main__":
    debug_main()
    sys.exit(0)
