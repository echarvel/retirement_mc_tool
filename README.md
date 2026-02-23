# Retirement Monte Carlo Tinkering Tool (real-dollar model)

This project runs a Monte Carlo retirement simulation with configurable parameters in a `.env` file.

It will:
- Run scenarios (e.g., different loan sizes and reserve sizes)
- Find the **maximum planned pre-SS spending `E`** that achieves a target success probability
- Print a console summary table
- Write CSV outputs under `outputs/<run_id>/`

## Quick start

1) Install deps:
```bash
pip install -r requirements.txt
```

2) Copy the example config and edit:
```bash
cp .env.example .env
```

3) Run:
```bash
python simulate.py
```

## Outputs

A new folder will be created:
- `outputs/<run_id>/summary.csv` – scenario summary (max E, success rates)
- `outputs/<run_id>/settings.csv` – the config used for the run
- `outputs/<run_id>/notes.txt` – short run notes

## Notes on units

- The model is **real dollars** (inflation-adjusted).
- Return parameters `RETURN_MU_REAL` and `RETURN_VOL_REAL` are **real** (already net of inflation).

## What to tweak first

High-leverage knobs:
- `RESERVE_YEARS_LIST` (e.g., 0.5, 1.0, 1.5, 2.0)
- Guardrails: `DD1`, `DD2`, `CUT1`, `CUT2`
- Return model: `RETURN_MU_REAL`, `RETURN_VOL_REAL`
- Target: `TARGET_SUCCESS_DEATH_WEIGHTED`

To extend: edit `generate_returns()` in `simulate.py`.
