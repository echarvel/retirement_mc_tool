"""Binary search optimizer for maximum spending E."""

import numpy as np

from .engine import simulate_once


def find_max_E(
    returns: np.ndarray,
    target: float,
    e_lo: int,
    e_hi: int,
    e_search_iters: int,
    optimize_success_metric: str,
    both_weight: float,
    **sim_kwargs,
) -> tuple[int, dict]:
    """Binary search for max annual spending meeting target success probability.

    sim_kwargs are passed through to simulate_once (all params except E and returns).
    """

    def objective_p(metrics: dict) -> float:
        p_dw = float(metrics["p_success_death_weighted"])
        p99 = float(metrics["p_success_to_age_99"])
        if optimize_success_metric == "age_99":
            return p99
        if optimize_success_metric == "both_min":
            return min(p_dw, p99)
        if optimize_success_metric == "both_weighted":
            return both_weight * p_dw + (1.0 - both_weight) * p99
        return p_dw

    lo, hi = e_lo, e_hi

    metrics_lo = simulate_once(returns=returns, E=lo, **sim_kwargs)
    if objective_p(metrics_lo) < target:
        return lo, metrics_lo

    metrics_hi = simulate_once(returns=returns, E=hi, **sim_kwargs)
    while objective_p(metrics_hi) >= target and hi < 600_000:
        lo = hi
        metrics_lo = metrics_hi
        hi = int(hi * 1.25)
        metrics_hi = simulate_once(returns=returns, E=hi, **sim_kwargs)

    for _ in range(e_search_iters):
        mid = (lo + hi) // 2
        metrics_mid = simulate_once(returns=returns, E=int(mid), **sim_kwargs)
        if objective_p(metrics_mid) >= target:
            lo = mid
            metrics_lo = metrics_mid
        else:
            hi = mid - 1

    return int(lo), metrics_lo
