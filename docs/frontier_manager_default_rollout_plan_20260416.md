# Frontier Manager Default Rollout Plan

Date: `2026-04-16`

Objective: make the prop-firm manager optimize challenge utility rather than raw trade throughput by promoting the frontier manager to the default policy layer.

Primary targets:

1. Make `frontier_contextual_abstention_manager` the default backtest policy.
2. Disable both continuation experts by default.
3. Reduce `max_daily_trades` from `6` to `3` for the main frontier run.
4. Add state-dependent threshold tightening after win streaks and in drawdown.
5. Add rolling-start pass rate directly into context scoring.
6. Add profitable-day accumulation metrics into context scoring.
7. Re-run the frontier manager and compare against the current baseline.

## Current Code Surface

Relevant files already present in source:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/prop_firm_rules.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/prop_firm_rules.py:1)
- [scripts/generate_baseline_report.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/generate_baseline_report.py:1)
- [docs/latest_model_backtest_comparison_20260416.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/latest_model_backtest_comparison_20260416.md:1)

Relevant artifacts:

- [manager_policy.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415/manager_policy.json:1)
- [manager_policy_frontier.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415/manager_policy_frontier.json:1)
- [manager_policy_frontier_evaluation.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415/manager_policy_frontier_evaluation.json:1)
- [baseline_report.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415/baseline_report.json:1)
- [backtest_trades.csv.gz](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415/backtest_trades.csv.gz:1)

Constraint:

- [scripts/specialist_tcn_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/specialist_tcn_pipeline.py:1) is a wrapper around cached bytecode, so promoting the frontier manager to the default backtest policy may require either:
  - a source-level hook outside the cached module, or
  - replacing the active `manager_policy.json` artifact generation path until the backtest source is fully materialized.

## Success Criteria

The rollout is successful only if the default policy path improves prop-firm utility, not merely raw backtest return.

Primary scorecard:

- higher rolling-start pass rate
- higher bootstrap pass probabilities at `30`, `60`, `66`, `90`
- lower median days to pass
- at least equal or higher profitable-day accumulation
- lower or equal max drawdown
- fewer trades and fewer days at trade cap

Secondary scorecard:

- higher expectancy per trade
- less negative contribution from continuation setups
- lower loss-cluster concentration

## Implementation Phases

### Phase 1. Promote the frontier manager to the default policy path

Goal:

- make the active backtest policy use `frontier_contextual_abstention_manager` semantics by default

Planned changes:

- add a canonical policy output target so the frontier build writes to `manager_policy.json` for frontier runs instead of only `manager_policy_frontier.json`
- if the cached backtest module cannot be changed directly, add a source-level orchestration step that:
  - builds frontier policy
  - copies or writes it to the active `manager_policy.json` path
  - runs backtest with that policy path
- preserve the legacy policy as `manager_policy_legacy.json` for comparison

Likely files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/specialist_tcn_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/specialist_tcn_pipeline.py:1)

Acceptance criteria:

- a default run uses `selection = frontier_contextual_abstention_manager`
- the resulting backtest summary references the frontier policy as the active policy input

### Phase 2. Disable both continuation experts by default

Goal:

- start from the realized edge, not from model symmetry

Planned changes:

- change `DEFAULT_DISABLED_SETUPS` from `{ "long_continuation" }` to:
  - `long_continuation`
  - `short_continuation`
- keep a re-enable path only if a setup clears minimum realized challenge-utility thresholds
- add a note in policy payload explaining that continuation experts are disabled pending positive realized prop utility

Likely file:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)

Acceptance criteria:

- generated frontier policy enables only reversal experts unless continuation experts materially re-qualify

### Phase 3. Reduce max daily trades from 6 to 3 for the main frontier run

Goal:

- stop filling the daily slot budget with marginal trades

Planned changes:

- change `PolicyBuildConfig.max_daily_trades` default from `5` to `3`
- ensure policy payload writes `abstention.max_trades_per_day = 3`
- ensure `backtest_config.max_trades_per_day = 3`
- preserve a config override for research sweeps

Likely file:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)

Acceptance criteria:

- frontier policy mainline run uses `3` maximum trades per day
- comparison report includes trade-count compression versus current baseline

### Phase 4. Add state-dependent threshold tightening after win streaks and in drawdown

Goal:

- reduce give-back after favorable streaks and suppress weak-edge trades while underwater

Planned changes:

- extend policy payload with a `state_controls` block:
  - `post_win_1_threshold_bump`
  - `post_win_2_threshold_bump`
  - `soft_drawdown_threshold_bump`
  - `hard_drawdown_action = abstain`
  - optional `recovery_mode_max_trades`
- extend `apply_frontier_policy` to maintain a rolling state:
  - consecutive wins
  - consecutive losses
  - running peak
  - drawdown state
- compute effective threshold as:

```text
effective_threshold =
  context_threshold
  + post_win_adjustment
  + drawdown_adjustment
```

- apply trade suppression rules:
  - tighten after `1` win
  - tighten more after `2` wins
  - hard abstain beyond hard drawdown
  - optional daily trade compression in recovery mode

Likely file:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)

Acceptance criteria:

- policy payload documents state controls
- evaluation path shows fewer post-win give-back trades

### Phase 5. Add rolling-start pass rate directly into context scoring

Goal:

- rank contexts by challenge pass utility, not just trade expectancy

Planned changes:

