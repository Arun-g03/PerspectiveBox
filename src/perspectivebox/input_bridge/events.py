from __future__ import annotations

from pynput.mouse import Button, Controller


def click_screen(x: int, y: int, button: Button = Button.left) -> None:
    """Move cursor and perform a short click at absolute screen coordinates."""
    mouse = Controller()
    mouse.position = (int(x), int(y))
    mouse.click(button, 1)
