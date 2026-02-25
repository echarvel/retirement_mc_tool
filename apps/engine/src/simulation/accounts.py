"""Account helpers: take_from, safe_targets."""

from typing import Tuple

import numpy as np


def take_from(arr: np.ndarray, amount: np.ndarray) -> np.ndarray:
    """In-place withdrawal across all paths. Returns remaining amount."""
    take = np.minimum(amount, np.maximum(arr, 0.0))
    arr -= take
    return amount - take


def safe_targets(
    w: np.ndarray,
    t: int,
    reserve_years: float,
    reserve_cash_fraction: float,
) -> Tuple[float, float]:
    nxt = w[min(t + 1, len(w) - 1)]
    tgt_total = reserve_years * nxt
    tgt_cash = reserve_cash_fraction * tgt_total
    tgt_base = tgt_total - tgt_cash
    return tgt_cash, tgt_base
