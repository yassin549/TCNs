# Session Summary 2026-04-20: Frontier Utility Alignment And Challenge Risk Push

## Objective

This session focused on the frontier utility pipeline for the `300k` regime workbench artifact:

- measure the new architecture on the `300k` regime utility path,
- remove stale phase-1 outputs and regenerate the artifact with the new challenge/funded logic,
- diagnose why the refreshed run stopped taking trades,
- change the model and replay stack so it can select the best 1-2 trades per day and size risk more aggressively in challenge mode,
- rerun the full `300k` cycle and record the updated metrics.

Primary artifact:

- `artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k`

Primary input dataset:

- `data/features/us100_specialist_tcn_dataset_session_refined_rerun_20260415_regime.csv.gz`

Reference trade path used for account-state enrichment:

- `artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench/backtest_trades.csv.gz`

## Initial Diagnosis

The checked-in `300k` artifact was stale.

The old artifact still reflected a phase-1 target family:

- `delta_pass_prob_30`
- `delta_pass_prob_60`
- `delta_pass_prob_90`
- `delta_profitable_day_hit_prob`
- `delta_days_to_pass`
- `delta_drawdown_risk`

The repo code had already moved to phase-2 stage-aware targets:

- challenge pass/fail horizons,
- challenge time-to-resolution and drawdown-budget targets,
- funded return/breach/drawdown/payout targets.

After regenerating the `300k` artifact against the current code, the first refreshed run produced:

- model test metrics that were reasonable,
- but `0` replay trades.

The immediate failure mode was:

- all `38,755` test candidates had negative frontier scores,
- allocator `min_trade_score` stayed at `0.0`,
- every candidate was rejected as `rejected_by_allocator_low_marginal_utility`.

This exposed a misalignment:

- training ranked only on `trade_challenge_utility`,
- replay accepted/rejected on a wider challenge/funded composite,
- the raw scale of the new target heads made the replay score systematically negative.

## Code Changes

### 1. Train On The Same Frontier Composite Used In Replay

Updated:

- [scripts/frontier_utility_model.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_utility_model.py:1)

Changes:

- added `frontier_score_loss_weight` to `TrainConfig`,
- extended `SequenceDataset` to carry `account_stage_code`,
- added tensor helpers for challenge/funded frontier score construction,
- computed train-split `frontier_score_stats` from the stage-aware utility targets,
- normalized frontier scores during training and scoring,
- added a frontier-score regression loss and ranking loss on the stage-aware composite,
- persisted `frontier_score_stats` into `model.pt` and `training_summary.json`,
- emitted both `predicted_frontier_score_raw` and normalized `predicted_frontier_score` during candidate scoring.

Net effect:

- acceptance is now aligned with what the model is actually trained to rank.

### 2. Make The Allocator Use The Normalized Frontier Score Directly

Updated:

- [scripts/frontier_allocator.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_allocator.py:1)

Changes:

- `_base_candidate_score` now uses `predicted_frontier_score` directly when available,
- reduced default `max_trades_per_day` from `3` to `2`,
- widened the challenge/funded risk bands:
  - challenge min/base/max: `0.25 / 0.50 / 1.00`
  - funded min/base/max: `0.10 / 0.20 / 0.50`
- documented that selection should stay aligned with the model’s stage-aware frontier score.

Net effect:

- same model objective and same allocator acceptance surface.

### 3. Replace Static Stage Risk Buckets With Adaptive Per-Trade Risk

Updated:

- [scripts/frontier_replay.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_replay.py:1)

Changes:

- added sigmoid-based edge scaling from:
  - normalized `predicted_frontier_score`,
  - `predicted_trade_utility`,
  - challenge fail-risk and funded breach-risk penalties.
- challenge stage now sizes risk dynamically between `challenge_min_risk_pct` and `challenge_max_risk_pct`,
- funded stage now sizes risk dynamically between `funded_min_risk_pct` and `funded_max_risk_pct`,
- default replay trade cap changed from `3` to `2`.

First adaptive curve:

- brought risk above the prior `0.35%-0.50%` cluster,
- but still capped practical realized usage below `0.70%`.

Second challenge-risk push in this session:

- increased the edge-quality sensitivity,
- softened the challenge fail-risk damping,
- raised the floor for strong challenge-stage setups.

Net effect:

- the same selected trades are now sized more aggressively in challenge mode.

### 4. Default Config Alignment

Updated:

- [scripts/frontier_account_state.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_account_state.py:1)
- [scripts/frontier_utility_dataset.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_utility_dataset.py:1)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)

Changes:

- default `max_trades_per_day` was reduced from `3` to `2` across account state, dataset build, replay, and workbench CLI.

Net effect:

- the research path and replay path now default to the intended “best 2 trades per day” operating mode.

## Run History

### A. First refreshed `300k` run with phase-2 targets

Outcome:

- artifact regenerated successfully,
- replay took `0` trades,
- all candidates were rejected on score.

Key metrics:

