# Simulation model and tweakable parameters

This tool runs a **real-dollar** (inflation-adjusted) Monte Carlo simulation of a retirement drawdown plan from `START_AGE` through age **99**. Each Monte Carlo path represents one possible sequence of annual real returns.

It’s built for fast experimentation: tweak `.env` parameters, re-run, compare `summary.csv`.

---

## What “success” means

The simulation enforces a required **asset-funded floor**:

- Each year, assets must be able to fund **at least `FLOOR_ANNUAL_REAL`** (real $/yr).
- Social Security is modeled as guaranteed real income `SS_ANNUAL_REAL`, which reduces asset withdrawals after `SS_START_AGE`.

**Failure** occurs in any year where the plan cannot fund the year’s floor requirement (including the partial first year), even after using all permitted sources.

Two success metrics are computed:

1. **Death-weighted success**: weighted by a male mortality distribution conditional on being alive at age 53.
2. **Success to age 99**: never failing through the final year.

The optimization target is **death-weighted success**: `TARGET_SUCCESS_DEATH_WEIGHTED`.

---

## Timeline and withdrawals

### Ages and horizon
- Simulation starts at `START_AGE` and runs annually through age 99.
- The first year uses `PARTIAL_YEAR_FRACTION`.

### Planned spending schedule `E`
`E` is the planned annual spending level *before* Social Security begins (real $/yr).

- If `age < SS_START_AGE`: planned withdrawal is `E`
- If `age >= SS_START_AGE`: planned withdrawal is `max(0, E - SS_ANNUAL_REAL)`
- Year 1 is multiplied by `PARTIAL_YEAR_FRACTION`

---

## Accounts and balances

All balances are in **real dollars**:

1. **Risky portfolio**: stochastic real returns.
2. **Cash reserve**: earns `SAFE_REAL_RETURN`.
3. **Base Treasuries reserve**: earns `SAFE_REAL_RETURN`.
4. **Loan-funded ladder bucket** (optional): seeded by an equity loan; earns `LOAN_BUCKET_REAL_RETURN`; only usable in drawdowns.
5. **Reverse Mortgage LOC** (optional): opens at `RM_OPEN_AGE`; limit grows by `RM_LIMIT_REAL_GROWTH`; balance accrues at `RM_BAL_REAL_RATE`.

---

## Return model

Risky returns are i.i.d. Normal:

- mean = `RETURN_MU_REAL`
- volatility = `RETURN_VOL_REAL`

Returns are clipped at -99%.

To change distributions (fat tails, regimes), edit `generate_returns()` in `simulate.py`.

---

## Reserve policy (cash + base treasuries)

### Reserve target
Reserve is sized as a multiple of *next year’s planned withdrawal*:

- total reserve target = `RESERVE_YEARS * next_year_withdrawal`
- cash target = `RESERVE_CASH_FRACTION * total_target`
- base treas target = remainder

`RESERVE_YEARS` comes from `RESERVE_YEARS_LIST` (supports sweeping multiple sizes).

### Refill rule
When risky drawdown is **below** `DD1`, the model refills reserves from the risky portfolio:
1) cash up to target  
2) base treas up to target  

When drawdown ≥ `DD1`, refilling pauses.

---

## Drawdown definition

Drawdown is measured on the **risky portfolio**:

- high-water mark (HWM) tracks the max risky value to date
- drawdown = `1 - risky / HWM`

Guardrails and credit access key off this drawdown.

---

## Guardrails spending rule

Spending is split into:

- **Floor component** (not cut)
- **Flex component** (cut during drawdowns)

Flex % is calibrated from baseline constants:

- pre-SS flex % = `BASELINE_FLEX_PRE / BASELINE_E_FOR_FLEX`
- post-SS flex % = `BASELINE_FLEX_POST / BASELINE_NET_POST_SS`

For each year:
- `flex_amt = min(flex_pct * planned_withdrawal, planned_withdrawal)`
- `floor_amt = planned_withdrawal - flex_amt`

Cuts apply to the flex part:

