from __future__ import annotations

import math
import sys

import glfw
import moderngl
import numpy as np

from perspectivebox.capture.multi_desktop import MultiMonitorCapture
from perspectivebox.geometry_display import HALF_X, HALF_Y
from perspectivebox.input_bridge.events import click_screen
from perspectivebox.input_bridge.raycast import intersect_textured_walls, ndc_from_cursor, ray_from_ndc
from perspectivebox.projection.off_axis import head_to_view_proj
from perspectivebox.render.scene import CubeScene
from perspectivebox.tracking.face_track import FaceTracker
from perspectivebox.ui.sensitivity_panel import try_open_head_sensitivity_ui

# Portal size (16:9, typical FHD capture aspect).
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# Mouse wheel → exp(zoom_log); larger log = zoom in.
ZOOM_SCROLL_STEP = 0.12
ZOOM_LOG_MIN = -1.25
ZOOM_LOG_MAX = 1.25
# Right-drag pan: fraction of full wall span per window width/height dragged.
PAN_DRAG_SENS = 0.45
# Limit manual pan so the room stays mostly in view.
PAN_CLAMP_X = HALF_X * 0.92
PAN_CLAMP_Y = HALF_Y * 0.92


def run() -> None:
    if not glfw.init():
        raise RuntimeError("Failed to initialize glfw")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, "PerspectiveBox", None, None)
    if window is None:
        glfw.terminate()
        raise RuntimeError("Failed to create glfw window")

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.gc_mode = "auto"

    scene = CubeScene(ctx)
    try:
        capture = MultiMonitorCapture()
    except Exception as e:
        glfw.destroy_window(window)
        glfw.terminate()
        print("Desktop capture failed:", e, file=sys.stderr)
        raise

    tracker = FaceTracker()
    head_sensitivity = try_open_head_sensitivity_ui(ZOOM_LOG_MIN, ZOOM_LOG_MAX)
    head = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    head_baseline = np.zeros(3, dtype=np.float64)
    space_was_down = False

    state: dict = {
        "view": np.eye(4, dtype=np.float64),
        "proj": np.eye(4, dtype=np.float64),
        # Per-wall click mapping: index matches raycast wall_id (0=back,1=left,2=right).
        "wall_click": [
            {"w": 1, "h": 1, "gx": 0, "gy": 0},
            {"w": 1, "h": 1, "gx": 0, "gy": 0},
            {"w": 1, "h": 1, "gx": 0, "gy": 0},
        ],
        "zoom_log": 0.0,
        "pan_x": 0.0,
        "pan_y": 0.0,
    }

    def on_scroll(win, xoff: float, yoff: float) -> None:
        z = state["zoom_log"] + float(yoff) * ZOOM_SCROLL_STEP
        state["zoom_log"] = max(ZOOM_LOG_MIN, min(ZOOM_LOG_MAX, z))

    def on_mouse_click(win, button: int, action: int, mods: int) -> None:
        if button != glfw.MOUSE_BUTTON_LEFT or action != glfw.PRESS:
            return
        fb_w, fb_h = glfw.get_framebuffer_size(win)
        cx, cy = glfw.get_cursor_pos(win)
        win_w, win_h = glfw.get_window_size(win)
        sx = cx * fb_w / max(win_w, 1)
        sy = cy * fb_h / max(win_h, 1)
        ndc_x, ndc_y = ndc_from_cursor(sx, sy, fb_w, fb_h)
        ro, rd = ray_from_ndc(ndc_x, ndc_y, state["view"], state["proj"])
        hit = intersect_textured_walls(ro, rd)
        if hit is None:
            return
        wall_id, u, v = hit
        meta = state["wall_click"][wall_id]
        mw, mh = max(meta["w"], 1), max(meta["h"], 1)
        lx = int(np.clip(u * (mw - 1), 0, mw - 1))
        ly = int(np.clip((1.0 - v) * (mh - 1), 0, mh - 1))
        px = int(meta["gx"] + lx)
        py = int(meta["gy"] + ly)
        try:
            click_screen(px, py)
        except Exception as ex:
            print("Synthetic click failed:", ex, file=sys.stderr)

    glfw.set_mouse_button_callback(window, on_mouse_click)
    glfw.set_scroll_callback(window, on_scroll)

    rmb_prev: tuple[float, float] | None = None

    try:
        while not glfw.window_should_close(window):
            glfw.poll_events()
            if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
                glfw.set_window_should_close(window, True)

            p = tracker.update(smoothing_alpha=head_sensitivity.tracking_smoothing_alpha())
            if p is not None:
                head[:] = p

            space_down = glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS
            if space_down and not space_was_down and p is not None:
                head_baseline[:] = p
                state["zoom_log"] = 0.0
                state["pan_x"] = 0.0
                state["pan_y"] = 0.0
            space_was_down = space_down

            head_net = head - head_baseline

            win_w, win_h = glfw.get_window_size(window)
            win_w = max(win_w, 1)
            win_h = max(win_h, 1)
            cx, cy = glfw.get_cursor_pos(window)
            rmb_down = glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
            if rmb_down:
                if rmb_prev is not None:
                    dx, dy = cx - rmb_prev[0], cy - rmb_prev[1]
                    span_x = (2.0 * HALF_X / win_w) * PAN_DRAG_SENS
                    span_y = (2.0 * HALF_Y / win_h) * PAN_DRAG_SENS
                    state["pan_x"] -= dx * span_x
                    state["pan_y"] += dy * span_y
                    state["pan_x"] = max(-PAN_CLAMP_X, min(PAN_CLAMP_X, state["pan_x"]))
                    state["pan_y"] = max(-PAN_CLAMP_Y, min(PAN_CLAMP_Y, state["pan_y"]))
                rmb_prev = (cx, cy)
            else:
                rmb_prev = None

            wx, wy = glfw.get_window_pos(window)
            exclude = (wx, wy, wx + win_w, wy + win_h)

            (l_rgb, l_t), (b_rgb, b_t), (r_rgb, r_t) = capture.grab_walls(exclude_rect=exclude)
            scene.upload_wall("left", l_rgb)
            scene.upload_wall("back", b_rgb)
            scene.upload_wall("right", r_rgb)

            def _click_meta(rgb, t) -> dict:
                if rgb is None:
                    return {"w": 1, "h": 1, "gx": 0, "gy": 0}
                h0, w0 = rgb.shape[:2]
                return {"w": int(w0), "h": int(h0), "gx": int(t.left), "gy": int(t.top)}

            state["wall_click"] = [
                _click_meta(b_rgb, b_t),
                _click_meta(l_rgb, l_t),
                _click_meta(r_rgb, r_t),
            ]

            fb_w, fb_h = glfw.get_framebuffer_size(window)
            if fb_w <= 0 or fb_h <= 0:
                continue

            ez_scale = math.exp(state["zoom_log"])
            head_xy_scale = head_sensitivity.coupling_for_zoom(state["zoom_log"])
            view, proj, _eye = head_to_view_proj(
                head_net,
                pan_xy=(state["pan_x"], state["pan_y"]),
                ez_scale=ez_scale,
                head_xy_scale=head_xy_scale,
            )
            state["view"] = view
            state["proj"] = proj

            mvp = proj @ view

            ctx.viewport = (0, 0, fb_w, fb_h)
            cr, cg, cb = head_sensitivity.background_rgb()
            ctx.clear(cr, cg, cb, 1.0, depth=1.0)
            scene.draw(mvp)

            glfw.swap_buffers(window)
    finally:
        tracker.close()
        capture.close()
        glfw.destroy_window(window)
        glfw.terminate()
