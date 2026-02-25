"""Core year-by-year Monte Carlo simulation engine.

Ported from legacy simulate.py — preserves exact numerical behavior.
"""

from typing import List, Tuple

import numpy as np

from .accounts import take_from, safe_targets
from .guardrails import compute_cuts
from .loan import amort_payment, loan_balance_after_k
from .mortality import death_weighted_success


def build_withdrawals(
    E: float,
    n_years: int,
    ages: np.ndarray,
    partial_year_fraction: float,
    income_applies_to_actual_spend: bool,
    ss_annual_real: float,
    ss_start_age: int,
    earned_income_annual_real: float,
    earned_income_start_age: int,
    earned_income_end_age: int,
) -> np.ndarray:
    w = np.zeros(n_years, dtype=float)

    if income_applies_to_actual_spend:
        w[0] = max(0.0, E * partial_year_fraction)
        for t in range(1, n_years):
            w[t] = max(0.0, E)
        return w

    # Legacy mode: reduce planned withdrawals by SS + earned income
    def earned_income(age: int) -> float:
        if earned_income_annual_real <= 0:
            return 0.0
        if age < earned_income_start_age or age > earned_income_end_age:
            return 0.0
        return earned_income_annual_real

    age0 = int(ages[0])
    ei0 = earned_income(age0) * partial_year_fraction
    ss0 = (ss_annual_real * partial_year_fraction) if age0 >= ss_start_age else 0.0
    w[0] = max(0.0, (E * partial_year_fraction) - ss0 - ei0)

    for t in range(1, n_years):
        age = int(ages[t])
        ei = earned_income(age)
        ss = ss_annual_real if age >= ss_start_age else 0.0
        w[t] = max(0.0, E - ss - ei)

    return w


