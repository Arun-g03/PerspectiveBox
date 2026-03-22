import numpy as np

from perspectivebox.input_bridge.raycast import intersect_textured_walls, ray_from_ndc
from perspectivebox.projection.off_axis import head_to_view_proj
from perspectivebox.tracking.smoothing import ema_update


def test_ema_first_sample():
    v = np.array([1.0, 2.0, 3.0])
    assert np.allclose(ema_update(None, v, 0.5), v)


def test_ray_hits_back_wall():
    head = np.array([0.0, 0.0, 1.0])
    view, proj, _ = head_to_view_proj(head)
    ro, rd = ray_from_ndc(0.0, 0.0, view, proj)
    hit = intersect_textured_walls(ro, rd)
    assert hit is not None
    wall, u, v = hit
    assert wall == 0
    assert 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0
