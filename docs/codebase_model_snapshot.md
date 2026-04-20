# Codebase Model Snapshot

## Current Pipelines

- `scripts/prepare_market_data.py`
  - Data validation, gap handling, clean exports, strict ML exports.
- `scripts/specialist_tcn_pipeline.py`
  - Historical benchmark pipeline for the repo.
  - Produces the only artifact family in the workspace with a profitable full test backtest and a passed prop-style target under the legacy checked-in policy.
  - Important caveat: the checked-in `.py` file is a wrapper around cached bytecode in `scripts/__pycache__/`, so the main training and backtest implementation is not fully source-auditable from the repository text alone.
- `scripts/learned_moe_pipeline.py`
  - Experimental learned mixture-of-experts pipeline.
  - Current checked-in smoke artifact at `artifacts/learned_moe/us100_session_refined_smoke` does not trade on test under the fixed-risk policy.
- `scripts/learned_moe_tcn_pipeline.py`
  - Experimental MoE + TCN pipeline.
  - Current checked-in smoke artifact at `artifacts/learned_moe/us100_session_refined_tcn_smoke` is materially negative on test and does not pass the prop-style policy.

## Legacy Benchmark Snapshot

- Benchmark artifact: `artifacts/specialist_tcns/us100_session_refined`
- Benchmark report: `docs/current_baseline_us100_session_refined.md`
- Machine-readable baseline metrics: `artifacts/specialist_tcns/us100_session_refined/baseline_report.json`

## Why This Is The Baseline

- `specialist_tcns/us100_session_refined` is the only checked-in artifact set with:
  - positive out-of-sample expectancy
  - positive total return
  - acceptable drawdown relative to the legacy configured `6%` account floor
  - a recorded pass of the legacy configured `8%` target
- The learned-MoE artifacts in the repo are still exploratory smoke runs, not production baselines.
- FundedHive is now the active prop-firm target for source-level defaults, so this benchmark should be treated as a historical comparison point until it is rerun under the new policy.

## Baseline Numbers To Beat

- Win rate: `0.40665`
- Expectancy: `0.084399R`
- Total return: `8.3718%`
- Max drawdown: `5.4092%`
- Days to target: `66` active trading days
- Bootstrap pass probability:
  - `60` active-day horizon: `0.591000`
  - `90` active-day horizon: `0.752000`
