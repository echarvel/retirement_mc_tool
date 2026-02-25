"""Pydantic request/response models for the simulation API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ScenarioConfig(BaseModel):
    """Full scenario configuration sent from the frontend."""

    # Core
    seed: int = 424242
    n_sims: int = 25000
    start_age: int = 53
    partial_year_fraction: float = 0.894444

    # Returns
    return_mu_real: float = 0.04
    return_vol_real: float = 0.10

    # Optimization
    mode: str = "optimize"  # "optimize" | "single"
    e_fixed: float = 80000.0
    target_success_death_weighted: float = 0.90
    e_lo: int = 40000
    e_hi: int = 220000
    e_search_iters: int = 19
    optimize_success_metric: str = "death_weighted"
    both_weight: float = 0.5

    # Income
    ss_annual_real: float = 46405.0
    ss_start_age: int = 63
    earned_income_annual_real: float = 0.0
    earned_income_start_age: int = 54
    earned_income_end_age: int = 62
    income_applies_to_actual_spend: bool = True
    allow_surplus_savings: bool = False
    surplus_allocation: str = "reserve_first"

    # Spending
    floor_annual_real: float = 60000.0

    # Reserve
    reserve_cash_fraction: float = 0.5
    safe_real_return: float = 0.01

    # Guardrails
    dd1: float = 0.15
    dd2: float = 0.25
    cut1: float = 0.50
    cut2: float = 1.00
    baseline_e_for_flex: float = 99300.0
    baseline_flex_pre: float = 20000.0
    baseline_net_post_ss: float = 52895.0
    baseline_flex_post: float = 10000.0

    # Reverse mortgage
    rm_open_age: int = 62
    home_value_real: float = 950000.0
    rm_plf_at_open: float = 0.40
    rm_limit_real_growth: float = 0.015
    rm_bal_real_rate: float = 0.015
    rm_partial_cover: float = 0.50
    rm_repay_rate: float = 0.15
    payoff_dd_threshold: float = 0.05

    # Loan
    loan_real_rate: float = 0.03
    loan_term_years: int = 30
    loan_bucket_real_return: float = 0.01
    loan_bucket_use_dd: float = 0.15
    loan_bucket_partial_cover: float = 0.50

    # Sweep grid
    start_portfolios: List[float] = Field(default_factory=lambda: [1477000.0])
    reserve_years_list: List[float] = Field(default_factory=lambda: [1.0])
    loan_amounts: List[int] = Field(default_factory=lambda: [0])


class SimulationRequest(BaseModel):
    """Request body for POST /simulate."""

    scenario: ScenarioConfig
    run_id: Optional[str] = None


class GridPointResult(BaseModel):
    start_portfolio: float
    reserve_years: float
    loan_amount: int
    max_E_real_per_year: Optional[int] = None
    E_real_per_year: Optional[int] = None
    p_success_death_weighted: float
    p_success_to_age_99: float
    median_max_dd_risky: float
    median_max_dd_total: float
    home_equity_remaining_median: float
    p_any_rm_draw: float
    rm_balance_end_median: float
    risky_end_median: float
    total_net_end_median: float
    net_worth_end_median: float


class SimulationResponse(BaseModel):
    """Response body for POST /simulate."""

    run_id: Optional[str] = None
    status: str = "completed"
    results: List[GridPointResult]
    total_grid_points: int