- add a new context-level metric computation function based on grouped daily returns and `evaluate_propfirm_path`
- for each `setup x market_session x session_phase` context, compute:
  - `rolling_start_pass_rate`
  - `min_days_to_pass`
  - `median_days_to_pass`
  - `avg_days_to_pass`
- merge these metrics into `score_contexts`
- update `path_utility_score` to include rolling-start pass rate directly

Suggested utility revision:

```text
path_utility_score =
  0.25 * expectancy_r_norm
  + 0.15 * profit_factor_norm
  + 0.20 * positive_day_rate_norm
  + 0.15 * avg_day_r_norm
  + 0.20 * rolling_start_pass_rate_norm
  - 0.15 * loss_cluster_penalty_norm
```

Likely files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/prop_firm_rules.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/prop_firm_rules.py:1)

Acceptance criteria:

- generated policy contexts carry rolling-start metrics
- context ranking changes when pass geometry is weak despite decent expectancy

### Phase 6. Add profitable-day accumulation metrics into context scoring

Goal:

- directly reward contexts that help satisfy the `3` profitable-day requirement quickly

Planned changes:

- extend context path stats with:
  - `profitable_day_rate`
  - `avg_day_r`
  - `profit_day_hit_rate_day_10`
  - `profit_day_hit_rate_day_20`
  - optional `avg_profitable_days_to_pass`
- compute these from grouped context-level day returns
- include them in the context scoring frame and policy payload
- bias context retention toward slices that produce cleaner daily outcomes even if raw trade count drops

Likely files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/prop_firm_rules.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/prop_firm_rules.py:1)

Acceptance criteria:

- policy payload includes profitable-day metrics per retained context
- final context ranking is no longer dominated by total trade `R` alone

### Phase 7. Re-run frontier manager and compare against current baseline

Goal:

- validate the new default manager against the current documented baseline on the same artifact

Planned changes:

- generate new frontier policy from latest rerun artifact
- evaluate the policy on the checked-in trade path
- if feasible, run the full backtest through the active default policy path
- regenerate comparison report with:
  - baseline
  - previous frontier estimate
  - new frontier-default run

Likely commands:

```powershell
python scripts\frontier_prop_manager.py build-policy `
  --analysis-report artifacts\specialist_tcns\us100_session_refined_rerun_20260415\analysis_report.json `
  --baseline-report artifacts\specialist_tcns\us100_session_refined_rerun_20260415\baseline_report.json `
  --trades artifacts\specialist_tcns\us100_session_refined_rerun_20260415\backtest_trades.csv.gz `
  --output artifacts\specialist_tcns\us100_session_refined_rerun_20260415\manager_policy.json
```

```powershell
python scripts\frontier_prop_manager.py evaluate-policy `
  --policy artifacts\specialist_tcns\us100_session_refined_rerun_20260415\manager_policy.json `
  --trades artifacts\specialist_tcns\us100_session_refined_rerun_20260415\backtest_trades.csv.gz `
  --baseline-report artifacts\specialist_tcns\us100_session_refined_rerun_20260415\baseline_report.json `
  --output artifacts\specialist_tcns\us100_session_refined_rerun_20260415\manager_policy_frontier_evaluation_v2.json
```

Acceptance criteria:

- comparison output clearly shows deltas versus current baseline
- any degradation in pass probability or profitable-day accumulation blocks rollout

## Detailed Task Breakdown

1. Refactor policy defaults in `PolicyBuildConfig`.
2. Expand disabled-setup defaults to both continuation setups.
3. Add context-level rolling-start pass geometry functions.
4. Add context-level profitable-day accumulation functions.
5. Reweight `path_utility_score` toward pass utility.
6. Add stateful threshold logic in `apply_frontier_policy`.
7. Add optional policy metadata fields for state controls and context diagnostics.
8. Redirect frontier build output to the active default `manager_policy.json` path for the main run.
9. Re-evaluate the latest artifact and generate an updated comparison report.

## Risks

### Integration risk

The source wrapper for `specialist_tcn_pipeline.py` delegates to cached bytecode. If default policy selection is embedded there, promoting the frontier manager may require a wrapper-level artifact swap rather than a normal source patch.

### Metric leakage risk

Context scoring must remain validation-derived or evaluation-derived in a way that matches the repo’s current methodology. Do not accidentally use test-only context scores for model selection logic without documenting that the result is a policy estimate rather than a clean out-of-sample backtest.

### Over-pruning risk

Reducing trades too aggressively may improve expectancy but hurt profitable-day accumulation. That is why profitable-day metrics must be incorporated before finalizing the `3` trade/day cap.

## Recommended Rollout Order

1. Implement Phases `2`, `3`, `5`, and `6` first in `frontier_prop_manager.py`.
2. Implement Phase `4` stateful threshold logic.
3. Evaluate policy on the checked-in trade path.
4. Only then perform Phase `1` default-policy promotion.
5. Run Phase `7` comparison and freeze the new default only if pass-utility metrics improve.

## Definition Of Done

Done means:

- the default active manager is `frontier_contextual_abstention_manager`
- continuation experts are disabled by default
- frontier mainline uses `3` max trades per day
- context scoring includes rolling-start pass rate and profitable-day accumulation
- thresholding reacts to post-win state and drawdown state
- latest frontier run is compared against the current baseline in a checked-in report
- the new default improves challenge utility on the repo scorecard
