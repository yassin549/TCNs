# Capital.com Demo Live Scaffold 2026-04-20

## Scope

This session added a demo-account live trading scaffold for the frontier utility model.

New assets:

- [scripts/frontier_capital_live.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_capital_live.py:1)
- [.env](C:/Users/khoua/OneDrive/Desktop/TCNs/.env:1)

The scaffold is demo-oriented and defaults to dry-run mode.

## What The Live Runner Does

The Capital.com live runner:

1. loads credentials and broker settings from `.env`,
2. starts a Capital.com API session against the demo base URL,
3. loads the trained frontier utility checkpoint from an artifact directory,
4. scores the latest eligible row from a prepared feature snapshot dataset,
5. derives:
   - chosen setup,
   - normalized frontier score,
   - adaptive risk percent,
   - stop distance,
   - profit distance,
   - order size,
6. enforces a local daily trade cap and basic duplicate-signal protection,
7. writes a decision log to `artifacts/live_capital`,
8. only sends an actual order when `--execute-live` is explicitly passed.

## Important Assumptions

This is a scaffold, not a complete production execution system.

It assumes:

- an upstream process keeps a small prepared feature snapshot file up to date,
- that snapshot contains all columns expected by the frontier utility model,
- `CAPITAL_EPIC` is the correct Capital.com demo epic for the intended market,
- `CAPITAL_POINT_VALUE`, `CAPITAL_MIN_SIZE`, and `CAPITAL_SIZE_STEP` are calibrated for that instrument.

Without the correct epic and contract calibration, order sizing can be wrong even if the model signal is correct.

## Safety Defaults

The runner is intentionally conservative in how it executes:

- default mode is dry-run,
- local daily trade cap defaults to `2`,
- duplicate signal timestamps are blocked locally,
- open position count on the selected epic is checked before a new order is sent,
- logs are written to `artifacts/live_capital/live_decisions.jsonl`.

## Usage

Dry run:

```powershell
python -B scripts/frontier_capital_live.py `
  --dataset path\to\live_feature_snapshot.csv.gz `
  --artifacts-dir artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k
```

Live order placement on demo:

```powershell
python -B scripts/frontier_capital_live.py `
  --dataset path\to\live_feature_snapshot.csv.gz `
  --artifacts-dir artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k `
  --execute-live
```

## Next Recommended Step

Before actual demo execution, validate:

1. the exact `CAPITAL_EPIC` for the intended market,
2. the instrument point value and size increment,
3. that the live feature snapshot is updated at the same cadence as the trading decision loop,
4. that one dry-run output produces sane:
   - frontier score,
   - direction,
   - stop distance,
   - size,
   - risk cash.
