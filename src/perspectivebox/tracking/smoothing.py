from __future__ import annotations

import numpy as np


def ema_update(prev: np.ndarray | None, value: np.ndarray, alpha: float) -> np.ndarray:
    """Exponential moving average. `alpha` in (0, 1]; higher = more responsive."""
    if prev is None or prev.shape != value.shape:
        return value.astype(np.float64, copy=True)
    return (alpha * value + (1.0 - alpha) * prev).astype(np.float64, copy=False)
