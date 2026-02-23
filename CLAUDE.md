# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Retirement Monte Carlo simulation tool that finds the maximum annual spending level achieving a target success probability. Single-file Python project (`simulate.py`, ~735 lines) using NumPy vectorized computations across 25,000 Monte Carlo paths.

All dollar amounts and returns are in **real (inflation-adjusted) dollars**.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit .env

# Run simulation
python simulate.py
```

No test suite or linter is configured. Output goes to `outputs/YYYYMMDD_HHMMSS/` with `summary.csv`, `settings.csv`, and `notes.txt`.

## Architecture

### Configuration Flow
`.env` → `load_env()` → `read_config()` → `Config` frozen dataclass (holds all ~50 parameters)

### Simulation Pipeline
1. **`main()`** iterates over scenario grid: `START_PORTFOLIOS_LIST × RESERVE_YEARS_LIST × LOAN_AMOUNTS`
2. **`find_max_E()`** binary searches for max annual spending meeting `TARGET_SUCCESS_DEATH_WEIGHTED` (default 90%), using ~19 iterations between `E_LO` and `E_HI`
3. **`simulate_once()`** runs all 25k paths in parallel via NumPy arrays. Year-by-year loop updates state arrays (cash, treasuries, risky, loan bucket, RM) for all paths simultaneously
4. **`death_weighted_success()`** weights outcomes by SSA 2022 male mortality table (age 53 baseline)

### Key Simulation Mechanics
- **Guardrails spending**: Flex portion of spending is cut based on risky portfolio drawdown thresholds (`DD1`/`DD2` → `CUT1`/`CUT2`)
- **Reserve policy**: Cash + treasuries sized to `RESERVE_YEARS × next_year_withdrawal`, refilled when drawdown < `DD1`
- **Funding order**: cash → treasuries → loan bucket → RM draws → risky → RM credit line
- **Equity loan**: Amortized over `LOAN_TERM_YEARS`, bucket accessed only when drawdown ≥ `LOAN_BUCKET_USE_DD`
- **Reverse mortgage LOC**: Opens at `RM_OPEN_AGE`, limit grows annually, drawn when drawdown ≥ `DD2`, repaid at new portfolio highs
- **Income**: SS + optional earned income reduce asset-funded spending need (when `INCOME_APPLIES_TO_ACTUAL_SPEND=1`)

### Two Operating Modes
- **`MODE=optimize`**: Binary search for max spending E (primary use case)
- **`MODE=single`**: Evaluate a fixed spending level `E_FIXED`

### Helper Patterns
- `take_from(account_array, amount_array)`: In-place withdrawal across all paths with remainder tracking
- `amortize()`: Computes annual loan payment from principal/rate/term
- Returns are i.i.d. normal, clipped at -99%

## Configuration

All config lives in `.env` (see `.env.example` and `env.example` for documented defaults). Key parameter groups: returns, optimization bounds, income/SS, spending floor, reserve policy, guardrails thresholds, reverse mortgage, equity loan. Detailed model documentation is in `SIMULATION_MODEL.md`.