def simulate_once(
    # Core params
    n_sims: int,
    start_portfolio: float,
    start_age: int,
    partial_year_fraction: float,
    seed: int,
    # Returns (pre-generated)
    returns: np.ndarray,
    # Reserve
    reserve_years: float,
    reserve_cash_fraction: float,
    safe_real_return: float,
    # Spending
    E: int,
    floor_annual_real: float,
    income_applies_to_actual_spend: bool,
    ss_annual_real: float,
    ss_start_age: int,
    earned_income_annual_real: float,
    earned_income_start_age: int,
    earned_income_end_age: int,
    allow_surplus_savings: bool,
    surplus_allocation: str,
    # Guardrails
    dd1: float,
    dd2: float,
    cut1: float,
    cut2: float,
    baseline_e_for_flex: float,
    baseline_flex_pre: float,
    baseline_net_post_ss: float,
    baseline_flex_post: float,
    # Reverse mortgage
    rm_open_age: int,
    home_value_real: float,
    rm_plf_at_open: float,
    rm_limit_real_growth: float,
    rm_bal_real_rate: float,
    rm_partial_cover: float,
    rm_repay_rate: float,
    payoff_dd_threshold: float,
    # Loan
    loan_amount: int,
    loan_real_rate: float,
    loan_term_years: int,
    loan_bucket_real_return: float,
    loan_bucket_use_dd: float,
    loan_bucket_partial_cover: float,
) -> dict:
    n_years = returns.shape[1]
    ages = np.arange(start_age, start_age + n_years, dtype=int)

    # floor funded by assets
    floor_assets = np.full(n_years, floor_annual_real, dtype=float)
    floor_assets[0] = floor_annual_real * partial_year_fraction

    # flex calibration
    pre_flex_pct = baseline_flex_pre / baseline_e_for_flex if baseline_e_for_flex > 0 else 0.0
    post_flex_pct = baseline_flex_post / baseline_net_post_ss if baseline_net_post_ss > 0 else 0.0

    # RM
    rm_open_t = int(rm_open_age - start_age)
    rm_limit_open = home_value_real * rm_plf_at_open

    # loan
    has_loan = loan_amount > 0
    pay = amort_payment(loan_amount, loan_real_rate, loan_term_years)
    loan_bucket_r = loan_bucket_real_return

    # withdrawals
    w = build_withdrawals(
        float(E), n_years, ages, partial_year_fraction,
        income_applies_to_actual_spend, ss_annual_real, ss_start_age,
        earned_income_annual_real, earned_income_start_age, earned_income_end_age,
    )

    # init reserve
    tgt_cash0, tgt_base0 = safe_targets(w, 0, reserve_years, reserve_cash_fraction)
    init_safe = min(tgt_cash0 + tgt_base0, start_portfolio)
    cash = np.full(n_sims, min(tgt_cash0, init_safe), dtype=float)
    base_treas = np.full(n_sims, max(0.0, init_safe - cash[0]), dtype=float)
    risky = np.full(n_sims, start_portfolio - init_safe, dtype=float)

    loan_bucket = np.zeros(n_sims, dtype=float)
    loan_bal = np.zeros(n_sims, dtype=float)
    if has_loan:
        loan_bucket[:] = float(loan_amount)
        loan_bal[:] = float(loan_amount)

    hwm = risky.copy()
    max_dd_risky = np.zeros(n_sims, dtype=float)

    total_net = cash + base_treas + risky + loan_bucket - loan_bal
    hwm_total = total_net.copy()
    max_dd_total = np.zeros(n_sims, dtype=float)

    rm_limit = np.zeros(n_sims, dtype=float)
    rm_bal = np.zeros(n_sims, dtype=float)
    rm_ever_used = np.zeros(n_sims, dtype=bool)

    failed = np.zeros(n_sims, dtype=bool)
    fail_idx = np.full(n_sims, n_years, dtype=int)

    for t in range(n_years):
        # growth
        risky *= (1.0 + returns[:, t])
        cash *= (1.0 + safe_real_return)
        base_treas *= (1.0 + safe_real_return)
        if has_loan:
            loan_bucket *= (1.0 + loan_bucket_r)

        # drawdown
        hwm = np.maximum(hwm, risky)
        drawdown = np.where(hwm > 0, 1.0 - risky / hwm, 0.0)
        max_dd_risky = np.maximum(max_dd_risky, drawdown)
        total_net = cash + base_treas + risky + loan_bucket - loan_bal
        hwm_total = np.maximum(hwm_total, total_net)
        dd_total = 1.0 - np.divide(
            total_net, hwm_total, out=np.zeros_like(total_net), where=hwm_total > 0
        )
        max_dd_total = np.maximum(max_dd_total, dd_total)

        # loan payment before RM open
        if has_loan and t < rm_open_t:
            rem = np.full(n_sims, pay, dtype=float)
            rem = take_from(cash, rem)
            rem = take_from(base_treas, rem)
            rem = take_from(risky, rem)

            allow = (drawdown >= loan_bucket_use_dd) & (~failed) & (rem > 1e-9)
            if np.any(allow):
                take = np.minimum(rem[allow], loan_bucket[allow])
                loan_bucket[allow] -= take
                rem[allow] -= take

            newly_failed = (~failed) & (rem > 1e-9)
            if np.any(newly_failed):
                failed[newly_failed] = True
                fail_idx[newly_failed] = t

            k = t + 1
            loan_bal[:] = (
                loan_balance_after_k(float(loan_amount), loan_real_rate, pay, k)
                if k <= loan_term_years
                else 0.0
            )

        # RM open + lien payoff
        if t == rm_open_t:
            rm_limit[:] = rm_limit_open * (1.0 + rm_limit_real_growth)

            if has_loan:
                payoff = loan_bal.copy()
                risky_first = drawdown <= payoff_dd_threshold

                if np.any(risky_first):
                    payoff[risky_first] = take_from(
                        risky[risky_first], payoff[risky_first]
                    )

                if np.any(~risky_first):
                    avail_rm = np.maximum(
                        0.0, rm_limit[~risky_first] - rm_bal[~risky_first]
                    )
                    take = np.minimum(payoff[~risky_first], avail_rm)
                    rm_bal[~risky_first] += take
                    payoff[~risky_first] -= take

                if np.any(risky_first):
                    avail_rm = np.maximum(
                        0.0, rm_limit[risky_first] - rm_bal[risky_first]
                    )
                    take = np.minimum(payoff[risky_first], avail_rm)
                    rm_bal[risky_first] += take
                    payoff[risky_first] -= take
                if np.any(~risky_first):
                    payoff[~risky_first] = take_from(
                        risky[~risky_first], payoff[~risky_first]
                    )

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
            rm_limit *= (1.0 + rm_limit_real_growth)
            rm_bal *= (1.0 + rm_bal_real_rate)

        # desired spend with guardrails
        flex_pct = pre_flex_pct if ages[t] < ss_start_age else post_flex_pct
        flex_amt = min(flex_pct * w[t], w[t])
        floor_amt = w[t] - flex_amt

        cut = compute_cuts(drawdown, dd1, dd2, cut1, cut2)
        desired = floor_amt + flex_amt * (1.0 - cut)

        # feasibility
        avail_rm = np.maximum(0.0, rm_limit - rm_bal)
        accessible_loan = np.where(drawdown >= loan_bucket_use_dd, loan_bucket, 0.0)
        max_feasible = (
            cash + base_treas + np.maximum(risky, 0.0) + avail_rm + accessible_loan
        )

        floor_need = floor_assets[t]

        # income application
        income_scalar = 0.0
        if income_applies_to_actual_spend:
            age = int(ages[t])
            if (
                earned_income_annual_real > 0
                and earned_income_start_age <= age <= earned_income_end_age
            ):
                ei = earned_income_annual_real
            else:
                ei = 0.0
            ss = ss_annual_real if age >= ss_start_age else 0.0
            if t == 0:
                ei *= partial_year_fraction
                ss *= partial_year_fraction
            income_scalar = ss + ei

        if income_scalar > 0:
            income = np.full(n_sims, income_scalar, dtype=float)
            asset_desired = np.maximum(0.0, desired - income)
            floor_need_assets = np.maximum(0.0, floor_need - income)
            surplus = np.maximum(0.0, income - desired)
            if np.any(surplus > 0):
                if surplus_allocation == "risky_first":
                    risky += surplus
                else:
                    tgt_cash, tgt_base = safe_targets(
                        w, t, reserve_years, reserve_cash_fraction
                    )
                    add_cash = np.minimum(
                        np.maximum(0.0, tgt_cash - cash), surplus
                    )
                    cash += add_cash
                    surplus -= add_cash
                    add_base = np.minimum(
                        np.maximum(0.0, tgt_base - base_treas), surplus
                    )
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
        spend_assets = np.where(
            ~failed, np.maximum(spend_assets, floor_need_assets), 0.0
        )

        # funding order
        rem = spend_assets
        rem = take_from(cash, rem)
        rem = take_from(base_treas, rem)

        allow = (drawdown >= loan_bucket_use_dd) & (~failed) & (loan_bucket > 0)
        take_loan = np.where(
            allow,
            np.minimum(rem * loan_bucket_partial_cover, loan_bucket),
            0.0,
        )
        loan_bucket -= take_loan
        rem -= take_loan

        avail_rm = np.maximum(0.0, rm_limit - rm_bal)
        take_rm = np.where(
            (drawdown >= dd2) & (~failed),
            np.minimum(rem * rm_partial_cover, avail_rm),
            0.0,
        )
        rm_bal += take_rm
        rem -= take_rm

        rem = take_from(risky, rem)

        avail_rm = np.maximum(0.0, rm_limit - rm_bal)
        take_rm2 = np.minimum(rem, avail_rm)
        rm_bal += take_rm2
        rem -= take_rm2

        allow2 = (drawdown >= loan_bucket_use_dd) & (~failed) & (rem > 1e-9)
        if np.any(allow2):
            take = np.minimum(rem[allow2], loan_bucket[allow2])
            loan_bucket[allow2] -= take
            rem[allow2] -= take

        # refill reserve in good years
        good = (drawdown < dd1) & (~failed)
        tgt_cash_r, tgt_base_r = safe_targets(
            w, t, reserve_years, reserve_cash_fraction
        )

        need_cash = np.maximum(0.0, tgt_cash_r - cash)
        add_cash = np.where(good, np.minimum(need_cash, np.maximum(risky, 0.0)), 0.0)
        risky -= add_cash
        cash += add_cash

        need_base = np.maximum(0.0, tgt_base_r - base_treas)
        add_base = np.where(good, np.minimum(need_base, np.maximum(risky, 0.0)), 0.0)
        risky -= add_base
        base_treas += add_base

        # repay RM at new highs
        recovered = (drawdown < 1e-9) & good & (rm_bal > 0)
        repay_amt = np.where(recovered, rm_bal * rm_repay_rate, 0.0)
        repay_take = np.minimum(repay_amt, np.maximum(risky, 0.0))
        risky -= repay_take
        rm_bal -= repay_take

        rm_ever_used = rm_ever_used | (rm_bal > 0)

    ages_model = np.arange(start_age, start_age + n_years, dtype=int)
    p_dw, p99 = death_weighted_success(fail_idx, ages_model)

    home_equity_remaining = np.maximum(0.0, home_value_real - rm_bal)
    risky_end_median = float(np.median(risky))
    total_net_end = cash + base_treas + risky + loan_bucket - loan_bal
    total_net_end_median = float(np.median(total_net_end))
    net_worth_end = total_net_end + home_equity_remaining
    net_worth_end_median = float(np.median(net_worth_end))

    return {
        "p_success_death_weighted": float(p_dw),
        "p_success_to_age_99": float(p99),
        "median_max_dd_risky": float(np.median(max_dd_risky)),
        "median_max_dd_total": float(np.median(max_dd_total)),
        "home_equity_remaining_median": float(np.median(home_equity_remaining)),
        "p_any_rm_draw": float(np.mean(rm_ever_used)),
        "rm_balance_end_median": float(np.median(rm_bal)),
        "risky_end_median": risky_end_median,
        "total_net_end_median": total_net_end_median,
        "net_worth_end_median": net_worth_end_median,
    }
