import numpy as np

from perspectivebox.capture.letterbox import letterbox_to_size, wall_uv_to_region_pixel
from perspectivebox.capture.monitors import CaptureTarget, split_monitor_into_wall_regions


def _monitor(left: int, top: int, width: int, height: int) -> CaptureTarget:
    return CaptureTarget(
        device_idx=0,
        output_idx=0,
        left=left,
        top=top,
        right=left + width,
        bottom=top + height,
    )


def test_split_covers_full_width_no_gaps_or_overlap():
    mon = _monitor(0, 0, 1920, 1080)
    left, back, right = split_monitor_into_wall_regions(mon)

    assert left.left == mon.left
    assert right.right == mon.right
    assert left.right == back.left
    assert back.right == right.left
    assert left.width + back.width + right.width == mon.width
    assert left.height == back.height == right.height == mon.height


def test_split_region_origins_for_click_mapping():
    # Offset desktop origin (e.g. secondary-style global coords on primary).
    mon = _monitor(100, 50, 1920, 1080)
    left, back, right = split_monitor_into_wall_regions(mon)

    assert left.left == 100 and left.top == 50
    assert back.left == 100 + 1920 // 3 and back.top == 50
    assert right.left == 100 + (2 * 1920) // 3 and right.top == 50
    assert left.right == back.left
    assert back.right == right.left


def test_split_uneven_width_integer_boundaries():
    mon = _monitor(0, 0, 1919, 1080)
    left, back, right = split_monitor_into_wall_regions(mon)
    assert left.width + back.width + right.width == 1919
    assert left.right == back.left
    assert back.right == right.left
    assert right.right == mon.right


def test_letterbox_portrait_into_16x9_pillarboxes():
    # Portrait strip (one third of 1920x1080) into 1920x1080 → side padding.
    src = np.full((1080, 640, 3), 200, dtype=np.uint8)
    canvas, ox, oy, cw, ch = letterbox_to_size(src, 1920, 1080)
    assert canvas.shape == (1080, 1920, 3)
    assert oy == 0
    assert ch == 1080
    assert cw < 1920
    assert ox > 0
    # Padding stays black; content is non-black.
    assert canvas[540, 0, 0] == 0
    assert canvas[540, ox + cw // 2, 0] == 200


def test_wall_uv_click_through_letterbox():
    src = np.zeros((1080, 640, 3), dtype=np.uint8)
    canvas, ox, oy, cw, ch = letterbox_to_size(src, 1920, 1080)
    # Center of wall UV should land in content.
    hit = wall_uv_to_region_pixel(
        0.5,
        0.5,
        tex_w=canvas.shape[1],
        tex_h=canvas.shape[0],
        content_x=ox,
        content_y=oy,
        content_w=cw,
        content_h=ch,
        region_w=640,
        region_h=1080,
    )
    assert hit is not None
    lx, ly = hit
    assert 0 <= lx < 640 and 0 <= ly < 1080
    # Far-left UV is padding.
    assert (
        wall_uv_to_region_pixel(
            0.0,
            0.5,
            tex_w=canvas.shape[1],
            tex_h=canvas.shape[0],
            content_x=ox,
            content_y=oy,
            content_w=cw,
            content_h=ch,
            region_w=640,
            region_h=1080,
        )
        is None
    )
