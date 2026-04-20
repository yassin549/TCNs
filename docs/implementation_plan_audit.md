# Implementation Plan Audit

Audit date: `2026-04-15`

## Already Implemented Before This Change

- Context gating existed in artifacts:
  - `artifacts/specialist_tcns/us100_session_refined/manager_policy.json`
  - `artifacts/specialist_tcns/us100_session_refined/analysis_report.json`
- The checked-in policy already filtered setups by `market_session` and `session_phase`.
- The analysis artifact already ranked validation contexts by realized trade expectancy and profit factor.
- Abstention existed only in a limited form:
  - disable experts with zero passing contexts
  - skip trades outside whitelisted contexts
  - skip after fixed session-end buffer / cooldown / daily trade cap

## Not Implemented Before This Change

- `long_continuation` was still enabled in the active checked-in manager policy despite baseline expectancy of only `0.002667R`.
- Thresholds were still flat per expert. There were no context-specific thresholds in source or checked-in policy.
- Risk sizing was still flat at `0.25%` per trade.
- There was no source-level frontier manager implementation:
  - `scripts/frontier_prop_manager.py` was empty.
- Path-aware selection utility was not explicitly encoded in source-level policy logic.
- Explicit regime-feature enrichment for:
  - session range expansion state
  - prior session imbalance
  - opening drive strength
  - volatility regime percentile
  - intraday trend persistence / chop
  was not present in source-level tooling.
- Abstention was not elevated to an explicit default policy action with stronger marginal-edge rejection.

## Implemented In This Change

- Added `scripts/frontier_prop_manager.py`.
- Added policy builder for:
  - aggressive weak-slice removal
  - context-specific thresholds
  - conditional tiered risk
  - path-aware context ranking
  - explicit abstention rules
- Added regime feature enrichment command.
- Added policy evaluation command to estimate the impact of the new manager on the checked-in trade path.

## Commands

Build frontier manager policy:

```powershell
python -B scripts\frontier_prop_manager.py build-policy `
  --analysis-report artifacts\specialist_tcns\us100_session_refined\analysis_report.json `
  --baseline-report artifacts\specialist_tcns\us100_session_refined\baseline_report.json `
  --trades artifacts\specialist_tcns\us100_session_refined\backtest_trades.csv.gz `
  --output artifacts\specialist_tcns\us100_session_refined\manager_policy_frontier.json
```

Estimate frontier policy effect on the checked-in trade path:

```powershell
python -B scripts\frontier_prop_manager.py evaluate-policy `
  --policy artifacts\specialist_tcns\us100_session_refined\manager_policy_frontier.json `
  --trades artifacts\specialist_tcns\us100_session_refined\backtest_trades.csv.gz `
  --baseline-report artifacts\specialist_tcns\us100_session_refined\baseline_report.json
```

Enrich the feature dataset with regime columns:

```powershell
python -B scripts\frontier_prop_manager.py enrich-features `
  --input data\features\us100_specialist_tcn_dataset_session_refined.csv.gz `
  --output data\features\us100_specialist_tcn_dataset_session_refined_regime.csv.gz
```
