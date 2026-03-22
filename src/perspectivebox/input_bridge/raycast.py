from __future__ import annotations

import numpy as np

from perspectivebox.geometry_display import HALF_X, HALF_Y, HALF_Z


def ndc_from_cursor(x: float, y: float, fb_width: int, fb_height: int) -> tuple[float, float]:
    """glfw cursor (origin top-left) → OpenGL NDC x,y in [-1,1] (y up)."""
    w = max(fb_width, 1)
    h = max(fb_height, 1)
    ndc_x = 2.0 * x / w - 1.0
    ndc_y = 1.0 - 2.0 * y / h
    return ndc_x, ndc_y


def ray_from_ndc(ndc_x: float, ndc_y: float, view: np.ndarray, proj: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """World-space ray (origin, direction) from NDC; view/proj row-major numpy 4x4."""
    vp = proj @ view
    inv = np.linalg.inv(vp)
    p0 = inv @ np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float64)
    p1 = inv @ np.array([ndc_x, ndc_y, 1.0, 1.0], dtype=np.float64)
    p0 = p0[:3] / p0[3]
    p1 = p1[:3] / p1[3]
    ro = p0
    rd = p1 - p0
    n = np.linalg.norm(rd)
    if n < 1e-9:
        rd = np.array([0.0, 0.0, -1.0])
    else:
        rd = rd / n
    return ro, rd


def _hit_plane(
    ro: np.ndarray,
    rd: np.ndarray,
    plane_point: np.ndarray,
    plane_normal: np.ndarray,
) -> float | None:
    denom = float(np.dot(rd, plane_normal))
    if abs(denom) < 1e-8:
        return None
    t = float(np.dot(plane_point - ro, plane_normal) / denom)
    if t < 0:
        return None
    return t


def intersect_textured_walls(ro: np.ndarray, rd: np.ndarray) -> tuple[int, float, float] | None:
    """
    Intersect ray with back / left / right walls (each face 1920×1080 in world units).
    Returns (wall_id, u, v) with u,v in [0,1] texture coords, or None.
    wall_id: 0=back (z=-HALF_Z), 1=left (x=-HALF_X), 2=right (x=+HALF_X).
    """
    eps = 1e-2 * max(HALF_X, HALF_Y, HALF_Z)
    hits: list[tuple[int, float, float, float]] = []

    # Back z = -HALF_Z, normal (0,0,1)
    t = _hit_plane(ro, rd, np.array([0.0, 0.0, -HALF_Z]), np.array([0.0, 0.0, 1.0]))
    if t is not None:
        p = ro + rd * t
        if (
            -HALF_X - eps <= p[0] <= HALF_X + eps
            and -HALF_Y - eps <= p[1] <= HALF_Y + eps
        ):
            u = float((p[0] + HALF_X) / (2.0 * HALF_X))
            v = float((p[1] + HALF_Y) / (2.0 * HALF_Y))
            hits.append((0, t, u, v))

    # Left x = -HALF_X, normal (1,0,0)
    t = _hit_plane(ro, rd, np.array([-HALF_X, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    if t is not None:
        p = ro + rd * t
        if (
            -HALF_Z - eps <= p[2] <= HALF_Z + eps
            and -HALF_Y - eps <= p[1] <= HALF_Y + eps
        ):
            u = float((p[2] + HALF_Z) / (2.0 * HALF_Z))
            v = float((p[1] + HALF_Y) / (2.0 * HALF_Y))
            hits.append((1, t, u, v))

    # Right x = +HALF_X, normal (-1,0,0)
    t = _hit_plane(ro, rd, np.array([HALF_X, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0]))
    if t is not None:
        p = ro + rd * t
        if (
            -HALF_Z - eps <= p[2] <= HALF_Z + eps
            and -HALF_Y - eps <= p[1] <= HALF_Y + eps
        ):
            u = float((HALF_Z - p[2]) / (2.0 * HALF_Z))
            v = float((p[1] + HALF_Y) / (2.0 * HALF_Y))
            hits.append((2, t, u, v))

    if not hits:
        return None
    hits.sort(key=lambda h: h[1])
    w, _t, u, v = hits[0]
    return w, u, v