- test mAP: `0.115832`
- test ROC AUC: `0.948479`
- test utility MAE: `0.101226`
- test utility correlation: `0.290582`
- replay trades: `0`
- pass probability 30/60/90: `0.0 / 0.0 / 0.0`

### B. Smoke validation after alignment fix

Artifact:

- `artifacts/frontier_utility/prop_stage_smoke`

Outcome:

- normalized frontier score became usable,
- replay started taking trades again.

Key metrics:

- normalized frontier score positive rate: `1.0`
- replay trades: `14`
- return: `1.0448%`
- pass probability 30/60/90: `0.006 / 0.338 / 0.854`

This validated that the alignment fix worked before spending time on the full `300k` rerun.

### C. Full `300k` rerun after alignment + adaptive sizing

Outcome:

- replay resumed trading,
- artifact passed the challenge on the recorded test path.

Key metrics:

- trades: `66`
- active trading days: `33`
- average trades per active day: `2.0`
- win rate: `0.30303`
- expectancy: `0.439906R`
- return: `14.83%`
- max drawdown: `1.0174%`
- reached target: `true`
- days to pass: `18`
- pass probability 30/60/90: `0.878 / 1.0 / 1.0`

Risk distribution:

- mean risk: `0.429%`
- median risk: `0.350%`
- min risk: `0.246%`
- max risk: `0.683%`

### D. Full `300k` rerun after challenge max-risk push

Outcome:

- same `66` trade count,
- higher challenge-stage sizing,
- faster pass and better total return,
- slightly higher drawdown but still well controlled.

Final key metrics:

- trades: `66`
- active trading days: `33`
- average trades per active day: `2.0`
- average trades per full 34-day span: `1.94`
- win rate: `0.318182`
- expectancy: `0.463918R`
- total R: `30.61862R`
- return: `17.015%`
- max drawdown: `1.1942%`
- reached target: `true`
- days to pass: `11`
- pass probability 30/60/90: `0.938 / 1.0 / 1.0`
- median days to pass: `11.0`
- rolling-start pass rate: `0.272727`

Final risk distribution:

- mean risk: `0.463341%`
- median risk: `0.343350%`
- min risk: `0.249000%`
- max risk: `0.785700%`
- 90th percentile risk: `0.772400%`
- 95th percentile risk: `0.781275%`
- trades at `>= 0.75%`: `11`
- trades at `>= 0.90%`: `0`
- trades at `>= 1.0%`: `0`

## Comparison Versus Canonical Frontier Workbench

Canonical baseline:

- `artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench`

Comparison output refreshed in this session:

- [docs/frontier_utility_us100_session_refined_rerun_20260415_regime_workbench_300k_compare_20260420.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/frontier_utility_us100_session_refined_rerun_20260415_regime_workbench_300k_compare_20260420.md:1)
- [artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/compare_vs_canonical_20260420.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/compare_vs_canonical_20260420.json:1)

Final deltas versus canonical frontier baseline:

- fewer trades: `66` vs `180`
- lower win rate: `0.318182` vs `0.505556`
- better expectancy: `0.463918R` vs `0.348148R`
- lower return: `17.015%` vs `23.8254%`
- lower max drawdown: `1.1942%` vs `2.2716%`
- faster pass: `11` vs `24` days
- much better 30-day pass probability: `0.938` vs `0.552`

Interpretation:

- the utility regime path is now a more selective, lower-drawdown, faster-pass challenge model,
- but it still produces lower total return than the canonical frontier workbench.

## Final State At End Of Session

The utility regime pipeline is no longer blocked by the “zero-trade” failure mode.

Current operating profile:

- the model takes the best `2` trades per active day on average,
- it passes the historical challenge path quickly,
- it sizes challenge risk adaptively instead of using static stage buckets,
- it can push into the `0.75%-0.80%` range on stronger trades,
- it still does not naturally reach `1.0%` risk often under the current edge/risk calibration.

Current documentation and artifacts updated in this session:

- [docs/frontier_utility_us100_session_refined_rerun_20260415_regime_workbench_300k.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/frontier_utility_us100_session_refined_rerun_20260415_regime_workbench_300k.md:1)
- [docs/frontier_utility_us100_session_refined_rerun_20260415_regime_workbench_300k_compare_20260420.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/frontier_utility_us100_session_refined_rerun_20260415_regime_workbench_300k_compare_20260420.md:1)
- [artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/training_summary.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/training_summary.json:1)
- [artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/analysis_report.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/analysis_report.json:1)
- [artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/replay_report.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k/replay_report.json:1)

## Recommended Next Step

If the goal remains “reach `1.0%` challenge risk more often on the best setups,” the next controlled step should be one of:

1. further relax challenge fail-risk damping for top-decile candidates only,
2. add an explicit risk head to the model so risk is learned rather than derived from score heuristics,
3. run a small sweep on challenge risk-floor and score-to-risk slope while holding the `2`-trade daily cap fixed.
