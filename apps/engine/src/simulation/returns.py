"""Return generators for Monte Carlo simulation."""

import numpy as np


def generate_returns(
    seed: int, n_sims: int, n_years: int, mu: float, vol: float
) -> np.ndarray:
    """Generate i.i.d. normal returns clipped at -99%."""
    rng = np.random.default_rng(seed)
    r = rng.normal(mu, vol, size=(n_sims, n_years))
    return np.clip(r, -0.99, None)
