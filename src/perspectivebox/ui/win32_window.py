"""Win32 helpers for the portal window."""

from __future__ import annotations

import ctypes
import sys
from typing import Any

# Exclude window from screen capture; capture shows whatever is behind it.
WDA_EXCLUDEFROMCAPTURE = 0x00000011
WDA_NONE = 0x00000000


def try_exclude_window_from_capture(glfw_window: Any) -> bool:
    """
    Mark the GLFW window as excluded from Desktop Duplication / screenshots.

    Returns True if SetWindowDisplayAffinity succeeded (caller can skip blacking
    out the portal rect). Windows 10 2004+ required.
    """
    if sys.platform != "win32":
        return False
    try:
        import glfw

        hwnd = int(glfw.get_win32_window(glfw_window))
    except Exception:
        return False
    if not hwnd:
        return False
    try:
        ok = bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
        return ok
    except Exception:
        return False


def clear_window_capture_affinity(glfw_window: Any) -> None:
    if sys.platform != "win32":
        return
    try:
        import glfw

        hwnd = int(glfw.get_win32_window(glfw_window))
        if hwnd:
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_NONE)
    except Exception:
        pass
