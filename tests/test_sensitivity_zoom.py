from perspectivebox.ui.sensitivity_panel import head_xy_scale_for_zoom


def test_head_xy_scale_endpoints():
    z0, z1 = -1.0, 1.0
    assert abs(head_xy_scale_for_zoom(z0, z0, z1, 2.0, 0.5) - 2.0) < 1e-9
    assert abs(head_xy_scale_for_zoom(z1, z0, z1, 2.0, 0.5) - 0.5) < 1e-9


def test_head_xy_scale_midpoint():
    z0, z1 = 0.0, 2.0
    m = head_xy_scale_for_zoom(1.0, z0, z1, 0.0, 10.0)
    assert abs(m - 5.0) < 1e-9