- if drawdown ≥ `DD2`: cut fraction = `CUT2`
- else if drawdown ≥ `DD1`: cut fraction = `CUT1`
- else: 0

So:
- `desired_spend = floor_amt + flex_amt * (1 - cut_fraction)`

Then the tool enforces the absolute floor:
- actual spend is at least `FLOOR_ANNUAL_REAL` (asset-funded), if feasible
- otherwise the path fails

---

## Reverse Mortgage LOC (RM LOC)

At age `RM_OPEN_AGE`:

- initial limit = `HOME_VALUE_REAL * RM_PLF_AT_OPEN`
- annually: limit grows by `RM_LIMIT_REAL_GROWTH`
- outstanding RM balance accrues by `RM_BAL_REAL_RATE`

### RM usage
In deep drawdowns (drawdown ≥ `DD2`), RM can cover up to:
- `RM_PARTIAL_COVER` of the remaining shortfall (capped by remaining credit)

### RM payback rule
At new highs (drawdown ~ 0), repay:
- `RM_REPAY_RATE` of RM balance (capped by available risky funds)

---

## Equity loan + loan-funded ladder bucket

### Loan
For each principal in `LOAN_AMOUNTS`:

- real rate = `LOAN_REAL_RATE`
- term = `LOAN_TERM_YEARS`
- annual payment uses standard amortization

### Bucket
Loan proceeds sit in a separate bucket earning:
- `LOAN_BUCKET_REAL_RETURN`

### Access rule
Bucket usable only when drawdown ≥ `LOAN_BUCKET_USE_DD`, covering up to:
- `LOAN_BUCKET_PARTIAL_COVER` of the remaining shortfall (capped by bucket balance)

### Loan payments before RM opens
Before `RM_OPEN_AGE`, annual loan payments attempt funding from:
1) cash  
2) base treas  
3) risky  

If still short and drawdown ≥ `LOAN_BUCKET_USE_DD`, bucket can cover the remainder.

If payment cannot be made, the path fails (cashflow failure).

### Lien payoff at RM open
At `RM_OPEN_AGE`, the equity loan must be cleared.

Ordering depends on drawdown:
- if drawdown <= `PAYOFF_DD_THRESHOLD`: prefer risky first
- else: prefer RM credit first

Then tries the other source, then reserves, then bucket. If lien cannot be cleared, the path fails.

---

## Annual spending funding order

After computing desired spend and enforcing the floor:

1) cash  
2) base treas  
3) (if drawdown ≥ `LOAN_BUCKET_USE_DD`) bucket partial cover  
4) (if drawdown ≥ `DD2`) RM partial cover  
5) risky  
6) RM (remaining available credit)  
7) bucket (last resort if still in drawdown)

---

## Optimization: finding max `E`

For each scenario (reserve_years × loan_amount), the tool solves:

- maximize integer `E`
- subject to death-weighted success ≥ `TARGET_SUCCESS_DEATH_WEIGHTED`

Using binary search:

- lower bound `E_LO`
- upper bound `E_HI` (auto-expanded if it still succeeds)
- iterations `E_SEARCH_ITERS`

---

## `.env` keys and meanings

### Core
- `SEED`
- `N_SIMS`
- `START_PORTFOLIO`
- `START_AGE`
- `PARTIAL_YEAR_FRACTION`

### Returns (real)
- `RETURN_MU_REAL`
- `RETURN_VOL_REAL`

### Target / search
- `TARGET_SUCCESS_DEATH_WEIGHTED`
- `E_LO`, `E_HI`
- `E_SEARCH_ITERS`

### Social Security
- `SS_ANNUAL_REAL`
- `SS_START_AGE`

### Earned income after retirement
- `EARNED_INCOME_ANNUAL_REAL`: annual earned income in real dollars (set 0 to disable)
- `EARNED_INCOME_START_AGE`: first age the earned income applies
- `EARNED_INCOME_END_AGE`: last age the earned income applies (inclusive)

### Income application mode
- `INCOME_APPLIES_TO_ACTUAL_SPEND`: if 1, SS + earned income reduce **actual** spending each year; surplus (income > spending) is invested back into assets.

