# Frontier Pass-Utility Execution Plan

Date: `2026-04-17`

## Objective

Turn the current specialist TCN plus frontier manager stack into a prop-firm-first system that:

- treats frontier-managed outputs as the canonical benchmark
- trades fewer but higher-utility opportunities
- ranks candidates by challenge pass utility instead of raw setup probability
- keeps continuation experts disabled until they prove additive value under slot competition
- actively suppresses weak months and loss-cluster regimes

This plan addresses six concrete priorities:

1. Keep continuation experts disabled by default until retrained on regime-filtered labels and judged on challenge utility, not classification lift.
2. Tighten or remove `short_reversal / asia / build_20_40` sub-slices that live in the weakest probability buckets.
3. Refit ranking and calibration around pass utility.
4. Promote frontier wrapper outputs, not raw verification outputs, as the canonical benchmark.
5. Optimize directly on `30/60/90` day pass probability, days-to-pass, profitable-day hit rate, and loss-cluster penalty.
6. Add explicit kill-switches for weak months, with February 2025 as the current reference failure pocket.

## Current Diagnosis Snapshot

The latest rerun exposes a clean split between raw path quality and frontier-managed path quality:

- raw path: `453` trades, `10.3396%` return, `4.7929%` max drawdown, pass in `76` trading days
- frontier-managed path: `162` trades, `14.1709%` return, `3.3916%` max drawdown, pass in `57` trading days

Observed failure modes:

- continuation setups are negative on realized R in the raw path
- `short_reversal / asia / build_20_40` is positive overall, but its weakest probability buckets still dilute edge
- model probability is not monotonic enough with realized R
- the repo still contains raw verification outputs that are easy to mistake for the active benchmark
- path-quality metrics are not yet the first-class optimization target everywhere
- weak regime pockets are diagnosed after the fact rather than enforced by explicit manager controls

## Delivery Strategy

Implement this in three layers:

1. Benchmark governance
2. Manager and calibration upgrades
3. Data and retraining loop for continuation recovery

The sequence matters. Benchmark governance must be fixed first so later improvements are evaluated on the right target.

## Workstream 1. Canonical Frontier Benchmark

Priority addressed:

- promote the frontier wrapper outputs, not the raw verification path, as the canonical benchmark

### Goal

Ensure every baseline, report, comparison, and acceptance gate points to the frontier-managed backtest outputs produced by `specialist_tcn_pipeline.py backtest` under the frontier wrapper path.

### File scope

Primary files:

- [scripts/specialist_tcn_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/specialist_tcn_pipeline.py:1)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)
- [scripts/generate_baseline_report.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/generate_baseline_report.py:1)

Docs and artifacts to update:

- `docs/latest_model_backtest_comparison_20260416.md`
- `docs/current_baseline_us100_session_refined.md`
- `docs/fundedhive_baseline_us100_session_refined.md`
- future benchmark docs generated from frontier outputs only

### Implementation steps

1. Rename raw-path outputs in reporting surfaces to `raw_candidate_path_*` or equivalent so they are never presented as the benchmark.
2. Update report generators to treat:
   - `backtest_summary.json`
   - `backtest_trades.csv.gz`
   as canonical when the active policy is frontier.
3. Add explicit metadata fields in summaries:
   - `execution_mode = raw_candidate_path | frontier_managed`
   - `policy_selection`
   - `raw_source_summary`
4. Make the comparison workflow display both paths, but always label the frontier-managed path as the acceptance baseline.
5. Add a validation check that fails report generation if a raw-path file is accidentally used as the headline benchmark for a frontier artifact.

### Acceptance criteria

- no benchmark doc or comparison report can silently present raw cached outputs as the primary result for frontier artifacts
- the default artifact comparison path uses frontier-managed outputs
- every final summary clearly says whether it is `raw_candidate_path` or `frontier_managed`

## Workstream 2. Continuation Expert Freeze and Recovery Path

Priority addressed:

- keep continuation experts disabled by default until retrained on regime-filtered labels and judged on challenge utility, not classification lift

### Goal

Preserve the current default of disabling continuation experts, then build a controlled path for reintroducing them only if they improve integrated challenge utility under daily trade-slot competition.

### File scope

Primary files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)
- [scripts/frontier_utility_dataset.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_utility_dataset.py:1)
- [scripts/frontier_utility_model.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_utility_model.py:1)

### Implementation steps

1. Lock the default policy template so `long_continuation` and `short_continuation` remain disabled in all benchmarked frontier builds.
2. Create a continuation-retraining branch of the dataset with regime-filtered label eligibility:
   - high trend persistence
   - low chop score
   - favorable opening-drive state
   - acceptable volatility regime percentile
3. Add continuation-specific label diagnostics:
   - label frequency by regime
   - realized R by regime
   - pass-utility contribution by regime
