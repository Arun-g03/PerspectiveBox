from __future__ import annotations

import sys

import numpy as np

from perspectivebox.capture.letterbox import letterbox_to_size
from perspectivebox.capture.monitors import (
    CaptureTarget,
    load_capture_targets,
    split_monitor_into_wall_regions,
    wall_source_indices,
)
from perspectivebox.geometry_display import DISPLAY_HEIGHT, DISPLAY_WIDTH

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
        self._single_regions: tuple[CaptureTarget, CaptureTarget, CaptureTarget] | None = None
        n = len(self.targets)
        if n == 1:
            self._single_regions = split_monitor_into_wall_regions(self.targets[0])
            print(
                "PerspectiveBox: 1 display; single-monitor region split (L/C/R thirds).",
                file=sys.stderr,
            )
            print(
                "PerspectiveBox: for full-resolution walls, add 2 virtual displays "
                "(see Docs/VirtualDisplays.md).",
                file=sys.stderr,
            )
        else:
            print(
                f"PerspectiveBox: {n} display(s); "
                f"walls left/back/right use monitor indices "
                f"{self._li}/{self._bi}/{self._ri} (left-to-right order).",
                file=sys.stderr,
            )
            if n < 3:
                print(
                    "PerspectiveBox: fewer than 3 displays — some walls share a monitor. "
                    "Install virtual displays for L/C/R (see Docs/VirtualDisplays.md).",
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
        tuple[np.ndarray | None, CaptureTarget, dict],
        tuple[np.ndarray | None, CaptureTarget, dict],
        tuple[np.ndarray | None, CaptureTarget, dict],
    ]:
        """
        Returns ((rgb, target, click_meta), ...) for left / back / right.

        click_meta maps wall UVs to global desktop pixels (supports letterboxing).
        exclude_rect: global desktop (left, top, right, bottom) to black out when
        the portal cannot be excluded from capture via Win32 affinity.
        """
        frames: list[np.ndarray | None] = []
        for cam in self._cams:
            f = cam.grab()
            frames.append(None if f is None else np.ascontiguousarray(f))

        if exclude_rect is not None:
            for i, t in enumerate(self.targets):
                if frames[i] is not None:
                    _apply_mask_local(frames[i], exclude_rect, t)

        if self._single_regions is not None:
            frame = frames[0] if frames else None
            left_t, back_t, right_t = self._single_regions
            if frame is None:
                empty = {
                    "gx": 0,
                    "gy": 0,
                    "rw": 1,
                    "rh": 1,
                    "tex_w": 1,
                    "tex_h": 1,
                    "content_x": 0,
                    "content_y": 0,
                    "content_w": 1,
                    "content_h": 1,
                }
                return (
                    (None, left_t, dict(empty)),
                    (None, back_t, dict(empty)),
                    (None, right_t, dict(empty)),
                )
            mon = self.targets[0]
            # Frame-local x relative to the full monitor; region targets use global coords.
            x1 = left_t.right - mon.left
            x2 = back_t.right - mon.left
            crops = (
                (np.ascontiguousarray(frame[:, :x1]), left_t),
                (np.ascontiguousarray(frame[:, x1:x2]), back_t),
                (np.ascontiguousarray(frame[:, x2:]), right_t),
            )
            out = []
            for crop, tgt in crops:
                canvas, ox, oy, cw, ch = letterbox_to_size(
                    crop, int(DISPLAY_WIDTH), int(DISPLAY_HEIGHT)
                )
                meta = {
                    "gx": int(tgt.left),
                    "gy": int(tgt.top),
                    "rw": int(tgt.width),
                    "rh": int(tgt.height),
                    "tex_w": int(canvas.shape[1]),
                    "tex_h": int(canvas.shape[0]),
                    "content_x": int(ox),
                    "content_y": int(oy),
                    "content_w": int(cw),
                    "content_h": int(ch),
                }
                out.append((canvas, tgt, meta))
            return (out[0], out[1], out[2])

        def pick(idx: int) -> tuple[np.ndarray | None, CaptureTarget, dict]:
            idx = min(idx, len(self.targets) - 1)
            rgb = frames[idx]
            tgt = self.targets[idx]
            if rgb is None:
                meta = {
                    "gx": int(tgt.left),
                    "gy": int(tgt.top),
                    "rw": 1,
                    "rh": 1,
                    "tex_w": 1,
                    "tex_h": 1,
                    "content_x": 0,
                    "content_y": 0,
                    "content_w": 1,
                    "content_h": 1,
                }
            else:
                h0, w0 = rgb.shape[:2]
                meta = {
                    "gx": int(tgt.left),
                    "gy": int(tgt.top),
                    "rw": int(w0),
                    "rh": int(h0),
                    "tex_w": int(w0),
                    "tex_h": int(h0),
                    "content_x": 0,
                    "content_y": 0,
                    "content_w": int(w0),
                    "content_h": int(h0),
                }
            return (rgb, tgt, meta)

        return (pick(self._li), pick(self._bi), pick(self._ri))
