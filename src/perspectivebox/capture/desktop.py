from __future__ import annotations

import numpy as np

try:
    import bettercam
except ImportError:  # pragma: no cover
    bettercam = None  # type: ignore


class DesktopCapture:
    """DXGI desktop grab via bettercam, with optional screen-rect masking (recursion guard)."""

    def __init__(self, output_idx: int = 0, output_color: str = "RGB") -> None:
        if bettercam is None:
            raise RuntimeError("bettercam is not installed")
        self._cam = bettercam.create(output_idx=output_idx, output_color=output_color)

    def close(self) -> None:
        try:
            del self._cam
        except Exception:
            pass

    def grab(
        self,
        exclude_rect: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray | None:
        """
        Returns HxWxC RGB uint8 or None.

        exclude_rect: (left, top, right, bottom) in **desktop/screen pixel** coordinates.
        That region is zeroed after capture to avoid capturing the portal window.
        """
        frame = self._cam.grab()
        if frame is None:
            return None
        out = np.ascontiguousarray(frame)
        if exclude_rect is not None:
            self._apply_mask(out, exclude_rect)
        return out

    @staticmethod
    def _apply_mask(frame: np.ndarray, rect: tuple[int, int, int, int]) -> None:
        h, w = frame.shape[:2]
        left, top, right, bottom = rect
        left = int(np.clip(left, 0, w - 1))
        right = int(np.clip(right, 0, w))
        top = int(np.clip(top, 0, h - 1))
        bottom = int(np.clip(bottom, 0, h))
        if right <= left or bottom <= top:
            return
        frame[top:bottom, left:right] = 0