4. Retrain continuation specialists only on filtered regimes and score them in a shadow mode first.
5. Evaluate continuation re-entry with full integrated replay:
   - continuation disabled
   - continuation enabled globally
   - continuation enabled only in whitelisted regimes
6. Accept continuation only if it improves frontier acceptance metrics after slot competition, not if it merely improves precision or lift.

### Required new metrics

- marginal `30/60/90` day pass probability delta with continuation enabled
- delta in median days-to-pass
- delta in profitable-day hit rate by day `10` and day `20`
- delta in longest loss streak
- delta in worst-month return

### Acceptance criteria

- continuation remains disabled by default until a shadow replay proves additive pass utility
- no continuation expert is promoted based on classification lift alone
- any re-enabled continuation slice must be tied to explicit regime whitelists

## Workstream 3. `short_reversal / asia / build_20_40` Probability Bucket Cleanup

Priority addressed:

- tighten or remove `short_reversal / asia / build_20_40` sub-slices that live in the weakest probability buckets

### Goal

Preserve the profitable core of `short_reversal / asia / build_20_40` while removing the low-quality tail that still passes the current threshold.

### File scope

Primary files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/backtest_diagnostics.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/backtest_diagnostics.py:1)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)

### Implementation steps

1. Add bucket-level diagnostics for every `(setup, market_session, session_phase)` slice:
   - trade count
   - win rate
   - expectancy
   - pass-utility contribution
   - drawdown contribution
2. For `short_reversal / asia / build_20_40`, identify the lowest buckets by:
   - negative or low expectancy
   - weak pass-probability contribution
   - elevated loss-cluster contribution
3. Add one of two controls:
   - tighter context threshold for weak buckets
   - explicit bucket blacklist if the tail remains unstable
4. Support bucket-aware manager rules:
   - `min_probability_surplus`
   - `bucket_rank_floor`
   - `risk_pct_by_bucket`
5. Re-run a threshold sweep specifically for this slice and optimize on pass utility, not total trade count.

### Experiments to run

1. baseline frontier threshold
2. tighter static threshold
3. threshold plus bucket blacklist
4. threshold plus risk haircut on weak buckets
5. full removal of the slice

### Acceptance criteria

- the surviving `short_reversal / asia / build_20_40` slice has monotonic or near-monotonic realized edge by bucket
- the slice does not worsen longest loss streak or weak-month drawdown
- if cleanup cannot produce stable bucket behavior, the slice is removed

## Workstream 4. Pass-Utility Calibration and Ranking Refit

Priority addressed:

- refit ranking and calibration around pass utility
- optimize directly on `30/60/90` day pass probability, days-to-pass, profitable-day hit rate, and loss-cluster penalty

### Goal

Replace the current probability-first ranking with a utility-first ranking surface that is calibrated to challenge outcomes rather than mostly setup occurrence.

### File scope

Primary files:

- [scripts/frontier_utility_model.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_utility_model.py:1)
- [scripts/frontier_allocator.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_allocator.py:1)
- [scripts/frontier_replay.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_replay.py:1)
- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)

### Implementation steps

1. Introduce new supervised targets at candidate level:
   - `delta_pass_prob_30`
   - `delta_pass_prob_60`
   - `delta_pass_prob_90`
   - `delta_days_to_pass`
   - `delta_profitable_day_hit_rate`
   - `loss_cluster_penalty`
   - `trade_challenge_utility`
2. Train calibration layers against those targets instead of only against setup hit labels.
3. Replace the ranking score with an explicit frontier utility score:

```text
frontier_score =
  w1 * delta_pass_prob_30
  + w2 * delta_pass_prob_60
  + w3 * delta_pass_prob_90
  - w4 * normalized_days_to_pass
  + w5 * delta_profitable_day_hit_rate
  - w6 * loss_cluster_penalty
```

4. Learn or grid-search weights on validation and lock them by challenge utility, not by AP.
5. Update policy summaries and diagnostics to show:
   - bucket calibration against realized R
   - bucket calibration against pass probability
   - ranking correlation with realized challenge utility
6. Update allocator tie-breaking to use frontier score first, setup probability second.

### Validation experiments

1. current probability-based ranking
2. utility score without `90` day term
3. utility score with `90` day term
4. utility score plus loss-cluster penalty
5. utility score plus account-state-aware calibration

### Acceptance criteria

- validation and test rankings are materially more monotonic by realized challenge utility than the current setup-probability ordering
- the chosen score improves pass probability and/or reduces days-to-pass without worsening max drawdown
- calibration reports explicitly show improvement at the bucket level

## Workstream 5. Challenge-Metric-First Evaluation Stack

Priority addressed:

- optimize directly on `30/60/90` day pass probability, days-to-pass, profitable-day hit rate, and loss-cluster penalty

### Goal

Make challenge metrics the first-class acceptance surface across training summaries, replay summaries, policy evaluation, and model comparison.