### Income surplus handling
- `SURPLUS_ALLOCATION`: `reserve_first` (fill reserve targets first, then risky) or `risky_first`.
- `ALLOW_SURPLUS_SAVINGS`: legacy-only; used only when `INCOME_APPLIES_TO_ACTUAL_SPEND=0`.

### Floor
- `FLOOR_ANNUAL_REAL`

### Reserve policy
- `RESERVE_YEARS_LIST`
- `RESERVE_CASH_FRACTION`
- `SAFE_REAL_RETURN`

### Guardrails
- `DD1`, `DD2`
- `CUT1`, `CUT2`

### Flex calibration
- `BASELINE_E_FOR_FLEX`
- `BASELINE_FLEX_PRE`
- `BASELINE_NET_POST_SS`
- `BASELINE_FLEX_POST`

### Reverse mortgage LOC
- `RM_OPEN_AGE`
- `HOME_VALUE_REAL`
- `RM_PLF_AT_OPEN`
- `RM_LIMIT_REAL_GROWTH`
- `RM_BAL_REAL_RATE`
- `RM_PARTIAL_COVER`
- `RM_REPAY_RATE`
- `PAYOFF_DD_THRESHOLD`

### Equity loan
- `LOAN_AMOUNTS`
- `LOAN_REAL_RATE`
- `LOAN_TERM_YEARS`

### Loan bucket
- `LOAN_BUCKET_REAL_RETURN`
- `LOAN_BUCKET_USE_DD`
- `LOAN_BUCKET_PARTIAL_COVER`

### Output
- `OUTPUT_DIR`

---

## Limitations

This model omits:
- taxes (Roth/taxable/pre-tax), ACA/IRMAA cliffs
- glidepaths (changing risk mix over time)
- fat tails, regimes, inflation correlation, valuation effects
- lumpy medical/LTC shocks
- multi-person mortality
- explicit home price volatility (home is constant in real terms)

Add those and results can shift materially.


## Run modes

The tool supports two execution modes:

- `MODE=optimize`: binary-search for the maximum `E` (planned annual spending, real $/yr) that meets `TARGET_SUCCESS_DEATH_WEIGHTED`.
- `MODE=single`: evaluate one fixed spending level `E_FIXED` and report success statistics (no optimization).

### `.env` keys
- `MODE`: `optimize` or `single`
- `E_FIXED`: used only when `MODE=single`


## Optimization objective

When `MODE=optimize`, the binary search can target different definitions of success via `OPTIMIZE_SUCCESS_METRIC`:

- `death_weighted` (default): optimize on death-weighted success.
- `age_99`: optimize on survival of the spending floor through age 99.
- `both_min`: optimize on the minimum of the two success metrics.
- `both_weighted`: optimize on a weighted blend; weight set by `BOTH_WEIGHT`.


## Additional reported metrics

The summary table includes:

- `median_max_dd_risky`: median across simulations of the per-path maximum drawdown of the risky bucket.
- `median_max_dd_total`: median across simulations of the per-path maximum drawdown of total net liquid wealth (cash + base treas + risky + loan bucket − loan balance).
- `p_any_rm_draw`: fraction of simulations where RM balance was ever > 0.

## Median net worth

`net_worth_end_median` is computed at the end of the simulation horizon as:

- `total_net_end = cash + base_treas + risky + loan_bucket − loan_balance`
- `home_equity_remaining = max(0, home_value − rm_balance)`
- `net_worth_end = total_net_end + home_equity_remaining`

The tool reports the median of `net_worth_end` across simulation paths.


## Terminal balance medians

- `risky_end_median`: median ending risky balance.
- `total_net_end_median`: median ending total net liquid wealth.
- `net_worth_end_median`: median ending net worth (liquid + remaining home equity).


## Multiple starting portfolios

You can sweep multiple starting portfolio values via `START_PORTFOLIOS_LIST` (comma-separated real dollars). If provided, the simulator runs the full scenario grid for each starting amount and includes a `start_portfolio` column in `summary.csv`.
