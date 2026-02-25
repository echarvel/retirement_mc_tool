"""FastAPI application — stateless simulation engine."""

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models.schemas import (
    GridPointResult,
    SimulationRequest,
    SimulationResponse,
)
from .simulation.engine import simulate_once
from .simulation.optimizer import find_max_E
from .simulation.returns import generate_returns

app = FastAPI(title="Retirement MC Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


def _run_simulation(req: SimulationRequest) -> SimulationResponse:
    """Synchronous simulation — runs in thread pool."""
    cfg = req.scenario
    n_years = 99 - cfg.start_age + 1
    returns = generate_returns(
        cfg.seed, cfg.n_sims, n_years, cfg.return_mu_real, cfg.return_vol_real
    )

    # Common kwargs for simulate_once (everything except E, returns, start_portfolio,
    # reserve_years, loan_amount)
    sim_kwargs = dict(
        n_sims=cfg.n_sims,
        start_age=cfg.start_age,
        partial_year_fraction=cfg.partial_year_fraction,
        seed=cfg.seed,
        reserve_cash_fraction=cfg.reserve_cash_fraction,
        safe_real_return=cfg.safe_real_return,
        floor_annual_real=cfg.floor_annual_real,
        income_applies_to_actual_spend=cfg.income_applies_to_actual_spend,
        ss_annual_real=cfg.ss_annual_real,
        ss_start_age=cfg.ss_start_age,
        earned_income_annual_real=cfg.earned_income_annual_real,
        earned_income_start_age=cfg.earned_income_start_age,
        earned_income_end_age=cfg.earned_income_end_age,
        allow_surplus_savings=cfg.allow_surplus_savings,
        surplus_allocation=cfg.surplus_allocation,
        dd1=cfg.dd1,
        dd2=cfg.dd2,
        cut1=cfg.cut1,
        cut2=cfg.cut2,
        baseline_e_for_flex=cfg.baseline_e_for_flex,
        baseline_flex_pre=cfg.baseline_flex_pre,
        baseline_net_post_ss=cfg.baseline_net_post_ss,
        baseline_flex_post=cfg.baseline_flex_post,
        rm_open_age=cfg.rm_open_age,
        home_value_real=cfg.home_value_real,
        rm_plf_at_open=cfg.rm_plf_at_open,
        rm_limit_real_growth=cfg.rm_limit_real_growth,
        rm_bal_real_rate=cfg.rm_bal_real_rate,
        rm_partial_cover=cfg.rm_partial_cover,
        rm_repay_rate=cfg.rm_repay_rate,
        payoff_dd_threshold=cfg.payoff_dd_threshold,
        loan_real_rate=cfg.loan_real_rate,
        loan_term_years=cfg.loan_term_years,
        loan_bucket_real_return=cfg.loan_bucket_real_return,
        loan_bucket_use_dd=cfg.loan_bucket_use_dd,
        loan_bucket_partial_cover=cfg.loan_bucket_partial_cover,
    )

    rows = []
    for start_p in cfg.start_portfolios:
        for reserve_years in cfg.reserve_years_list:
            for loan_amount in cfg.loan_amounts:
                kw = {
                    **sim_kwargs,
                    "start_portfolio": float(start_p),
                    "reserve_years": float(reserve_years),
                    "loan_amount": int(loan_amount),
                    "returns": returns,
                }

                if cfg.mode == "single":
                    metrics = simulate_once(E=int(cfg.e_fixed), **kw)
                    row = GridPointResult(
                        start_portfolio=float(start_p),
                        reserve_years=float(reserve_years),
                        loan_amount=int(loan_amount),
                        E_real_per_year=int(cfg.e_fixed),
                        **metrics,
                    )
                else:
                    max_e, metrics = find_max_E(
                        returns=returns,
                        target=float(cfg.target_success_death_weighted),
                        e_lo=cfg.e_lo,
                        e_hi=cfg.e_hi,
                        e_search_iters=cfg.e_search_iters,
                        optimize_success_metric=cfg.optimize_success_metric,
                        both_weight=cfg.both_weight,
                        **{k: v for k, v in kw.items() if k != "returns"},
                    )
                    row = GridPointResult(
                        start_portfolio=float(start_p),
                        reserve_years=float(reserve_years),
                        loan_amount=int(loan_amount),
                        max_E_real_per_year=int(max_e),
                        **metrics,
                    )
                rows.append(row)

    return SimulationResponse(
        run_id=req.run_id,
        status="completed",
        results=rows,
        total_grid_points=len(rows),
    )


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(req: SimulationRequest):
    return await asyncio.to_thread(_run_simulation, req)
