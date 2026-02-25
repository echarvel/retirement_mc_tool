import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { runSimulation, type ScenarioConfig } from "@/lib/simulation-client";

export async function POST(request: Request) {
  const supabase = await createClient();

  // Verify auth
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { scenarioId } = await request.json();
  if (!scenarioId) {
    return NextResponse.json(
      { error: "scenarioId required" },
      { status: 400 }
    );
  }

  // Read scenario (RLS ensures user owns it)
  const { data: scenario, error: scenarioError } = await supabase
    .from("scenarios")
    .select("*")
    .eq("id", scenarioId)
    .single();

  if (scenarioError || !scenario) {
    return NextResponse.json(
      { error: "Scenario not found" },
      { status: 404 }
    );
  }

  // Create simulation run
  const { data: run, error: runError } = await supabase
    .from("simulation_runs")
    .insert({
      user_id: user.id,
      scenario_id: scenarioId,
      status: "running",
      config_snapshot: scenario,
    })
    .select("id")
    .single();

  if (runError || !run) {
    return NextResponse.json(
      { error: "Failed to create run" },
      { status: 500 }
    );
  }

  try {
    // Map DB scenario to engine config
    const config: ScenarioConfig = {
      seed: scenario.seed,
      n_sims: scenario.n_sims,
      start_age: scenario.start_age,
      partial_year_fraction: scenario.partial_year_fraction,
      return_mu_real: scenario.return_mu_real,
      return_vol_real: scenario.return_vol_real,
      mode: scenario.mode,
      e_fixed: scenario.e_fixed,
      target_success_death_weighted: scenario.target_success_death_weighted,
      e_lo: scenario.e_lo,
      e_hi: scenario.e_hi,
      e_search_iters: scenario.e_search_iters,
      optimize_success_metric: scenario.optimize_success_metric,
      both_weight: scenario.both_weight,
      ss_annual_real: scenario.ss_annual_real,
      ss_start_age: scenario.ss_start_age,
      earned_income_annual_real: scenario.earned_income_annual_real,
      earned_income_start_age: scenario.earned_income_start_age,
      earned_income_end_age: scenario.earned_income_end_age,
      income_applies_to_actual_spend: scenario.income_applies_to_actual_spend,
      allow_surplus_savings: scenario.allow_surplus_savings,
      surplus_allocation: scenario.surplus_allocation,
      floor_annual_real: scenario.floor_annual_real,
      reserve_cash_fraction: scenario.reserve_cash_fraction,
      safe_real_return: scenario.safe_real_return,
      dd1: scenario.dd1,
      dd2: scenario.dd2,
      cut1: scenario.cut1,
      cut2: scenario.cut2,
      baseline_e_for_flex: scenario.baseline_e_for_flex,
      baseline_flex_pre: scenario.baseline_flex_pre,
      baseline_net_post_ss: scenario.baseline_net_post_ss,
      baseline_flex_post: scenario.baseline_flex_post,
      rm_open_age: scenario.rm_open_age,
      home_value_real: scenario.home_value_real,
      rm_plf_at_open: scenario.rm_plf_at_open,
      rm_limit_real_growth: scenario.rm_limit_real_growth,
      rm_bal_real_rate: scenario.rm_bal_real_rate,
      rm_partial_cover: scenario.rm_partial_cover,
      rm_repay_rate: scenario.rm_repay_rate,
      payoff_dd_threshold: scenario.payoff_dd_threshold,
      loan_real_rate: scenario.loan_real_rate,
      loan_term_years: scenario.loan_term_years,
      loan_bucket_real_return: scenario.loan_bucket_real_return,
      loan_bucket_use_dd: scenario.loan_bucket_use_dd,
      loan_bucket_partial_cover: scenario.loan_bucket_partial_cover,
      start_portfolios: scenario.start_portfolios as number[],
      reserve_years_list: scenario.reserve_years_list as number[],
      loan_amounts: scenario.loan_amounts as number[],
    };

    // Call Python engine
    const engineResult = await runSimulation(config, run.id);

    // Write results to Supabase
    const resultRows = engineResult.results.map((r) => ({
      run_id: run.id,
      user_id: user.id,
      start_portfolio: r.start_portfolio,
      reserve_years: r.reserve_years,
      loan_amount: r.loan_amount,
      max_e_real_per_year: r.max_E_real_per_year ?? null,
      e_real_per_year: r.E_real_per_year ?? null,
      p_success_death_weighted: r.p_success_death_weighted,
      p_success_to_age_99: r.p_success_to_age_99,
      median_max_dd_risky: r.median_max_dd_risky,
      median_max_dd_total: r.median_max_dd_total,
      home_equity_remaining_median: r.home_equity_remaining_median,
      p_any_rm_draw: r.p_any_rm_draw,
      rm_balance_end_median: r.rm_balance_end_median,
      risky_end_median: r.risky_end_median,
      total_net_end_median: r.total_net_end_median,
      net_worth_end_median: r.net_worth_end_median,
    }));

    await supabase.from("simulation_results").insert(resultRows);

    // Update run status
    await supabase
      .from("simulation_runs")
      .update({ status: "completed", completed_at: new Date().toISOString() })
      .eq("id", run.id);

    return NextResponse.json({
      runId: run.id,
      status: "completed",
      totalGridPoints: engineResult.total_grid_points,
    });
  } catch (e: any) {
    // Mark run as failed
    await supabase
      .from("simulation_runs")
      .update({ status: "failed", error_message: e.message })
      .eq("id", run.id);

    return NextResponse.json(
      { error: e.message },
      { status: 500 }
    );
  }
}
