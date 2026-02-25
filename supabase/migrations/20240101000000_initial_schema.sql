-- Phase 1: Core tables for scenarios, simulation runs, and results
-- All tables use RLS with auth.uid() for per-user data isolation

-- =============================================================================
-- scenarios
-- =============================================================================
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Untitled Scenario',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Core params
    start_age INT NOT NULL DEFAULT 53,
    partial_year_fraction DOUBLE PRECISION NOT NULL DEFAULT 0.894444,

    -- Returns
    return_mu_real DOUBLE PRECISION NOT NULL DEFAULT 0.04,
    return_vol_real DOUBLE PRECISION NOT NULL DEFAULT 0.10,

    -- Simulation
    seed INT NOT NULL DEFAULT 424242,
    n_sims INT NOT NULL DEFAULT 25000,

    -- Optimization
    mode TEXT NOT NULL DEFAULT 'optimize' CHECK (mode IN ('optimize', 'single')),
    e_fixed DOUBLE PRECISION NOT NULL DEFAULT 80000,
    target_success_death_weighted DOUBLE PRECISION NOT NULL DEFAULT 0.90,
    e_lo INT NOT NULL DEFAULT 40000,
    e_hi INT NOT NULL DEFAULT 220000,
    e_search_iters INT NOT NULL DEFAULT 19,
    optimize_success_metric TEXT NOT NULL DEFAULT 'death_weighted'
        CHECK (optimize_success_metric IN ('death_weighted', 'age_99', 'both_min', 'both_weighted')),
    both_weight DOUBLE PRECISION NOT NULL DEFAULT 0.5,

    -- Income
    ss_annual_real DOUBLE PRECISION NOT NULL DEFAULT 46405,
    ss_start_age INT NOT NULL DEFAULT 63,
    earned_income_annual_real DOUBLE PRECISION NOT NULL DEFAULT 0,
    earned_income_start_age INT NOT NULL DEFAULT 54,
    earned_income_end_age INT NOT NULL DEFAULT 62,
    income_applies_to_actual_spend BOOLEAN NOT NULL DEFAULT true,
    allow_surplus_savings BOOLEAN NOT NULL DEFAULT false,
    surplus_allocation TEXT NOT NULL DEFAULT 'reserve_first'
        CHECK (surplus_allocation IN ('reserve_first', 'risky_first')),

    -- Spending
    floor_annual_real DOUBLE PRECISION NOT NULL DEFAULT 60000,

    -- Reserve
    reserve_cash_fraction DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    safe_real_return DOUBLE PRECISION NOT NULL DEFAULT 0.01,

    -- Guardrails
    dd1 DOUBLE PRECISION NOT NULL DEFAULT 0.15,
    dd2 DOUBLE PRECISION NOT NULL DEFAULT 0.25,
    cut1 DOUBLE PRECISION NOT NULL DEFAULT 0.50,
    cut2 DOUBLE PRECISION NOT NULL DEFAULT 1.00,
    baseline_e_for_flex DOUBLE PRECISION NOT NULL DEFAULT 99300,
    baseline_flex_pre DOUBLE PRECISION NOT NULL DEFAULT 20000,
    baseline_net_post_ss DOUBLE PRECISION NOT NULL DEFAULT 52895,
    baseline_flex_post DOUBLE PRECISION NOT NULL DEFAULT 10000,

    -- Reverse mortgage
    rm_open_age INT NOT NULL DEFAULT 62,
    home_value_real DOUBLE PRECISION NOT NULL DEFAULT 950000,
    rm_plf_at_open DOUBLE PRECISION NOT NULL DEFAULT 0.40,
    rm_limit_real_growth DOUBLE PRECISION NOT NULL DEFAULT 0.015,
    rm_bal_real_rate DOUBLE PRECISION NOT NULL DEFAULT 0.015,
    rm_partial_cover DOUBLE PRECISION NOT NULL DEFAULT 0.50,
    rm_repay_rate DOUBLE PRECISION NOT NULL DEFAULT 0.15,
    payoff_dd_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.05,

    -- Loan
    loan_real_rate DOUBLE PRECISION NOT NULL DEFAULT 0.03,
    loan_term_years INT NOT NULL DEFAULT 30,
    loan_bucket_real_return DOUBLE PRECISION NOT NULL DEFAULT 0.01,
    loan_bucket_use_dd DOUBLE PRECISION NOT NULL DEFAULT 0.15,
    loan_bucket_partial_cover DOUBLE PRECISION NOT NULL DEFAULT 0.50,

    -- Sweep grid (JSONB arrays for flexibility)
    start_portfolios JSONB NOT NULL DEFAULT '[1477000]'::jsonb,
    reserve_years_list JSONB NOT NULL DEFAULT '[1.0]'::jsonb,
    loan_amounts JSONB NOT NULL DEFAULT '[0]'::jsonb
);

ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own scenarios" ON scenarios
    FOR ALL USING (user_id = auth.uid());

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER scenarios_updated_at
    BEFORE UPDATE ON scenarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- simulation_runs
-- =============================================================================
CREATE TABLE simulation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    progress DOUBLE PRECISION NOT NULL DEFAULT 0,
    error_message TEXT,
    config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

ALTER TABLE simulation_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own runs" ON simulation_runs
    FOR ALL USING (user_id = auth.uid());

-- =============================================================================
-- simulation_results
-- =============================================================================
CREATE TABLE simulation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Grid point identifiers
    start_portfolio DOUBLE PRECISION NOT NULL,
    reserve_years DOUBLE PRECISION NOT NULL,
    loan_amount INT NOT NULL,

    -- Results
    max_e_real_per_year INT,
    e_real_per_year INT,
    p_success_death_weighted DOUBLE PRECISION NOT NULL,
    p_success_to_age_99 DOUBLE PRECISION NOT NULL,
    median_max_dd_risky DOUBLE PRECISION NOT NULL,
    median_max_dd_total DOUBLE PRECISION NOT NULL,
    home_equity_remaining_median DOUBLE PRECISION NOT NULL,
    p_any_rm_draw DOUBLE PRECISION NOT NULL,
    rm_balance_end_median DOUBLE PRECISION NOT NULL,
    risky_end_median DOUBLE PRECISION NOT NULL,
    total_net_end_median DOUBLE PRECISION NOT NULL,
    net_worth_end_median DOUBLE PRECISION NOT NULL,

    -- Optional path data (Phase 3)
    path_data JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE simulation_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own results" ON simulation_results
    FOR ALL USING (user_id = auth.uid());

-- Index for fast lookups
CREATE INDEX idx_simulation_results_run_id ON simulation_results(run_id);
CREATE INDEX idx_simulation_runs_scenario_id ON simulation_runs(scenario_id);
CREATE INDEX idx_scenarios_user_id ON scenarios(user_id);