### File scope

Primary files:

- [scripts/frontier_replay.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_replay.py:1)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)
- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/backtest_diagnostics.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/backtest_diagnostics.py:1)

### Implementation steps

1. Standardize an acceptance metric block used everywhere:
   - `pass_probability_30`
   - `pass_probability_60`
   - `pass_probability_90`
   - `median_days_to_pass`
   - `avg_days_to_pass`
   - `profitable_day_hit_rate_day_10`
   - `profitable_day_hit_rate_day_20`
   - `longest_trade_loss_streak`
   - `longest_negative_day_streak`
   - `worst_month_return_pct`
   - `loss_cluster_penalty`
2. Add those fields to:
   - training summaries
   - replay summaries
   - policy evaluation outputs
   - comparison reports
3. Make model selection and policy selection require explicit improvement on this block.
4. Add a benchmark scoreboard command in the research workbench that ranks artifacts on these metrics first and raw expectancy second.
5. Add fail-fast guards for frontier acceptance:
   - reject artifacts with worse `60` day pass probability than benchmark unless offset by a clear days-to-pass improvement
   - reject artifacts with materially worse longest loss streak or worst-month return

### Acceptance criteria

- no frontier artifact can be promoted without challenge metrics
- comparison reports rank by pass utility first
- benchmark acceptance logic is deterministic and challenge-metric-first

## Workstream 6. Weak-Month Kill-Switches

Priority addressed:

- add explicit kill-switches for weak months, with February 2025 as the obvious stress pocket

### Goal

Convert weak-month diagnosis into a systematic live control layer that cuts or shuts off exposure when the current month resembles a known failure regime.

### File scope

Primary files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/frontier_account_state.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_account_state.py:1)
- [scripts/frontier_replay.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_replay.py:1)

### Implementation steps

1. Add month-level and rolling-regime diagnostics:
   - monthly R
   - monthly return
   - rolling 10-day and 20-day pass utility
   - rolling loss-cluster penalty
2. Define kill-switch states:
   - `normal`
   - `soft_defensive`
   - `hard_defensive`
   - `shutdown`
3. Trigger states from current account and regime conditions, not calendar month alone:
   - recent rolling utility below floor
   - recent loss-cluster penalty above ceiling
   - current drawdown above soft or hard threshold
   - current slice-specific degradation relative to benchmark
4. Map state to actions:
   - tighten thresholds
   - reduce max daily trades
   - reduce risk per trade
   - disable weakest setup-context slices
   - trade nothing until recovery criteria are met
5. Add recovery rules:
   - minimum cooldown duration
   - profitability requirement over trailing days
   - regime normalization requirement
6. Backtest kill-switch logic against February 2025 and other stress periods to ensure it improves path quality instead of merely reducing exposure indiscriminately.

### Acceptance criteria

- weak-month stress pockets are detected by live rules rather than only by retrospective reporting
- kill-switch logic reduces drawdown and loss-cluster severity in stress windows
- kill-switch rules do not destroy pass probability in healthy windows

## Execution Order

### Phase 1. Benchmark governance and diagnostics

1. Complete Workstream 1.
2. Extend diagnostics for bucket-level and challenge-level reporting.
3. Freeze continuation defaults.

### Phase 2. Manager-layer edge cleanup

1. Complete Workstream 3.
2. Complete Workstream 6 with source-level controls.
3. Re-run frontier policy sweeps on the latest artifact family.

### Phase 3. Utility-centric scoring

1. Complete Workstream 5 metric standardization.
2. Complete Workstream 4 ranking and calibration refit.
3. Promote the best utility-ranked frontier policy as the new benchmark.

### Phase 4. Continuation recovery

1. Complete Workstream 2 regime-filtered continuation retraining.
2. Re-test continuation in shadow mode and then in integrated replay.
3. Re-enable only slices that pass the challenge-utility gates.

## Definition of Done

This plan is complete only when all of the following are true:

- frontier-managed outputs are the canonical benchmark everywhere
- continuation experts remain disabled by default unless full replay proves additive pass utility
- `short_reversal / asia / build_20_40` no longer contains unstable low-utility tail buckets, or the slice is removed
- ranking and calibration are challenge-utility-first and measurably more monotonic
- artifact acceptance is based on `30/60/90` day pass probability, days-to-pass, profitable-day hit rates, and loss-cluster controls
- weak-month kill-switches are active and validated in replay

## Immediate Next Sprint

The next implementation sprint should ship these concrete items:

1. Benchmark-governance changes from Workstream 1.
2. Bucket diagnostics plus threshold sweep for `short_reversal / asia / build_20_40`.
3. Challenge-metric scoreboard additions to replay and workbench outputs.
4. First version of weak-month kill-switch logic in the frontier manager.

That sprint creates the minimum reliable foundation for the later utility-model refit and continuation-retraining cycle.
