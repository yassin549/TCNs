# Latest Model Backtest Comparison

Generated on `2026-04-16` for the latest trained specialist TCN artifact:

- latest artifact: `artifacts/specialist_tcns/us100_session_refined_rerun_20260415`
- verification backtest: `artifacts/specialist_tcns/us100_session_refined_rerun_20260415/backtest_summary_verification.json`
- previous documented baselines:
  - `docs/current_baseline_us100_session_refined.md`
  - `docs/fundedhive_baseline_us100_session_refined.md`
  - `docs/us100_session_refined_rerun_20260415_baseline.md`

## Verification

The latest backtest was re-run through the repository backtest path and the verification output matched the documented baseline exactly.

- trades: `453`
- trading days: `76`
- win rate: `0.408389`
- expectancy: `0.089036R`
- total return: `10.3396%`
- ending balance: `$110,339.63`
- max drawdown: `4.7929%`
- FundedHive-style recorded-path pass: `True`

## Model Comparison

| Model snapshot | Policy framing | Trades | Trading days | Return | Max DD | Expectancy | Profit factor | Recorded-path pass |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `us100_session_refined` | legacy pre-FundedHive rules | 391 | 66 | `8.3718%` | `5.4092%` | `0.084399R` | `1.142241` | `True` under old rules |
| `us100_session_refined_fundedhive` | same old model, re-evaluated under FundedHive | 391 | 66 | `8.3718%` | `5.4092%` | `0.084399R` | `1.142241` | `False` |
| `us100_session_refined_rerun_20260415` | latest model under active FundedHive-style rules | 453 | 76 | `10.3396%` | `4.7929%` | `0.089036R` | `1.150498` | `True` |

## What Improved

- The latest model closes the FundedHive gap. The previous `us100_session_refined` model failed under the `10%` target plus profitable-day requirement, while the rerun passes on the recorded path.
- Relative to the previous model snapshot, the rerun adds `62` trades, `+7.333333R`, `+1.9678%` return, and reduces max drawdown by `0.6163%`.
- Profitable days improve from `32` to `35`, which matters directly for prop-firm passability.
- Bootstrap pass probability also improves:
  - `30`-day horizon: `13.9% -> 15.75%`
  - `60`-day horizon: `46.3% -> 47.9%`
  - `66`-day horizon: `50.3% -> 55.25%`

## Bottlenecks

### 1. The manager is still overtrading weak edge

The strongest evidence is internal to the latest artifact:

- current baseline: `453` trades, `10.3396%` return, `0.089036R` expectancy
- frontier policy estimate on the same model: `236` trades, `16.5589%` return, `0.19774R` expectancy

That means the main inefficiency is not lack of model output volume. It is that the active manager still deploys too many marginal trades.

Supporting signs:

- days at max trade cap: `75 / 76`
- skipped by daily trade cap: `63,649`
- average trades per active day: `5.96`

The model is effectively saturating the trade budget every day. In prop-firm terms, that is the wrong optimization target. The goal is faster and smoother challenge progression, not maximum trade count.

### 2. Continuation experts are diluting realized edge

Latest realized test breakdown by setup:

- `short_reversal`: `24.0R`
- `long_reversal`: `20.0R`
- `long_continuation`: `-1.666667R`
- `short_continuation`: `-2.0R`

Both continuation experts are negative on realized backtest PnL even though they still consume trade slots. The repo's own frontier policy disables both continuation experts and concentrates on the reversal experts.

This is the cleanest current bottleneck: the classifier may detect continuation structure, but under prop-firm execution constraints those trades are not converting into positive challenge utility.

### 3. Edge is path-inefficient even when total return is positive

The latest model passes, but it still takes `76` active trading days and only has a `2 / 76` rolling-start pass rate (`2.6316%`).

This means the system has enough total expectancy to cross the line on one long realized path, but not enough path consistency to pass from many arbitrary starting points. For prop firms, that is a structural weakness because account lifecycle depends on short-horizon path shape, not only terminal expectancy.

### 4. Session and phase concentration remains narrow

Latest realized breakdown:

- market session:
  - `asia`: `40.0R`
  - `europe`: `0.333333R`
- session phase:
  - `build_20_40`: `25.666667R`
  - `opening_0_20`: `14.333333R`
  - `mid_40_60`: `-4.666667R`

The model is not broadly monetizing the session map. Most of the edge is concentrated in Asia and in the early session phases. This is acceptable if intentionally exploited, but then the manager should abstain more aggressively outside those slices.

### 5. Post-win behavior still looks weak

From the latest sequence diagnostics:

- after `win` streak `1`: next-trade expectancy `-0.064327R`
- after `win` streak `2`: next-trade expectancy `0.000000R`

By contrast, many post-loss states remain positive expectancy. This suggests the manager is too willing to keep firing immediately after wins, when the residual edge is weaker. That is a direct prop-firm path issue because clustered give-back slows time-to-pass.

## First-Principles Diagnosis

The limiting factor is no longer "train a stronger generic classifier."

The limiting factor is that the active execution policy is still closer to a probability maximizer than a prop-firm utility maximizer.

A prop-firm frontier model should optimize for:

- pass probability within bounded horizons
- time to pass
- profitable-day accumulation
- loss-cluster avoidance
- trade-slot allocation to the highest path-utility contexts

The latest repository artifacts already point in that direction: `manager_policy_frontier.json` moves to contextual abstention, context-specific thresholds, and path-aware utility ranking.

## What Should Change Next

### Highest-priority changes

1. Promote the frontier manager from research artifact to the main backtest policy.
2. Disable continuation experts by default until they are positive on realized challenge utility, not just classification lift.
3. Replace flat per-expert thresholds with context thresholds keyed by `market_session x session_phase x setup`.
4. Lower daily trade count from "fill all 6 slots" logic to "preserve only the best 3 to 5 opportunities."
5. Add explicit sequence-state gating so the manager cools down after single-win and two-win streaks where next-trade expectancy is weak.

### Data and model changes that are actually justified

1. Add regime features that separate trend persistence from chop persistence:
   - session range expansion state
   - opening drive strength
   - volatility regime percentile
   - intraday chop score
   - prior session imbalance
2. Retrain continuation experts only after relabeling or filtering them around regimes where continuation is genuinely executable under the prop envelope.
3. Rank models and policies by challenge utility metrics first:
   - rolling-start pass rate
   - `30/60/66/90` day pass probability
   - median days to pass
   - profitable-day rate
   - drawdown-cluster severity

## Bottom Line

The latest trained model is better than the documented previous models and it is the first one in this repo snapshot that clears the active FundedHive-style hurdle on the recorded path.

But the dominant bottleneck is now the manager layer, not the base TCN architecture. The path to materially higher prop-firm edge is to trade far less, abstain outside validated contexts, disable negative-expectancy continuation slices, and optimize directly for challenge pass probability and time-to-pass.
