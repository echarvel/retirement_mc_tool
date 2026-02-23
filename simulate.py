\
import datetime
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# -----------------------
# Minimal .env parser
# -----------------------
def load_env(path: str = ".env") -> Dict[str, str]:
    out: Dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing {path}. Copy .env.example to .env and edit it.")
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def get_float(env: Dict[str, str], key: str, default: float) -> float:
    v = env.get(key, "")
    return default if v == "" else float(v)

def get_int(env: Dict[str, str], key: str, default: int) -> int:
    v = env.get(key, "")
    return default if v == "" else int(float(v))

def get_str(env: Dict[str, str], key: str, default: str) -> str:
    v = env.get(key, "")
    return default if v == "" else v

def get_list_floats(env: Dict[str, str], key: str, default: List[float]) -> List[float]:
    v = env.get(key, "")
    if v == "":
        return default
    return [float(x.strip()) for x in v.split(",") if x.strip()]

def get_list_ints(env: Dict[str, str], key: str, default: List[int]) -> List[int]:
    v = env.get(key, "")
    if v == "":
        return default
    return [int(float(x.strip())) for x in v.split(",") if x.strip()]

# -----------------------
# SSA male life table (2022), ages 53-99 (qx, lx)
# Conditional on alive at 53
# -----------------------
SSA_ROWS = [
(53, 0.007073, 88825),(54, 0.007675, 88196),(55, 0.008348, 87520),(56, 0.009051, 86789),
(57, 0.009822, 86003),(58, 0.010669, 85159),(59, 0.011548, 84250),(60, 0.012458, 83277),
(61, 0.013403, 82240),(62, 0.014450, 81138),(63, 0.015571, 79965),(64, 0.016737, 78720),
(65, 0.017897, 77402),(66, 0.019017, 76017),(67, 0.020213, 74572),(68, 0.021569, 73064),
(69, 0.023088, 71488),(70, 0.024828, 69838),(71, 0.026705, 68104),(72, 0.028761, 66285),
(73, 0.031116, 64379),(74, 0.033861, 62376),(75, 0.037088, 60263),(76, 0.041126, 58028),
(77, 0.045241, 55642),(78, 0.049793, 53125),(79, 0.054768, 50479),(80, 0.060660, 47715),
(81, 0.067027, 44820),(82, 0.073999, 41816),(83, 0.081737, 38722),(84, 0.090458, 35557),
(85, 0.100525, 32340),(86, 0.111793, 29089),(87, 0.124494, 25837),(88, 0.138398, 22621),
(89, 0.153207, 19490),(90, 0.169704, 16504),(91, 0.187963, 13703),(92, 0.208395, 11128),
(93, 0.230808, 8809),(94, 0.253914, 6776),(95, 0.277402, 5055),(96, 0.300882, 3653),
(97, 0.324326, 2554),(98, 0.347332, 1726),(99, 0.369430, 1126),
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

@dataclass(frozen=True)
class Config:
    seed: int
    n_sims: int
    start_portfolio: float
    start_portfolios: list[float]
    start_age: int
    partial_year_fraction: float

    return_mu_real: float
    return_vol_real: float

    target_success_death_weighted: float
    e_lo: int
    e_hi: int
    e_search_iters: int



    optimize_success_metric: str
    both_weight: float
    mode: str
    e_fixed: float
    ss_annual_real: float
    ss_start_age: int


    earned_income_annual_real: float
    earned_income_start_age: int
    earned_income_end_age: int

    allow_surplus_savings: int
    surplus_allocation: str

    income_applies_to_actual_spend: int
    floor_annual_real: float

    reserve_years_list: List[float]
    reserve_cash_fraction: float
    safe_real_return: float

    dd1: float
    dd2: float
    cut1: float
    cut2: float

    baseline_e_for_flex: float
    baseline_flex_pre: float
    baseline_net_post_ss: float
    baseline_flex_post: float

    rm_open_age: int
    home_value_real: float
    rm_plf_at_open: float
    rm_limit_real_growth: float
    rm_bal_real_rate: float
    rm_partial_cover: float
    rm_repay_rate: float
    payoff_dd_threshold: float

    loan_amounts: List[int]
    loan_real_rate: float
    loan_term_years: int

    loan_bucket_real_return: float
    loan_bucket_use_dd: float
    loan_bucket_partial_cover: float

    output_dir: str

def read_config(env: Dict[str, str]) -> Config:
    return Config(
        seed=get_int(env, "SEED", 424242),
        n_sims=get_int(env, "N_SIMS", 25000),
        start_portfolio=get_float(env, "START_PORTFOLIO", 1_477_000.0),
        start_portfolios=(get_list_floats(env, "START_PORTFOLIOS_LIST", []) or [get_float(env, "START_PORTFOLIO", 1_477_000.0)]),
        start_age=get_int(env, "START_AGE", 53),
        partial_year_fraction=get_float(env, "PARTIAL_YEAR_FRACTION", 0.894444),

        return_mu_real=get_float(env, "RETURN_MU_REAL", 0.04),
        return_vol_real=get_float(env, "RETURN_VOL_REAL", 0.10),

        target_success_death_weighted=get_float(env, "TARGET_SUCCESS_DEATH_WEIGHTED", 0.90),
        e_lo=get_int(env, "E_LO", 40000),
        e_hi=get_int(env, "E_HI", 220000),
        e_search_iters=get_int(env, "E_SEARCH_ITERS", 19),

        optimize_success_metric=get_str(env, "OPTIMIZE_SUCCESS_METRIC", "death_weighted"),
        both_weight=get_float(env, "BOTH_WEIGHT", 0.5),

        mode=get_str(env, "MODE", "optimize"),
        e_fixed=get_float(env, "E_FIXED", 80_000.0),

        ss_annual_real=get_float(env, "SS_ANNUAL_REAL", 46_405.0),
        ss_start_age=get_int(env, "SS_START_AGE", 63),

        earned_income_annual_real=get_float(env, "EARNED_INCOME_ANNUAL_REAL", 0.0),
        earned_income_start_age=get_int(env, "EARNED_INCOME_START_AGE", 54),
        earned_income_end_age=get_int(env, "EARNED_INCOME_END_AGE", 62),

        allow_surplus_savings=get_int(env, "ALLOW_SURPLUS_SAVINGS", 0),
        surplus_allocation=get_str(env, "SURPLUS_ALLOCATION", "reserve_first"),
        income_applies_to_actual_spend=get_int(env, "INCOME_APPLIES_TO_ACTUAL_SPEND", 1),

        floor_annual_real=get_float(env, "FLOOR_ANNUAL_REAL", 60_000.0),

        reserve_years_list=get_list_floats(env, "RESERVE_YEARS_LIST", [1.0]),
        reserve_cash_fraction=get_float(env, "RESERVE_CASH_FRACTION", 0.5),
        safe_real_return=get_float(env, "SAFE_REAL_RETURN", 0.01),

        dd1=get_float(env, "DD1", 0.15),
        dd2=get_float(env, "DD2", 0.25),
        cut1=get_float(env, "CUT1", 0.50),
        cut2=get_float(env, "CUT2", 1.00),

        baseline_e_for_flex=get_float(env, "BASELINE_E_FOR_FLEX", 99_300.0),
        baseline_flex_pre=get_float(env, "BASELINE_FLEX_PRE", 20_000.0),
        baseline_net_post_ss=get_float(env, "BASELINE_NET_POST_SS", 52_895.0),
        baseline_flex_post=get_float(env, "BASELINE_FLEX_POST", 10_000.0),

        rm_open_age=get_int(env, "RM_OPEN_AGE", 62),
        home_value_real=get_float(env, "HOME_VALUE_REAL", 950_000.0),
        rm_plf_at_open=get_float(env, "RM_PLF_AT_OPEN", 0.40),
        rm_limit_real_growth=get_float(env, "RM_LIMIT_REAL_GROWTH", 0.015),
        rm_bal_real_rate=get_float(env, "RM_BAL_REAL_RATE", 0.015),
        rm_partial_cover=get_float(env, "RM_PARTIAL_COVER", 0.50),
        rm_repay_rate=get_float(env, "RM_REPAY_RATE", 0.15),
        payoff_dd_threshold=get_float(env, "PAYOFF_DD_THRESHOLD", 0.05),

        loan_amounts=get_list_ints(env, "LOAN_AMOUNTS", [0, 100000, 150000, 200000]),
        loan_real_rate=get_float(env, "LOAN_REAL_RATE", 0.03),
        loan_term_years=get_int(env, "LOAN_TERM_YEARS", 30),

        loan_bucket_real_return=get_float(env, "LOAN_BUCKET_REAL_RETURN", 0.01),
        loan_bucket_use_dd=get_float(env, "LOAN_BUCKET_USE_DD", 0.15),
        loan_bucket_partial_cover=get_float(env, "LOAN_BUCKET_PARTIAL_COVER", 0.50),

        output_dir=get_str(env, "OUTPUT_DIR", "outputs"),
    )

def generate_returns(cfg: Config, n_years: int) -> np.ndarray:
    rng = np.random.default_rng(cfg.seed)
    r = rng.normal(cfg.return_mu_real, cfg.return_vol_real, size=(cfg.n_sims, n_years))
    return np.clip(r, -0.99, None)

def build_withdrawals(cfg: Config, E: float, n_years: int, ages: np.ndarray) -> np.ndarray:
    """Planned schedule in real dollars.

    Two modes:

    1) income_applies_to_actual_spend == 1 (recommended):
       - w[t] is the planned *spending* level E (prorated for year 0).
       - SS + earned income are applied later against *actual spend*, reducing required withdrawals.
       - If income exceeds spending, the surplus is contributed back into assets.

    2) income_applies_to_actual_spend == 0 (legacy):
       - w[t] is the planned *asset withdrawal* amount: E reduced by SS and earned income.
    """
    w = np.zeros(n_years, dtype=float)

    if cfg.income_applies_to_actual_spend:
        w[0] = max(0.0, E * cfg.partial_year_fraction)
        for t in range(1, n_years):
            w[t] = max(0.0, E)
        return w

    # --- Legacy: reduce planned withdrawals by SS + earned income ---
    def earned_income(age: int) -> float:
        if cfg.earned_income_annual_real <= 0:
            return 0.0
        if age < cfg.earned_income_start_age or age > cfg.earned_income_end_age:
            return 0.0
        return cfg.earned_income_annual_real

    age0 = int(ages[0])
    ei0 = earned_income(age0) * cfg.partial_year_fraction
    ss0 = (cfg.ss_annual_real * cfg.partial_year_fraction) if age0 >= cfg.ss_start_age else 0.0
    w[0] = max(0.0, (E * cfg.partial_year_fraction) - ss0 - ei0)

    for t in range(1, n_years):
        age = int(ages[t])
        ei = earned_income(age)
        ss = cfg.ss_annual_real if age >= cfg.ss_start_age else 0.0
        w[t] = max(0.0, E - ss - ei)

    return w

def safe_targets(w: np.ndarray, t: int, reserve_years: float, cfg: Config) -> Tuple[float, float]:
    nxt = w[min(t + 1, len(w) - 1)]
    tgt_total = reserve_years * nxt
    tgt_cash = cfg.reserve_cash_fraction * tgt_total
    tgt_base = tgt_total - tgt_cash
    return tgt_cash, tgt_base

def death_weighted_success(fail_idx: np.ndarray, ages_model: np.ndarray) -> Tuple[float, float]:
    """Return (death-weighted success, success-to-age-99/horizon).

    Convention: fail_idx == len(ages_model) means 'never failed within horizon'.
    """
    ages_lt, p_death = mortality_weights()
    n_years = len(ages_model)

    # ruin_by_t[t] = fraction of sims ruined by time index t
    ruin_by_t = np.array([(fail_idx <= t).mean() for t in range(n_years)], dtype=float)

    age_to_t = {int(ages_model[t]): t for t in range(n_years)}
    ruin_by_age = np.array([ruin_by_t[age_to_t.get(int(a), n_years - 1)] for a in ages_lt], dtype=float)

    p_dw = float(np.sum(p_death * (1.0 - ruin_by_age)))
    p99 = float((fail_idx >= n_years).mean())
    return p_dw, p99

def amort_payment(principal: float, rate_real: float, term_years: int) -> float:
    if principal <= 0:
        return 0.0
    r = rate_real
    n = term_years
    return (r * principal) / (1.0 - (1.0 + r) ** (-n))

def loan_balance_after_k(principal: float, rate_real: float, payment: float, k: int) -> float:
    if principal <= 0:
        return 0.0
    r = rate_real
    return principal * (1.0 + r) ** k - payment * (((1.0 + r) ** k - 1.0) / r)

def simulate_once(cfg: Config, returns: np.ndarray, reserve_years: float, loan_amount: int, E: int) -> dict:
    n_years = returns.shape[1]
    ages = np.arange(cfg.start_age, cfg.start_age + n_years, dtype=int)

    # floor funded by assets (SS treated separately)
    floor_assets = np.full(n_years, cfg.floor_annual_real, dtype=float)
    floor_assets[0] = cfg.floor_annual_real * cfg.partial_year_fraction

    # flex calibration
    pre_flex_pct = cfg.baseline_flex_pre / cfg.baseline_e_for_flex
    post_flex_pct = cfg.baseline_flex_post / cfg.baseline_net_post_ss

    # RM
    rm_open_t = int(cfg.rm_open_age - cfg.start_age)
    rm_limit_open = cfg.home_value_real * cfg.rm_plf_at_open

    # loan
    has_loan = loan_amount > 0
    pay = amort_payment(loan_amount, cfg.loan_real_rate, cfg.loan_term_years)
    loan_bucket_r = cfg.loan_bucket_real_return

    # withdrawals
    w = build_withdrawals(cfg, float(E), n_years, ages)

    # init reserve
    tgt_cash0, tgt_base0 = safe_targets(w, 0, reserve_years, cfg)
    init_safe = min(tgt_cash0 + tgt_base0, cfg.start_portfolio)
    cash = np.full(cfg.n_sims, min(tgt_cash0, init_safe), dtype=float)
    base_treas = np.full(cfg.n_sims, max(0.0, init_safe - cash[0]), dtype=float)
    risky = np.full(cfg.n_sims, cfg.start_portfolio - init_safe, dtype=float)

    loan_bucket = np.zeros(cfg.n_sims, dtype=float)
    loan_bal = np.zeros(cfg.n_sims, dtype=float)
    if has_loan:
        loan_bucket[:] = float(loan_amount)
        loan_bal[:] = float(loan_amount)

    hwm = risky.copy()
    max_dd_risky = np.zeros(cfg.n_sims, dtype=float)

    # Total net liquid wealth (liquid assets incl. loan bucket, minus loan balance)
    total_net = cash + base_treas + risky + loan_bucket - loan_bal
    hwm_total = total_net.copy()
    max_dd_total = np.zeros(cfg.n_sims, dtype=float)

    rm_limit = np.zeros(cfg.n_sims, dtype=float)
    rm_bal = np.zeros(cfg.n_sims, dtype=float)

    rm_ever_used = np.zeros(cfg.n_sims, dtype=bool)

    failed = np.zeros(cfg.n_sims, dtype=bool)
    fail_idx = np.full(cfg.n_sims, n_years, dtype=int)

    def take_from(arr: np.ndarray, amount: np.ndarray) -> np.ndarray:
        take = np.minimum(amount, np.maximum(arr, 0.0))
        arr -= take
        return amount - take

    for t in range(n_years):
        # growth
        risky *= (1.0 + returns[:, t])
        cash *= (1.0 + cfg.safe_real_return)
        base_treas *= (1.0 + cfg.safe_real_return)
        if has_loan:
            loan_bucket *= (1.0 + loan_bucket_r)

        # drawdown
        hwm = np.maximum(hwm, risky)
        drawdown = np.where(hwm > 0, 1.0 - risky / hwm, 0.0)
        max_dd_risky = np.maximum(max_dd_risky, drawdown)
        total_net = cash + base_treas + risky + loan_bucket - loan_bal
        hwm_total = np.maximum(hwm_total, total_net)
        dd_total = 1.0 - np.divide(total_net, hwm_total, out=np.zeros_like(total_net), where=hwm_total>0)
        max_dd_total = np.maximum(max_dd_total, dd_total)

        # loan payment before RM open
        if has_loan and t < rm_open_t:
            rem = np.full(cfg.n_sims, pay, dtype=float)
            rem = take_from(cash, rem)
            rem = take_from(base_treas, rem)
            rem = take_from(risky, rem)

            allow = (drawdown >= cfg.loan_bucket_use_dd) & (~failed) & (rem > 1e-9)
            if np.any(allow):
                take = np.minimum(rem[allow], loan_bucket[allow])
                loan_bucket[allow] -= take
                rem[allow] -= take

            newly_failed = (~failed) & (rem > 1e-9)
            if np.any(newly_failed):
                failed[newly_failed] = True
                fail_idx[newly_failed] = t

            k = t + 1
            loan_bal[:] = loan_balance_after_k(float(loan_amount), cfg.loan_real_rate, pay, k) if k <= cfg.loan_term_years else 0.0

        # RM open + lien payoff
        if t == rm_open_t:
            rm_limit[:] = rm_limit_open * (1.0 + cfg.rm_limit_real_growth)

            if has_loan:
                payoff = loan_bal.copy()
                risky_first = (drawdown <= cfg.payoff_dd_threshold)

                if np.any(risky_first):
                    payoff[risky_first] = take_from(risky[risky_first], payoff[risky_first])

                if np.any(~risky_first):
                    avail_rm = np.maximum(0.0, rm_limit[~risky_first] - rm_bal[~risky_first])
                    take = np.minimum(payoff[~risky_first], avail_rm)
                    rm_bal[~risky_first] += take
                    payoff[~risky_first] -= take

                if np.any(risky_first):
                    avail_rm = np.maximum(0.0, rm_limit[risky_first] - rm_bal[risky_first])
                    take = np.minimum(payoff[risky_first], avail_rm)
                    rm_bal[risky_first] += take
                    payoff[risky_first] -= take
                if np.any(~risky_first):
                    payoff[~risky_first] = take_from(risky[~risky_first], payoff[~risky_first])

                payoff = take_from(base_treas, payoff)
                payoff = take_from(cash, payoff)
                payoff = take_from(loan_bucket, payoff)

                newly_failed = (~failed) & (payoff > 1e-9)
                if np.any(newly_failed):
                    failed[newly_failed] = True
                    fail_idx[newly_failed] = t

                loan_bal[:] = 0.0

        # RM growth
        if t >= rm_open_t:
            rm_limit *= (1.0 + cfg.rm_limit_real_growth)
            rm_bal *= (1.0 + cfg.rm_bal_real_rate)

        # desired spend with guardrails
        flex_pct = pre_flex_pct if ages[t] < cfg.ss_start_age else post_flex_pct
        flex_amt = min(flex_pct * w[t], w[t])
        floor_amt = w[t] - flex_amt

        cut = np.zeros(cfg.n_sims, dtype=float)
        cut = np.where(drawdown >= cfg.dd2, cfg.cut2, cut)
        cut = np.where((drawdown >= cfg.dd1) & (drawdown < cfg.dd2), cfg.cut1, cut)

        desired = floor_amt + flex_amt * (1.0 - cut)

        # feasibility
        avail_rm = np.maximum(0.0, rm_limit - rm_bal)
        accessible_loan = np.where(drawdown >= cfg.loan_bucket_use_dd, loan_bucket, 0.0)
        max_feasible = cash + base_treas + np.maximum(risky, 0.0) + avail_rm + accessible_loan

        floor_need = floor_assets[t]

        # --- INCOME APPLICATION (SS + earned income) ---
        # When enabled, income reduces what must be funded from assets each year.
        # If income exceeds desired spending, the surplus is contributed back into assets.
        income_scalar = 0.0
        if cfg.income_applies_to_actual_spend:
            age = int(ages[t])

            # Earned income (real)
            if cfg.earned_income_annual_real > 0 and (cfg.earned_income_start_age <= age <= cfg.earned_income_end_age):
                ei = cfg.earned_income_annual_real
            else:
                ei = 0.0

            # Social Security (real)
            ss = cfg.ss_annual_real if age >= cfg.ss_start_age else 0.0

            # Prorate in year 0
            if t == 0:
                ei *= cfg.partial_year_fraction
                ss *= cfg.partial_year_fraction

            income_scalar = ss + ei

        if income_scalar > 0:
            income = np.full(cfg.n_sims, income_scalar, dtype=float)

            # Reduce desired spend by income to get asset-funded desired spend
            asset_desired = np.maximum(0.0, desired - income)

            # Floor is expressed in spending terms; income reduces what must be funded from assets.
            floor_need_assets = np.maximum(0.0, floor_need - income)

            # Income surplus (income > desired spend) becomes a contribution to assets
            surplus = np.maximum(0.0, income - desired)
            if np.any(surplus > 0):
                if cfg.surplus_allocation == "risky_first":
                    risky += surplus
                else:
                    tgt_cash, tgt_base = safe_targets(w, t, reserve_years, cfg)

                    add_cash = np.minimum(np.maximum(0.0, tgt_cash - cash), surplus)
                    cash += add_cash
                    surplus -= add_cash

                    add_base = np.minimum(np.maximum(0.0, tgt_base - base_treas), surplus)
                    base_treas += add_base
                    surplus -= add_base

                    risky += surplus
        else:
            asset_desired = desired
            floor_need_assets = floor_need

        # feasibility (asset-funded)
        newly_failed = (~failed) & (max_feasible < floor_need_assets - 1e-9)
        if np.any(newly_failed):
            failed[newly_failed] = True
            fail_idx[newly_failed] = t

        spend_assets = np.minimum(asset_desired, max_feasible)
        spend_assets = np.where(~failed, np.maximum(spend_assets, floor_need_assets), 0.0)

        # funding order
        rem = spend_assets
        rem = take_from(cash, rem)
        rem = take_from(base_treas, rem)

        allow = (drawdown >= cfg.loan_bucket_use_dd) & (~failed) & (loan_bucket > 0)
        take_loan = np.where(allow, np.minimum(rem * cfg.loan_bucket_partial_cover, loan_bucket), 0.0)
        loan_bucket -= take_loan
        rem -= take_loan

        avail_rm = np.maximum(0.0, rm_limit - rm_bal)
        take_rm = np.where((drawdown >= cfg.dd2) & (~failed), np.minimum(rem * cfg.rm_partial_cover, avail_rm), 0.0)
        rm_bal += take_rm
        rem -= take_rm

        rem = take_from(risky, rem)

        avail_rm = np.maximum(0.0, rm_limit - rm_bal)
        take_rm2 = np.minimum(rem, avail_rm)
        rm_bal += take_rm2
        rem -= take_rm2

        allow2 = (drawdown >= cfg.loan_bucket_use_dd) & (~failed) & (rem > 1e-9)
        if np.any(allow2):
            take = np.minimum(rem[allow2], loan_bucket[allow2])
            loan_bucket[allow2] -= take
            rem[allow2] -= take

        # refill reserve in good years
        good = (drawdown < cfg.dd1) & (~failed)
        tgt_cash, tgt_base = safe_targets(w, t, reserve_years, cfg)

        need_cash = np.maximum(0.0, tgt_cash - cash)
        add_cash = np.where(good, np.minimum(need_cash, np.maximum(risky, 0.0)), 0.0)
        risky -= add_cash
        cash += add_cash

        need_base = np.maximum(0.0, tgt_base - base_treas)
        add_base = np.where(good, np.minimum(need_base, np.maximum(risky, 0.0)), 0.0)
        risky -= add_base
        base_treas += add_base

        # repay RM at new highs
        recovered = (drawdown < 1e-9) & good & (rm_bal > 0)
        repay_amt = np.where(recovered, rm_bal * cfg.rm_repay_rate, 0.0)
        repay_take = np.minimum(repay_amt, np.maximum(risky, 0.0))
        risky -= repay_take
        rm_bal -= repay_take

        rm_ever_used = rm_ever_used | (rm_bal > 0)

    ages_model = np.arange(cfg.start_age, cfg.start_age + n_years, dtype=int)
    p_dw, p99 = death_weighted_success(fail_idx, ages_model)

    # Remaining home equity (real dollars) at end of horizon
    home_equity_remaining = np.maximum(0.0, cfg.home_value_real - rm_bal)

    # Terminal (end-of-horizon) balances (real dollars)
    risky_end_median = float(np.median(risky))
    total_net_end = cash + base_treas + risky + loan_bucket - loan_bal
    total_net_end_median = float(np.median(total_net_end))
    net_worth_end = total_net_end + home_equity_remaining
    net_worth_end_median = float(np.median(net_worth_end))

    return {
        "p_success_death_weighted": float(p_dw),
        "p_success_to_age_99": float(p99),

        # Drawdown medians (per-path max drawdown; median across sims)
        "median_max_dd_risky": float(np.median(max_dd_risky)),
        "median_max_dd_total": float(np.median(max_dd_total)),

        # RM/equity medians
        "home_equity_remaining_median": float(np.median(home_equity_remaining)),
        "p_any_rm_draw": float(np.mean(rm_ever_used)),
        "rm_balance_end_median": float(np.median(rm_bal)),

        # Terminal balance medians
        "risky_end_median": risky_end_median,
        "total_net_end_median": total_net_end_median,
        "net_worth_end_median": net_worth_end_median,
    }
def find_max_E(cfg: Config, returns: np.ndarray, reserve_years: float, loan_amount: int) -> tuple[int, dict]:
    """Binary search the maximum constant annual real spending (E) that meets the target success probability.

    Returns: (best_E, metrics_dict_at_best_E)
    """

    def objective_p(metrics: dict) -> float:
        m = getattr(cfg, "optimize_success_metric", "death_weighted")
        p_dw = float(metrics["p_success_death_weighted"])
        p99 = float(metrics["p_success_to_age_99"])
        if m == "age_99":
            return p99
        if m == "both_min":
            return min(p_dw, p99)
        if m == "both_weighted":
            w = float(getattr(cfg, "both_weight", 0.5))
            return w * p_dw + (1.0 - w) * p99
        return p_dw

    target = float(cfg.target_success_death_weighted)
    lo, hi = int(cfg.e_lo), int(cfg.e_hi)

    # Ensure lo is evaluated (so we can return a meaningful metrics dict even if nothing passes)
    metrics_lo = simulate_once(cfg, returns, reserve_years, loan_amount, lo)
    if objective_p(metrics_lo) < target:
        return lo, metrics_lo

    # Expand hi upward while still meeting target, so the binary search bracket is valid.
    metrics_hi = simulate_once(cfg, returns, reserve_years, loan_amount, hi)
    while objective_p(metrics_hi) >= target and hi < 600_000:
        lo = hi
        metrics_lo = metrics_hi
        hi = int(hi * 1.25)
        metrics_hi = simulate_once(cfg, returns, reserve_years, loan_amount, hi)

    # Now binary search between current lo (pass) and hi (fail or cap).
    for _ in range(int(cfg.e_search_iters)):
        mid = (lo + hi) // 2
        metrics_mid = simulate_once(cfg, returns, reserve_years, loan_amount, int(mid))
        if objective_p(metrics_mid) >= target:
            lo = mid
            metrics_lo = metrics_mid
        else:
            hi = mid - 1

    return int(lo), metrics_lo


def print_table(df: pd.DataFrame) -> None:
    """Print DataFrame with fixed-point formatting (no scientific notation)."""
    def ff(x: float) -> str:
        if x != x:  # nan
            return ""
        if abs(x) < 1:
            return f"{x:.6f}"
        return f"{x:,.2f}"
    print(df.to_string(index=False, float_format=ff))

def main() -> None:
    env = load_env(".env")
    cfg = read_config(env)

    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path(cfg.output_dir) / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    n_years = 99 - cfg.start_age + 1
    returns = generate_returns(cfg, n_years)

    rows = []
    start_portfolios = cfg.start_portfolios if cfg.start_portfolios else [cfg.start_portfolio]

    for start_p in start_portfolios:
        cfg_run = replace(cfg, start_portfolio=float(start_p))
        for reserve_years in cfg.reserve_years_list:
            for loan_amount in cfg.loan_amounts:
                if cfg.mode == "single":
                    metrics = simulate_once(cfg_run, returns, float(reserve_years), int(loan_amount), int(cfg.e_fixed))
                    row = {
                        "start_portfolio": float(start_p),
                        "reserve_years": float(reserve_years),
                        "loan_amount": int(loan_amount),
                        "E_real_per_year": int(cfg.e_fixed),
                        "p_success_death_weighted": metrics["p_success_death_weighted"],
                        "p_success_to_age_99": metrics["p_success_to_age_99"],
                    }
                else:
                    max_e, metrics = find_max_E(cfg_run, returns, float(reserve_years), int(loan_amount))
                    row = {
                        "start_portfolio": float(start_p),
                        "reserve_years": float(reserve_years),
                        "loan_amount": int(loan_amount),
                        "max_E_real_per_year": int(max_e),
                        "p_success_death_weighted": metrics["p_success_death_weighted"],
                        "p_success_to_age_99": metrics["p_success_to_age_99"],
                    }

                row.update({k: v for k, v in metrics.items() if k not in row})
                rows.append(row)

    df = pd.DataFrame(rows).sort_values(["start_portfolio", "reserve_years", "loan_amount"]).reset_index(drop=True)

    if cfg.mode == "single":
        print("\n=== Summary (fixed E evaluation) ===")
        print(f"E (real $/yr): {cfg.e_fixed:.0f}\n")
    else:
        print("\n=== Summary (max E at target success) ===")
        print(f"Target success: {cfg.target_success_death_weighted:.0%} | optimize metric: {cfg.optimize_success_metric}\n")
    pretty = df.copy()
    pretty["p_success_death_weighted"] = (pretty["p_success_death_weighted"] * 100).round(1).astype(str) + "%"
    pretty["p_success_to_age_99"] = (pretty["p_success_to_age_99"] * 100).round(1).astype(str) + "%"
    print_table(pretty)

    df.to_csv(out_root / "summary.csv", index=False)
    pd.DataFrame([{k: env[k] for k in sorted(env.keys())}]).to_csv(out_root / "settings.csv", index=False)
    (out_root / "notes.txt").write_text(
        "\n".join([
            f"run_id: {run_id}",
            f"n_sims: {cfg.n_sims}",
            f"return_mu_real: {cfg.return_mu_real}",
            f"return_vol_real: {cfg.return_vol_real}",
            f"reserve_years_list: {cfg.reserve_years_list}",
            f"loan_amounts: {cfg.loan_amounts}",
            "outputs: summary.csv, settings.csv",
        ]) + "\n"
    )

    print(f"\nWrote: {out_root / 'summary.csv'}")
    print(f"Wrote: {out_root / 'settings.csv'}")

if __name__ == "__main__":
    main()