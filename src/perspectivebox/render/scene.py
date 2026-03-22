from __future__ import annotations

import numpy as np
import moderngl

from perspectivebox.geometry_display import HALF_X, HALF_Y, HALF_Z

VERT_SRC = """
#version 330
uniform mat4 mvp;
in vec3 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = mvp * vec4(in_pos, 1.0);
}
"""

FRAG_SRC = """
#version 330
uniform sampler2D u_tex;
in vec2 v_uv;
out vec4 f_color;
void main() {
    f_color = texture(u_tex, v_uv);
}
"""


def _quad_vertices(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
    d: tuple[float, float, float],
) -> np.ndarray:
    verts: list[tuple[float, float, float, float, float]] = [
        (*a, 0.0, 1.0),
        (*b, 1.0, 1.0),
        (*c, 1.0, 0.0),
        (*a, 0.0, 1.0),
        (*c, 1.0, 0.0),
        (*d, 0.0, 0.0),
    ]
    return np.array(verts, dtype=np.float32)


def _wall_vertex_buffers() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    back = _quad_vertices(
        (-HALF_X, -HALF_Y, -HALF_Z),
        (HALF_X, -HALF_Y, -HALF_Z),
        (HALF_X, HALF_Y, -HALF_Z),
        (-HALF_X, HALF_Y, -HALF_Z),
    )
    left = _quad_vertices(
        (-HALF_X, -HALF_Y, HALF_Z),
        (-HALF_X, -HALF_Y, -HALF_Z),
        (-HALF_X, HALF_Y, -HALF_Z),
        (-HALF_X, HALF_Y, HALF_Z),
    )
    right = _quad_vertices(
        (HALF_X, -HALF_Y, -HALF_Z),
        (HALF_X, -HALF_Y, HALF_Z),
        (HALF_X, HALF_Y, HALF_Z),
        (HALF_X, HALF_Y, -HALF_Z),
    )
    return back, left, right


class CubeScene:
    """Inside-out box with independent textures for back / left / right walls."""

    def __init__(self, ctx: moderngl.Context) -> None:
        assert isinstance(ctx, moderngl.Context)
        self._ctx = ctx
        self.prog = ctx.program(vertex_shader=VERT_SRC, fragment_shader=FRAG_SRC)
        back_d, left_d, right_d = _wall_vertex_buffers()
        self._vao_back = ctx.vertex_array(
            self.prog, [(ctx.buffer(back_d.tobytes()), "3f 2f", "in_pos", "in_uv")]
        )
        self._vao_left = ctx.vertex_array(
            self.prog, [(ctx.buffer(left_d.tobytes()), "3f 2f", "in_pos", "in_uv")]
        )
        self._vao_right = ctx.vertex_array(
            self.prog, [(ctx.buffer(right_d.tobytes()), "3f 2f", "in_pos", "in_uv")]
        )
        blank = np.zeros((4, 4, 3), dtype=np.uint8)
        self.tex_back = ctx.texture((4, 4), 3, blank.tobytes())
        self.tex_left = ctx.texture((4, 4), 3, blank.tobytes())
        self.tex_right = ctx.texture((4, 4), 3, blank.tobytes())
        for t in (self.tex_back, self.tex_left, self.tex_right):
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._tex_sizes: dict[str, tuple[int, int]] = {
            "back": (4, 4),
            "left": (4, 4),
            "right": (4, 4),
        }

    def _resize_tex(self, name: str, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        cur = self._tex_sizes[name]
        if (width, height) == cur:
            return
        old = getattr(self, f"tex_{name}")
        old.release()
        blank = np.zeros((height, width, 3), dtype=np.uint8)
        new_tex = self._ctx.texture((width, height), 3, blank.tobytes())
        new_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        setattr(self, f"tex_{name}", new_tex)
        self._tex_sizes[name] = (width, height)

    def upload_wall(self, wall: str, rgb: np.ndarray | None) -> None:
        if rgb is None or rgb.ndim != 3 or rgb.shape[2] != 3:
            return
        h, w = rgb.shape[:2]
        wall = wall.lower()
        if wall == "back":
            self._resize_tex("back", w, h)
            self.tex_back.write(rgb.tobytes())
        elif wall == "left":
            self._resize_tex("left", w, h)
            self.tex_left.write(rgb.tobytes())
        elif wall == "right":
            self._resize_tex("right", w, h)
            self.tex_right.write(rgb.tobytes())

    def draw(self, mvp: np.ndarray) -> None:
        mvp_bytes = mvp.astype(np.float32, copy=False).T.tobytes()
        self.prog["mvp"].write(mvp_bytes)
        self.tex_left.use(location=0)
        self.prog["u_tex"].value = 0
        self._vao_left.render()
        self.tex_back.use(location=0)
        self.prog["u_tex"].value = 0
        self._vao_back.render()
        self.tex_right.use(location=0)
        self.prog["u_tex"].value = 0
        self._vao_right.render()
