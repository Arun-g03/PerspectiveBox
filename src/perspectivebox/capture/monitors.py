"""Discover attached displays for multi-monitor capture (screeninfo + DXGI / bettercam layout)."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from bettercam.core.device import Device
from bettercam.core.output import Output
from bettercam.util.io import enum_dxgi_adapters


@dataclass(frozen=True)
class CaptureTarget:
    """One physical output bettercam can duplicate (sorted left-to-right, top-to-bottom)."""

    device_idx: int
    output_idx: int
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _enumerate_dxgi_targets() -> list[CaptureTarget]:
    out: list[CaptureTarget] = []
    for di, adapter_ptr in enumerate(enum_dxgi_adapters()):
        device = Device(adapter_ptr)
        for oi, optr in enumerate(device.enum_outputs()):
            o = Output(optr)
            if not o.attached_to_desktop:
                continue
            r = o.desc.DesktopCoordinates
            out.append(
                CaptureTarget(
                    device_idx=di,
                    output_idx=oi,
                    left=int(r.left),
                    top=int(r.top),
                    right=int(r.right),
                    bottom=int(r.bottom),
                )
            )
    out.sort(key=lambda t: (t.left, t.top))
    return out


def load_capture_targets() -> list[CaptureTarget]:
    """
    All desktop-attached outputs, ordered left-to-right (then top-to-bottom).

    Cross-checks count with ``screeninfo`` when available and prints a short notice on mismatch.
    """
    targets = _enumerate_dxgi_targets()
    try:
        from screeninfo import get_monitors

        si = sorted(get_monitors(), key=lambda m: (m.x, m.y))
        if len(si) != len(targets):
            print(
                f"PerspectiveBox: screeninfo reports {len(si)} monitor(s), "
                f"DXGI {len(targets)} — using DXGI order for capture.",
                file=sys.stderr,
            )
    except Exception:
        pass
    return targets


def wall_source_indices(num_monitors: int) -> tuple[int, int, int]:
    """
    Map sorted monitor index → (left_wall, back_wall, right_wall).

    1 monitor: all walls show the same desktop.
    2 monitors: left | back+left duplicate | right.
    3+: left-most, center, right-most among the first three.
    """
    n = max(num_monitors, 1)
    if n == 1:
        return (0, 0, 0)
    if n == 2:
        return (0, 0, 1)
    return (0, 1, 2)
