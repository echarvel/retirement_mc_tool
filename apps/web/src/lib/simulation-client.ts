const ENGINE_URL = process.env.ENGINE_URL || "http://localhost:8000";

export interface ScenarioConfig {
  seed: number;
  n_sims: number;
  start_age: number;
  partial_year_fraction: number;
  return_mu_real: number;
  return_vol_real: number;
  mode: string;
  e_fixed: number;
  target_success_death_weighted: number;
  e_lo: number;
  e_hi: number;
  e_search_iters: number;
  optimize_success_metric: string;
  both_weight: number;
  ss_annual_real: number;
  ss_start_age: number;
  earned_income_annual_real: number;
  earned_income_start_age: number;
  earned_income_end_age: number;
  income_applies_to_actual_spend: boolean;
  allow_surplus_savings: boolean;
  surplus_allocation: string;
  floor_annual_real: number;
  reserve_cash_fraction: number;
  safe_real_return: number;
  dd1: number;
  dd2: number;
  cut1: number;
  cut2: number;
  baseline_e_for_flex: number;
  baseline_flex_pre: number;
  baseline_net_post_ss: number;
  baseline_flex_post: number;
  rm_open_age: number;
  home_value_real: number;
  rm_plf_at_open: number;
  rm_limit_real_growth: number;
  rm_bal_real_rate: number;
  rm_partial_cover: number;
  rm_repay_rate: number;
  payoff_dd_threshold: number;
  loan_real_rate: number;
  loan_term_years: number;
  loan_bucket_real_return: number;
  loan_bucket_use_dd: number;
  loan_bucket_partial_cover: number;
  start_portfolios: number[];
  reserve_years_list: number[];
  loan_amounts: number[];
}

export interface GridPointResult {
  start_portfolio: number;
  reserve_years: number;
  loan_amount: number;
  max_E_real_per_year?: number;
  E_real_per_year?: number;
  p_success_death_weighted: number;
  p_success_to_age_99: number;
  median_max_dd_risky: number;
  median_max_dd_total: number;
  home_equity_remaining_median: number;
  p_any_rm_draw: number;
  rm_balance_end_median: number;
  risky_end_median: number;
  total_net_end_median: number;
  net_worth_end_median: number;
}

export interface SimulationResponse {
  run_id: string | null;
  status: string;
  results: GridPointResult[];
  total_grid_points: number;
}

export async function runSimulation(
  scenario: ScenarioConfig,
  runId?: string
): Promise<SimulationResponse> {
  const resp = await fetch(`${ENGINE_URL}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, run_id: runId }),
  });
  if (!resp.ok) {
    throw new Error(`Engine error: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}
