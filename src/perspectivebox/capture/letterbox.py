"""Image helpers for wall textures."""

from __future__ import annotations

import numpy as np


def letterbox_to_size(
    src: np.ndarray,
    out_w: int,
    out_h: int,
) -> tuple[np.ndarray, int, int, int, int]:
    """
    Fit ``src`` (HxWx3) into an ``out_w``×``out_h`` canvas, preserving aspect.

    Returns (canvas, content_x, content_y, content_w, content_h) where the
    content rectangle is the placed (possibly scaled) image within the canvas.
    """
    if src.ndim != 3 or src.shape[2] != 3:
        raise ValueError("src must be HxWx3")
    out_w = max(int(out_w), 1)
    out_h = max(int(out_h), 1)
    sh, sw = src.shape[:2]
    if sw <= 0 or sh <= 0:
        canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        return canvas, 0, 0, 0, 0

    scale = min(out_w / sw, out_h / sh)
    cw = max(int(round(sw * scale)), 1)
    ch = max(int(round(sh * scale)), 1)
    # Ensure fit after rounding.
    cw = min(cw, out_w)
    ch = min(ch, out_h)
    ox = (out_w - cw) // 2
    oy = (out_h - ch) // 2

    if cw == sw and ch == sh:
        resized = src
    else:
        # Nearest-neighbor resize (no OpenCV dependency in this helper).
        y_idx = (np.arange(ch) * sh / ch).astype(np.int32)
        x_idx = (np.arange(cw) * sw / cw).astype(np.int32)
        y_idx = np.clip(y_idx, 0, sh - 1)
        x_idx = np.clip(x_idx, 0, sw - 1)
        resized = src[y_idx][:, x_idx]

    canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    canvas[oy : oy + ch, ox : ox + cw] = resized
    return np.ascontiguousarray(canvas), ox, oy, cw, ch


def wall_uv_to_region_pixel(
    u: float,
    v: float,
    *,
    tex_w: int,
    tex_h: int,
    content_x: int,
    content_y: int,
    content_w: int,
    content_h: int,
    region_w: int,
    region_h: int,
) -> tuple[int, int] | None:
    """
    Map wall texture UV (v up) through a letterboxed texture to region-local pixels.
    Returns None if the hit lands on padding.
    """
    tw = max(tex_w, 1)
    th = max(tex_h, 1)
    cw = max(content_w, 1)
    ch = max(content_h, 1)
    rw = max(region_w, 1)
    rh = max(region_h, 1)

    tex_x = u * (tw - 1) if tw > 1 else 0.0
    tex_y = (1.0 - v) * (th - 1) if th > 1 else 0.0
    if (
        tex_x < content_x
        or tex_x >= content_x + content_w
        or tex_y < content_y
        or tex_y >= content_y + content_h
    ):
        return None
    u_c = (tex_x - content_x) / (cw - 1) if cw > 1 else 0.0
    v_c = (tex_y - content_y) / (ch - 1) if ch > 1 else 0.0
    u_c = float(np.clip(u_c, 0.0, 1.0))
    v_c = float(np.clip(v_c, 0.0, 1.0))
    lx = int(np.clip(u_c * (rw - 1), 0, rw - 1))
    ly = int(np.clip(v_c * (rh - 1), 0, rh - 1))
    return lx, ly
