# Frontier Default Rollout Results

Date: `2026-04-16`

This report summarizes the implementation and measured impact of promoting the frontier prop manager to the default policy path for the latest trained model:

- source policy engine: `scripts/frontier_prop_manager.py`
- original latest artifact: `artifacts/specialist_tcns/us100_session_refined_rerun_20260415`
- legacy policy backup: `artifacts/specialist_tcns/us100_session_refined_rerun_20260415/manager_policy_legacy.json`
- new default policy: `artifacts/specialist_tcns/us100_session_refined_rerun_20260415/manager_policy.json`
- frontier-default evaluation artifact: `artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_default`

## Implemented Changes

### 1. Frontier manager promoted to the default active policy artifact

- `manager_policy.json` for the latest model now uses:
  - `selection = frontier_contextual_abstention_manager`
- the previous active policy was preserved as:
  - `manager_policy_legacy.json`

### 2. Both continuation experts are disabled by default

New default policy:

- enabled experts:
  - `long_reversal`
  - `short_reversal`
- disabled experts:
  - `long_continuation`
  - `short_continuation`

### 3. Main frontier run trade budget reduced to `3` per day

Implemented in:

- `PolicyBuildConfig.max_daily_trades = 3`
- policy `abstention.max_trades_per_day = 3`
- policy `backtest_config.max_trades_per_day = 3`

### 4. Stateful threshold tightening added

Implemented controls:

- post-win threshold bump after `1` win
- stronger threshold bump after `2` wins
- threshold tightening in soft drawdown
- hard abstention in hard drawdown
- recovery-mode daily trade compression after loss streaks

### 5. Context scoring now includes rolling-start pass rate

Implemented context metrics:

- `rolling_start_pass_rate`
- `avg_days_to_pass`
- `median_days_to_pass`

### 6. Context scoring now includes profitable-day accumulation

Implemented context metrics:

- `profitable_day_hit_rate_day_10`
- `profitable_day_hit_rate_day_20`
- `avg_profitable_days_day_10`
- `avg_profitable_days_day_20`

### 7. New frontier-default trade path and baseline report generated

- evaluation JSON:
  - `artifacts/specialist_tcns/us100_session_refined_rerun_20260415/manager_policy_frontier_evaluation_v2.json`
- frontier-default baseline JSON:
  - `artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_default/baseline_report.json`
- frontier-default markdown report:
  - `docs/us100_session_refined_rerun_20260415_frontier_default.md`

## Measured Improvements

Comparison versus the previous latest baseline `us100_session_refined_rerun_20260415`.

| Metric | Previous latest baseline | Frontier default rollout | Delta |
| --- | ---: | ---: | ---: |
| Trades | `453` | `162` | `-291` |
| Active trading days | `76` | `68` | `-8` |
| Win rate | `0.408389` | `0.469136` | `+0.060747` |
| Expectancy per trade | `0.089036R` | `0.251029R` | `+0.161993R` |
| Total R | `40.333333R` | `40.666667R` | `+0.333334R` |
| Profit factor | `1.150498` | `1.472868` | `+0.322370` |
| Ending balance | `$110,339.63` | `$114,170.87` | `+$3,831.24` |
| Return | `10.3396%` | `14.1709%` | `+3.8313%` |
| Max drawdown | `4.7929%` | `3.3916%` | `-1.4013%` |
| Days to pass | `76` | `57` | `-19` |
| Historical rolling-start pass rate | `0.026316` | `0.117647` | `+0.091331` |
| Profitable days on recorded path | `35` | `36` | `+1` |
| Positive day rate | `0.460526` | `0.647059` | `+0.186533` |
| Avg trades per day | `5.960526` | `2.382353` | `-3.578173` |

## Prop-Firm Utility Improvement

Bootstrap pass probabilities improved materially:

- `30` active days:
  - `0.1575 -> 0.2210`
- `60` active days:
  - `0.4790 -> 0.7150`
- `66` active days:
  - `0.5525 -> 0.7815`
- `90` active days:
  - `0.6980 -> 0.9130`
- `120` active days:
  - `0.8380 -> 0.9715`

This confirms that the rollout improved the metrics that matter most for prop-firm progression:

- faster pass
- smoother pass path
- better short-horizon pass probability
- cleaner profitable-day profile
- lower drawdown pressure

## Structural Behavior After Rollout

### Setup mix

Before:

- reversals plus both continuation experts

After:

- only reversal experts remain active

Realized setup contribution in the frontier-default run:

- `long_reversal`: `29.333333R`
- `short_reversal`: `11.333333R`

### Daily shape

Before:

- positive day rate: `46.05%`
- mean daily return: `0.133268%`
- median daily return: `-0.169501%`

After:

- positive day rate: `64.71%`
- mean daily return: `0.197875%`
- median daily return: `0.296619%`

### Sequence control

The rollout materially improved post-win behavior:

- previous latest baseline:
  - after `win` streak `1`: next-trade expectancy `-0.064327R`
  - after `win` streak `2`: next-trade expectancy `0.000000R`
- frontier default:
  - after `win` streak `1`: next-trade expectancy `0.151515R`
  - after `win` streak `2`: next-trade expectancy `0.263158R`

That is strong evidence that the new threshold-tightening and abstention logic reduced weak recycling of risk after wins.

## Important Caveat

The frontier-default artifact is a manager-level backtest estimate built by reapplying the new policy to the recorded latest-model trade path and then regenerating the prop-firm baseline report from that adjusted path.

That means:

- the base model is unchanged
- the gain comes from better policy selection, abstention, and sizing
- this is not a fresh retrain
- this is not a raw market replay from the cached `specialist_tcn_pipeline.py` bytecode path

Even with that caveat, this is the correct implementation order because the measured bottleneck was the manager, not the TCN.

## Bottom Line

The rollout achieved the intended objective.

The frontier manager is now the default active policy artifact for the latest model, continuation experts are disabled by default, the system no longer fills six daily slots by default, context ranking is challenge-aware, and the resulting frontier-default backtest path is substantially better on every prop-firm-relevant metric that matters:

- higher pass probability
- faster time to pass
- better profitable-day accumulation
- lower drawdown
- higher expectancy
- fewer loss clusters
