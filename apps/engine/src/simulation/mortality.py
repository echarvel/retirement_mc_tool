"""SSA male life table (2022) and death-weighted success calculation."""

from typing import Tuple

import numpy as np

# SSA male life table (2022), ages 53-99 (age, qx, lx)
# Conditional on alive at 53
SSA_ROWS = [
    (53, 0.007073, 88825), (54, 0.007675, 88196), (55, 0.008348, 87520),
    (56, 0.009051, 86789), (57, 0.009822, 86003), (58, 0.010669, 85159),
    (59, 0.011548, 84250), (60, 0.012458, 83277), (61, 0.013403, 82240),
    (62, 0.014450, 81138), (63, 0.015571, 79965), (64, 0.016737, 78720),
    (65, 0.017897, 77402), (66, 0.019017, 76017), (67, 0.020213, 74572),
    (68, 0.021569, 73064), (69, 0.023088, 71488), (70, 0.024828, 69838),
    (71, 0.026705, 68104), (72, 0.028761, 66285), (73, 0.031116, 64379),
    (74, 0.033861, 62376), (75, 0.037088, 60263), (76, 0.041126, 58028),
    (77, 0.045241, 55642), (78, 0.049793, 53125), (79, 0.054768, 50479),
    (80, 0.060660, 47715), (81, 0.067027, 44820), (82, 0.073999, 41816),
    (83, 0.081737, 38722), (84, 0.090458, 35557), (85, 0.100525, 32340),
    (86, 0.111793, 29089), (87, 0.124494, 25837), (88, 0.138398, 22621),
    (89, 0.153207, 19490), (90, 0.169704, 16504), (91, 0.187963, 13703),
    (92, 0.208395, 11128), (93, 0.230808, 8809), (94, 0.253914, 6776),
    (95, 0.277402, 5055), (96, 0.300882, 3653), (97, 0.324326, 2554),
    (98, 0.347332, 1726), (99, 0.369430, 1126),
]


def mortality_weights() -> Tuple[np.ndarray, np.ndarray]:
    ages = np.array([r[0] for r in SSA_ROWS], dtype=int)
    qx = np.array([r[1] for r in SSA_ROWS], dtype=float)
    lx = np.array([r[2] for r in SSA_ROWS], dtype=float)
    l0 = lx[0]
    dx = lx * qx
    p = dx / l0
    p = p / p.sum()
    return ages, p


def death_weighted_success(
    fail_idx: np.ndarray, ages_model: np.ndarray
) -> Tuple[float, float]:
    """Return (death-weighted success, success-to-age-99/horizon).

    Convention: fail_idx == len(ages_model) means 'never failed within horizon'.
    """
    ages_lt, p_death = mortality_weights()
    n_years = len(ages_model)

    ruin_by_t = np.array(
        [(fail_idx <= t).mean() for t in range(n_years)], dtype=float
    )

    age_to_t = {int(ages_model[t]): t for t in range(n_years)}
    ruin_by_age = np.array(
        [ruin_by_t[age_to_t.get(int(a), n_years - 1)] for a in ages_lt],
        dtype=float,
    )

    p_dw = float(np.sum(p_death * (1.0 - ruin_by_age)))
    p99 = float((fail_idx >= n_years).mean())
    return p_dw, p99
