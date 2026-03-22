from __future__ import annotations

import sys

import numpy as np

from perspectivebox.capture.monitors import CaptureTarget, load_capture_targets, wall_source_indices

try:
    import bettercam
except ImportError:  # pragma: no cover
    bettercam = None  # type: ignore


def _apply_mask_local(
    frame: np.ndarray,
    exclude_global: tuple[int, int, int, int],
    target: CaptureTarget,
) -> None:
    """Zero out the intersection of exclude_global with this monitor in frame-local pixels."""
    h, w = frame.shape[:2]
    ex_l, ex_t, ex_r, ex_b = exclude_global
    ml, mt, mr, mb = target.left, target.top, target.right, target.bottom
    ix1 = max(ex_l, ml)
    iy1 = max(ex_t, mt)
    ix2 = min(ex_r, mr)
    iy2 = min(ex_b, mb)
    if ix2 <= ix1 or iy2 <= iy1:
        return
    loc_l = int(ix1 - ml)
    loc_t = int(iy1 - mt)
    loc_r = int(ix2 - ml)
    loc_b = int(iy2 - mt)
    loc_l = int(np.clip(loc_l, 0, w - 1))
    loc_r = int(np.clip(loc_r, 0, w))
    loc_t = int(np.clip(loc_t, 0, h - 1))
    loc_b = int(np.clip(loc_b, 0, h))
    if loc_r <= loc_l or loc_b <= loc_t:
        return
    frame[loc_t:loc_b, loc_l:loc_r] = 0


class MultiMonitorCapture:
    """
    One bettercam instance per DXGI output (left-to-right order).
    Produces three wall textures (left / back / right) according to monitor count.
    """

    def __init__(self, output_color: str = "RGB") -> None:
        if bettercam is None:
            raise RuntimeError("bettercam is not installed")
        self.targets = load_capture_targets()
        if not self.targets:
            raise RuntimeError("No attached desktop outputs found")
        self._cams: list = []
        for t in self.targets:
            cam = bettercam.create(
                device_idx=t.device_idx,
                output_idx=t.output_idx,
                output_color=output_color,
            )
            self._cams.append(cam)
        self._li, self._bi, self._ri = wall_source_indices(len(self.targets))
        print(
            f"PerspectiveBox: {len(self.targets)} display(s); "
            f"walls left/back/right use monitor indices "
            f"{self._li}/{self._bi}/{self._ri} (left-to-right order).",
            file=sys.stderr,
        )

    def close(self) -> None:
        for cam in self._cams:
            try:
                cam.release()
            except Exception:
                pass
        self._cams.clear()

    def wall_indices(self) -> tuple[int, int, int]:
        return (self._li, self._bi, self._ri)

    def grab_walls(
        self,
        exclude_rect: tuple[int, int, int, int] | None = None,
    ) -> tuple[
        tuple[np.ndarray | None, CaptureTarget],
        tuple[np.ndarray | None, CaptureTarget],
        tuple[np.ndarray | None, CaptureTarget],
    ]:
        """
        Returns ((rgb_left, target_left), (rgb_back, target_back), (rgb_right, target_right)).
        Each rgb is HxWx3 or None if grab failed for that source monitor.
        exclude_rect: global desktop (left, top, right, bottom) to black out (recursion guard).
        """
        frames: list[np.ndarray | None] = []
        for cam in self._cams:
            f = cam.grab()
            frames.append(None if f is None else np.ascontiguousarray(f))

        if exclude_rect is not None:
            for i, t in enumerate(self.targets):
                if frames[i] is not None:
                    _apply_mask_local(frames[i], exclude_rect, t)

        def pick(idx: int) -> tuple[np.ndarray | None, CaptureTarget]:
            idx = min(idx, len(self.targets) - 1)
            return (frames[idx], self.targets[idx])

        return (pick(self._li), pick(self._bi), pick(self._ri))
