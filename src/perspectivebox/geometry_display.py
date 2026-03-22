"""
Interior box in world units.

- Vertical extent of every wall is fixed to **1080** (DISPLAY_HEIGHT).
- Back wall is **1920×1080** (16:9).
- Left/right walls use the same **1920** span along **depth (z)** so they are **1920×1080**, not square
  (previously depth equaled height and sides were 1080×1080).
"""

DISPLAY_HEIGHT = 1080.0
DISPLAY_WIDTH = 1920.0

# Back wall: x ∈ [-HALF_X, HALF_X], y ∈ [-HALF_Y, HALF_Y] → 1920 × 1080.
HALF_X = DISPLAY_WIDTH / 2.0
HALF_Y = DISPLAY_HEIGHT / 2.0

# Room depth z ∈ [-HALF_Z, HALF_Z]: match monitor **width** so side faces share 16:9 with the back wall.
HALF_Z = HALF_X
