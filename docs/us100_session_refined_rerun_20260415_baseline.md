# Current Baseline Report

Generated at `2026-04-16T01:36:55.668217+00:00` from `specialist_tcns/us100_session_refined_rerun_20260415`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415\manager_policy.json`
- Dataset: `C:\Users\khoua\OneDrive\Desktop\TCNs\data\features\us100_specialist_tcn_dataset_session_refined_rerun_20260415.csv.gz`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415\backtest_summary.json`

## Training Snapshot

- Lookback: `96` bars
- Feature count: `55`
- Train / val split: `70%` / `15%`
- Epochs: `8`
- Batch size: `256`
- Negative ratio: `4.0`
- Channels: `48, 48, 64`
- Hidden dim: `64`
- Dropout: `0.1`

## Evaluation Scope

- Rows analyzed: `1,663,410`
- Eligible test rows: `215,050`
- Feature columns reported by analysis: `55`

## Backtest Summary

- Trades: `453`
- Active trading days: `76`
- First trade date: `2024-12-06`
- Last trade date: `2025-09-24`
- Calendar span covered by active trades: `293` days
- Win rate: `0.40839`
- Loss rate: `0.59161`
- Expectancy: `0.089036R` per trade
- Average R per trade: `0.089036R`
- Total R: `40.33R`
- Profit factor: `1.150498`
- Average win: `1.666667R`
- Average loss: `-1.000000R`
- Realized payoff ratio: `1.666667`
- Average hold time: `3.196468` bars
- Ending balance: `$110,339.63`
- Return: `10.3396%`
- Max drawdown: `4.7929%`
- Drawdown peak date: `2025-01-27`
- Drawdown trough date: `2025-03-03`
- Best trade: `2025-09-24` | `short_reversal` | `$457.84` | `1.67R` | `target`
- Worst trade: `2025-09-22` | `short_continuation` | `$-274.49` | `-1.00R` | `stop`

## Distribution

- Median trade: `-1.0`R
- Trade R std dev: `1.312211`
- Mean daily return: `0.133268`%
- Daily return std dev: `0.869368`%
- Daily Sharpe proxy: `0.1533`
- Daily Sortino proxy: `0.2837`

## Prop-Firm Metrics

- Policy: `legacy_prop_policy`
- Profit target: `10.00%`
- Minimum profitable days: `0`
- Max total drawdown: `10.00%`
- Max daily loss: `5.00%`
- Hard max loss per trade: `0.25%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `True`
- Days to pass on the recorded test path: `76` active trading days
- Profitable days on the recorded test path: `35`
- Historical rolling-start pass rate: `0.026316` (2/76)
- Fastest historical rolling-start pass: `75` active trading days
- Average historical rolling-start pass: `75.5` active trading days
- Median historical rolling-start pass: `75` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.157500`, average pass day `22.84`, median pass day `24`, min pass day `9`
  - `60`-day horizon: pass probability `0.479000`, average pass day `38.25`, median pass day `39`, min pass day `10`
  - `66`-day horizon: pass probability `0.552500`, average pass day `41.17`, median pass day `41`, min pass day `9`
  - `90`-day horizon: pass probability `0.698000`, average pass day `49.12`, median pass day `48`, min pass day `9`
  - `120`-day horizon: pass probability `0.838000`, average pass day `56.71`, median pass day `53`, min pass day `9`

## Daily Consistency

- Profitable days: `35`
- Losing days: `41`
- Positive day rate: `0.460526`
- Average daily return: `0.133268%`
- Median daily return: `-0.169501%`
- Best day: `2025-03-04` | `$2,543.26` | `10.00R` | `2.5262%` | `6` trades
- Worst day: `2025-09-12` | `$-1,592.66` | `-6.00R` | `-1.4907%` | `6` trades

## Streaks

- Longest win streak: `8` trades
- Longest loss streak: `9` trades
- Longest positive-day streak: `3` days
- Longest negative-day streak: `4` days

## Start Timing

- After `flat_or_unknown` streak `0`: `1` starts, pass rate `1.000000`, average days to pass `76.0`, median days to pass `76.0`
- After `loss` streak `1`: `11` starts, pass rate `0.090909`, average days to pass `75.0`, median days to pass `75.0`
- After `win` streak `1`: `23` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `2`: `11` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `3`: `9` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `2`: `7` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `4`: `4` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `6`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `5`: `2` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `4`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `5.960526`
- Median trades per day: `6.000000`
- Days at max-trade cap: `75` / `76`
- Capacity utilization on active days: `99.3421%`
- Skip counts: `cooldown=3254`, `ineligible=14030`, `session_end_buffer=2325`, `daily_trade_cap=63649`

## Breakdown By Setup

