"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  NumberField,
  SelectField,
  BoolField,
  ArrayField,
} from "./field-group";

export interface ScenarioData {
  id: string;
  name: string;
  start_age: number;
  partial_year_fraction: number;
  return_mu_real: number;
  return_vol_real: number;
  seed: number;
  n_sims: number;
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

interface ScenarioFormProps {
  data: ScenarioData;
  onChange: (data: ScenarioData) => void;
}

export function ScenarioForm({ data, onChange }: ScenarioFormProps) {
  function set<K extends keyof ScenarioData>(key: K, value: ScenarioData[K]) {
    onChange({ ...data, [key]: value });
  }

  return (
    <div>
      <div className="mb-4 space-y-1">
        <Label>Scenario Name</Label>
        <Input
          value={data.name}
          onChange={(e) => set("name", e.target.value)}
          className="max-w-md text-lg font-medium"
        />
      </div>

      <Tabs defaultValue="general" className="w-full">
        <TabsList className="mb-4 flex-wrap">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="income">Income</TabsTrigger>
          <TabsTrigger value="guardrails">Guardrails</TabsTrigger>
          <TabsTrigger value="rm_loans">RM & Loans</TabsTrigger>
          <TabsTrigger value="sweep">Sweep Grid</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Core
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <NumberField
                label="Start Age"
                value={data.start_age}
                onChange={(v) => set("start_age", v)}
              />
              <NumberField
                label="Partial Year Fraction"
                value={data.partial_year_fraction}
                onChange={(v) => set("partial_year_fraction", v)}
                step={0.01}
              />
              <NumberField
                label="Seed"
                value={data.seed}
                onChange={(v) => set("seed", v)}
              />
              <NumberField
                label="Paths (n_sims)"
                value={data.n_sims}
                onChange={(v) => set("n_sims", v)}
                step={1000}
                min={100}
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Returns
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <NumberField
                label="Expected Real Return"
                value={data.return_mu_real}
                onChange={(v) => set("return_mu_real", v)}
                step={0.005}
                suffix="%"
              />
              <NumberField
                label="Volatility"
                value={data.return_vol_real}
                onChange={(v) => set("return_vol_real", v)}
                step={0.005}
                suffix="%"
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Optimization
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <SelectField
                label="Mode"
                value={data.mode}
                onChange={(v) => set("mode", v)}
                options={[
                  { value: "optimize", label: "Optimize (find max E)" },
                  { value: "single", label: "Single (fixed E)" },
                ]}
              />
              {data.mode === "single" && (
                <NumberField
                  label="Fixed E"
                  value={data.e_fixed}
                  onChange={(v) => set("e_fixed", v)}
                  step={1000}
                  suffix="$/yr"
                />
              )}
              <NumberField
                label="Target Success"
                value={data.target_success_death_weighted}
                onChange={(v) => set("target_success_death_weighted", v)}
                step={0.01}
                min={0}
                max={1}
              />
              <NumberField
                label="E Low"
                value={data.e_lo}
                onChange={(v) => set("e_lo", v)}
                step={5000}
                suffix="$/yr"
              />
              <NumberField
                label="E High"
                value={data.e_hi}
                onChange={(v) => set("e_hi", v)}
                step={5000}
                suffix="$/yr"
              />
              <NumberField
                label="Search Iterations"
                value={data.e_search_iters}
                onChange={(v) => set("e_search_iters", v)}
              />
              <SelectField
                label="Optimize Metric"
                value={data.optimize_success_metric}
                onChange={(v) => set("optimize_success_metric", v)}
                options={[
                  { value: "death_weighted", label: "Death-Weighted" },
                  { value: "age_99", label: "Age 99" },
                  { value: "both_min", label: "Both (Min)" },
                  { value: "both_weighted", label: "Both (Weighted)" },
                ]}
              />
              {data.optimize_success_metric === "both_weighted" && (
                <NumberField
                  label="Both Weight"
                  value={data.both_weight}
                  onChange={(v) => set("both_weight", v)}
                  step={0.1}
                  min={0}
                  max={1}
                />
              )}
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Spending
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <NumberField
                label="Floor (Annual Real)"
                value={data.floor_annual_real}
                onChange={(v) => set("floor_annual_real", v)}
                step={1000}
                suffix="$/yr"
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Reserve Policy
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <NumberField
                label="Cash Fraction"
                value={data.reserve_cash_fraction}
                onChange={(v) => set("reserve_cash_fraction", v)}
                step={0.1}
                min={0}
                max={1}
              />
              <NumberField
                label="Safe Real Return"
                value={data.safe_real_return}
                onChange={(v) => set("safe_real_return", v)}
                step={0.005}
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="income" className="space-y-6">
          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Social Security
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <NumberField
                label="SS Annual (Real)"
                value={data.ss_annual_real}
                onChange={(v) => set("ss_annual_real", v)}
                step={1000}
                suffix="$/yr"
              />
              <NumberField
                label="SS Start Age"
                value={data.ss_start_age}
                onChange={(v) => set("ss_start_age", v)}
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Earned Income
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <NumberField
                label="Annual (Real)"
                value={data.earned_income_annual_real}
                onChange={(v) => set("earned_income_annual_real", v)}
                step={1000}
                suffix="$/yr"
              />
              <NumberField
                label="Start Age"
                value={data.earned_income_start_age}
                onChange={(v) => set("earned_income_start_age", v)}
              />
              <NumberField
                label="End Age"
                value={data.earned_income_end_age}
                onChange={(v) => set("earned_income_end_age", v)}
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Income Settings
            </h3>
            <div className="space-y-3">
              <BoolField
                label="Income applies to actual spend"
                value={data.income_applies_to_actual_spend}
                onChange={(v) => set("income_applies_to_actual_spend", v)}
              />
              <BoolField
                label="Allow surplus savings"
                value={data.allow_surplus_savings}
                onChange={(v) => set("allow_surplus_savings", v)}
              />
              <SelectField
                label="Surplus Allocation"
                value={data.surplus_allocation}
                onChange={(v) => set("surplus_allocation", v)}
                options={[
                  { value: "reserve_first", label: "Reserve First" },
                  { value: "risky_first", label: "Risky First" },
                ]}
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="guardrails" className="space-y-6">
          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Drawdown Thresholds
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <NumberField
                label="DD1 (mild)"
                value={data.dd1}
                onChange={(v) => set("dd1", v)}
                step={0.01}
              />
              <NumberField
                label="DD2 (severe)"
                value={data.dd2}
                onChange={(v) => set("dd2", v)}
                step={0.01}
              />
              <NumberField
                label="Cut1 (at DD1)"
                value={data.cut1}
                onChange={(v) => set("cut1", v)}
                step={0.05}
                min={0}
                max={1}
              />
              <NumberField
                label="Cut2 (at DD2)"
                value={data.cut2}
                onChange={(v) => set("cut2", v)}
                step={0.05}
                min={0}
                max={1}
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Flex Calibration
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <NumberField
                label="Baseline E for Flex"
                value={data.baseline_e_for_flex}
                onChange={(v) => set("baseline_e_for_flex", v)}
                step={1000}
                suffix="$/yr"
              />
              <NumberField
                label="Baseline Flex Pre-SS"
                value={data.baseline_flex_pre}
                onChange={(v) => set("baseline_flex_pre", v)}
                step={1000}
                suffix="$/yr"
              />
              <NumberField
                label="Baseline Net Post-SS"
                value={data.baseline_net_post_ss}
                onChange={(v) => set("baseline_net_post_ss", v)}
                step={1000}
                suffix="$/yr"
              />
              <NumberField
                label="Baseline Flex Post-SS"
                value={data.baseline_flex_post}
                onChange={(v) => set("baseline_flex_post", v)}
                step={1000}
                suffix="$/yr"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="rm_loans" className="space-y-6">
          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Reverse Mortgage
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <NumberField
                label="RM Open Age"
                value={data.rm_open_age}
                onChange={(v) => set("rm_open_age", v)}
              />
              <NumberField
                label="Home Value (Real)"
                value={data.home_value_real}
                onChange={(v) => set("home_value_real", v)}
                step={10000}
                suffix="$"
              />
              <NumberField
                label="PLF at Open"
                value={data.rm_plf_at_open}
                onChange={(v) => set("rm_plf_at_open", v)}
                step={0.01}
              />
              <NumberField
                label="Limit Real Growth"
                value={data.rm_limit_real_growth}
                onChange={(v) => set("rm_limit_real_growth", v)}
                step={0.005}
              />
              <NumberField
                label="Balance Real Rate"
                value={data.rm_bal_real_rate}
                onChange={(v) => set("rm_bal_real_rate", v)}
                step={0.005}
              />
              <NumberField
                label="Partial Cover"
                value={data.rm_partial_cover}
                onChange={(v) => set("rm_partial_cover", v)}
                step={0.05}
                min={0}
                max={1}
              />
              <NumberField
                label="Repay Rate"
                value={data.rm_repay_rate}
                onChange={(v) => set("rm_repay_rate", v)}
                step={0.05}
              />
              <NumberField
                label="Payoff DD Threshold"
                value={data.payoff_dd_threshold}
                onChange={(v) => set("payoff_dd_threshold", v)}
                step={0.01}
              />
            </div>
          </div>

          <Separator />

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Loan Settings
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <NumberField
                label="Loan Real Rate"
                value={data.loan_real_rate}
                onChange={(v) => set("loan_real_rate", v)}
                step={0.005}
              />
              <NumberField
                label="Loan Term (years)"
                value={data.loan_term_years}
                onChange={(v) => set("loan_term_years", v)}
              />
              <NumberField
                label="Bucket Real Return"
                value={data.loan_bucket_real_return}
                onChange={(v) => set("loan_bucket_real_return", v)}
                step={0.005}
              />
              <NumberField
                label="Bucket Use DD"
                value={data.loan_bucket_use_dd}
                onChange={(v) => set("loan_bucket_use_dd", v)}
                step={0.01}
              />
              <NumberField
                label="Bucket Partial Cover"
                value={data.loan_bucket_partial_cover}
                onChange={(v) => set("loan_bucket_partial_cover", v)}
                step={0.05}
                min={0}
                max={1}
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="sweep" className="space-y-6">
          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
              Parameter Sweep Grid
            </h3>
            <p className="mb-4 text-sm text-muted-foreground">
              The simulation runs for every combination of these values.
            </p>
            <div className="grid gap-4">
              <ArrayField
                label="Starting Portfolios"
                value={data.start_portfolios}
                onChange={(v) => set("start_portfolios", v)}
                suffix="$"
              />
              <ArrayField
                label="Reserve Years"
                value={data.reserve_years_list}
                onChange={(v) => set("reserve_years_list", v)}
                suffix="years"
              />
              <ArrayField
                label="Loan Amounts"
                value={data.loan_amounts}
                onChange={(v) => set("loan_amounts", v)}
                suffix="$"
              />
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Total grid points:{" "}
              {(data.start_portfolios?.length || 1) *
                (data.reserve_years_list?.length || 1) *
                (data.loan_amounts?.length || 1)}
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
