from __future__ import annotations

import numpy as np

from perspectivebox.geometry_display import HALF_X, HALF_Y

# When True, head yaw (look left/right) moves the virtual viewpoint opposite to raw tracker X.
# Feels natural for a “window into the desktop” so the scene shifts as if the monitor were a hole.
INVERT_HEAD_YAW = True
# When True, head pitch (look up/down) moves the virtual viewpoint opposite to raw tracker Y.
INVERT_HEAD_PITCH = True


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-9:
        return v * 0.0
    return v / n


def look_at_rh(eye: np.ndarray, target: np.ndarray, world_up: np.ndarray) -> np.ndarray:
    """4x4 row-major world→view for column vectors: clip = P @ V @ X (use .T for GL column-major upload)."""
    eye = np.asarray(eye, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    world_up = np.asarray(world_up, dtype=np.float64)
    f = _normalize(target - eye)
    s = _normalize(np.cross(f, world_up))
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float64)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


def frustum_rh(left: float, right: float, bottom: float, top: float, near: float, far: float) -> np.ndarray:
    """OpenGL-style column-vector projection (row storage); transpose when uploading as column-major."""
    rl = right - left
    tb = top - bottom
    fn = far - near
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = 2.0 * near / rl
    m[0, 2] = (right + left) / rl
    m[1, 1] = 2.0 * near / tb
    m[1, 2] = (top + bottom) / tb
    m[2, 2] = -(far + near) / fn
    m[2, 3] = -(2.0 * far * near) / fn
    m[3, 2] = -1.0
    return m


def head_to_view_proj(
    head_xyz: np.ndarray,
    near: float = 0.05,
    far: float = 5000.0,
    *,
    pan_xy: tuple[float, float] = (0.0, 0.0),
    ez_scale: float = 1.0,
    head_xy_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    head_xyz: smoothed [nx, ny, z_proxy] from FaceTracker (roughly [-1,1], [-1,1], ~0.35–2).

    Virtual screen at z=0 matches DISPLAY_WIDTH×DISPLAY_HEIGHT (1080 px tall in world units).
    Eye in front (+z) looking at origin.
    Horizontal coupling uses -nx when INVERT_HEAD_YAW is True; vertical uses -ny when
    INVERT_HEAD_PITCH is True (see module constants).
    pan_xy: extra world-space offset applied to eye X/Y (manual pan).
    ez_scale: multiplies head-derived eye Z; >1 zooms in (narrower frustum).
    head_xy_scale: multiplier for head X/Y offset (UI sliders vs zoom).
    Returns (view_4x4, proj_4x4, eye_world_3) as float64 row matrices; upload proj.T and view.T for GL.
    """
    nx, ny, zp = float(head_xyz[0]), float(head_xyz[1]), float(head_xyz[2])
    nx_use = -nx if INVERT_HEAD_YAW else nx
    ny_use = -ny if INVERT_HEAD_PITCH else ny
    px, py = float(pan_xy[0]), float(pan_xy[1])
    hs = float(head_xy_scale)
    ex = nx_use * 0.22 * HALF_Y * hs + px
    ey = ny_use * 0.22 * HALF_Y * hs + py
    ez0 = float(np.clip(0.55 * HALF_Y + 0.12 * (zp - 1.0) * HALF_Y, 0.28 * HALF_Y, 1.4 * HALF_Y))
    ez = max(ez0 * float(ez_scale), 1e-6)
    eye = np.array([ex, ey, ez], dtype=np.float64)

    l = (-HALF_X - ex) * near / ez
    r = (HALF_X - ex) * near / ez
    b = (-HALF_Y - ey) * near / ez
    t = (HALF_Y - ey) * near / ez

    view = look_at_rh(eye, np.array([0.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]))
    proj = frustum_rh(l, r, b, t, near, far)
    return view, proj, eye