- `short_reversal`: trades `152`, win rate `0.434211`, expectancy `0.157895R`, total `24.000000R`, PnL `$6,164.72`
- `long_reversal`: trades `100`, win rate `0.450000`, expectancy `0.200000R`, total `20.000000R`, PnL `$5,214.87`
- `long_continuation`: trades `119`, win rate `0.369748`, expectancy `-0.014006R`, total `-1.666667R`, PnL `$-446.56`
- `short_continuation`: trades `82`, win rate `0.365854`, expectancy `-0.024390R`, total `-2.000000R`, PnL `$-593.39`

## Breakdown By Market Session

- `asia`: trades `408`, win rate `0.411765`, expectancy `0.098039R`, total `40.000000R`
- `europe`: trades `45`, win rate `0.377778`, expectancy `0.007407R`, total `0.333333R`

## Breakdown By Session Phase

- `build_20_40`: trades `201`, win rate `0.422886`, expectancy `0.127695R`, total `25.666667R`
- `opening_0_20`: trades `207`, win rate `0.400966`, expectancy `0.069243R`, total `14.333333R`
- `late_60_80`: trades `3`, win rate `1.000000`, expectancy `1.666667R`, total `5.000000R`
- `mid_40_60`: trades `42`, win rate `0.333333`, expectancy `-0.111111R`, total `-4.666667R`

## Best Days

- `2025-03-04`: `$2,543.26` | `10.00R` | `2.5262%` | `6` trades
- `2025-09-16`: `$1,965.12` | `7.33R` | `1.8455%` | `6` trades
- `2025-02-25`: `$1,861.39` | `7.33R` | `1.8455%` | `6` trades
- `2024-12-09`: `$1,842.39` | `7.33R` | `1.8455%` | `6` trades
- `2025-09-24`: `$1,367.83` | `5.00R` | `1.2552%` | `3` trades
- `2025-09-09`: `$1,230.90` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-15`: `$1,230.75` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-03`: `$1,222.88` | `4.67R` | `1.1694%` | `6` trades
- `2025-03-07`: `$1,219.05` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-08`: `$1,216.66` | `4.67R` | `1.1694%` | `6` trades

## Worst Days

- `2025-09-12`: `$-1,592.66` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-01-31`: `$-1,555.17` | `-6.00R` | `-1.4907%` | `6` trades
- `2024-12-18`: `$-1,551.05` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-02-20`: `$-1,531.39` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-02-24`: `$-1,526.21` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-09-22`: `$-910.03` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-04`: `$-880.57` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-03-27`: `$-877.79` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-02`: `$-877.69` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-05`: `$-873.23` | `-3.33R` | `-0.8323%` | `6` trades

## Sequence Diagnostics


### After Loss Streaks

- Prior `loss` streak `1`: `114` samples, next-trade win probability `0.447368`, next-trade expectancy `0.192982R`, `next_5_trade_avg_r` `0.029240R`
- Prior `loss` streak `2`: `63` samples, next-trade win probability `0.380952`, next-trade expectancy `0.015873R`, `next_5_trade_avg_r` `0.047619R`
- Prior `loss` streak `3`: `39` samples, next-trade win probability `0.435897`, next-trade expectancy `0.162393R`, `next_5_trade_avg_r` `0.176068R`
- Prior `loss` streak `4`: `22` samples, next-trade win probability `0.409091`, next-trade expectancy `0.090909R`, `next_5_trade_avg_r` `0.236364R`
- Prior `loss` streak `5`: `13` samples, next-trade win probability `0.538462`, next-trade expectancy `0.435897R`, `next_5_trade_avg_r` `0.271795R`
- Prior `loss` streak `6`: `6` samples, next-trade win probability `0.166667`, next-trade expectancy `-0.555556R`, `next_5_trade_avg_r` `0.333333R`
- Prior `loss` streak `7`: `5` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `0.493333R`
- Prior `loss` streak `8`: `5` samples, next-trade win probability `0.800000`, next-trade expectancy `1.133333R`, `next_5_trade_avg_r` `0.813333R`
- Prior `loss` streak `9`: `1` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `1.666667R`

### After Win Streaks

- Prior `win` streak `1`: `114` samples, next-trade win probability `0.350877`, next-trade expectancy `-0.064327R`, `next_5_trade_avg_r` `-0.003509R`
- Prior `win` streak `2`: `40` samples, next-trade win probability `0.375000`, next-trade expectancy `0.000000R`, `next_5_trade_avg_r` `0.173333R`
- Prior `win` streak `3`: `14` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.333333R`
- Prior `win` streak `4`: `7` samples, next-trade win probability `0.571429`, next-trade expectancy `0.523810R`, `next_5_trade_avg_r` `0.142857R`
- Prior `win` streak `5`: `4` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.066667R`
- Prior `win` streak `6`: `2` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.333333R`
- Prior `win` streak `7`: `2` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `-0.200000R`
- Prior `win` streak `8`: `1` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `-0.466667R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
