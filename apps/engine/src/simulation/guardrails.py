"""Guardrails spending cut logic."""

import numpy as np


def compute_cuts(
    drawdown: np.ndarray, dd1: float, dd2: float, cut1: float, cut2: float
) -> np.ndarray:
    """Compute spending cut fractions based on drawdown thresholds."""
    cut = np.zeros_like(drawdown)
    cut = np.where(drawdown >= dd2, cut2, cut)
    cut = np.where((drawdown >= dd1) & (drawdown < dd2), cut1, cut)
    return cut
