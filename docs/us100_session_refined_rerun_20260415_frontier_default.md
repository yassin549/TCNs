# Current Baseline Report

Generated at `2026-04-16T11:31:53.654682+00:00` from `specialist_tcns/us100_session_refined_rerun_20260415_frontier_default`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_default`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_default\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_default\manager_policy.json`
- Dataset: `None`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_default\backtest_summary.json`

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

- Trades: `162`
- Active trading days: `68`
- First trade date: `2024-12-06`
- Last trade date: `2025-09-24`
- Calendar span covered by active trades: `293` days
- Win rate: `0.46914`
- Loss rate: `0.53086`
- Expectancy: `0.251029R` per trade
- Average R per trade: `0.251029R`
- Total R: `40.67R`
- Profit factor: `1.472868`
- Average win: `1.666667R`
- Average loss: `-1.000000R`
- Realized payoff ratio: `1.666667`
- Average hold time: `3.191358` bars
- Ending balance: `$114,170.87`
- Return: `14.1709%`
- Max drawdown: `3.3916%`
- Drawdown peak date: `2025-01-27`
- Drawdown trough date: `2025-03-03`
- Best trade: `2025-09-23` | `short_reversal` | `$842.87` | `1.67R` | `target`
- Worst trade: `2025-09-16` | `short_reversal` | `$-504.06` | `-1.00R` | `stop`

## Distribution

- Median trade: `-1.0`R
- Trade R std dev: `1.334917`
- Mean daily return: `0.197875`%
- Daily return std dev: `0.754034`%
- Daily Sharpe proxy: `0.2624`
- Daily Sortino proxy: `0.5639`

## Prop-Firm Metrics

- Policy: `FundedHive`
- Profit target: `10.00%`
- Minimum profitable days: `3`
- Max total drawdown: `10.00%`
- Max daily loss: `5.00%`
- Hard max loss per trade: `3.00%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `True`
- Days to pass on the recorded test path: `57` active trading days
- Profitable days on the recorded test path: `36`
- Historical rolling-start pass rate: `0.117647` (8/68)
- Fastest historical rolling-start pass: `56` active trading days
- Average historical rolling-start pass: `59.38` active trading days
- Median historical rolling-start pass: `59` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.221000`, average pass day `23.1`, median pass day `24`, min pass day `8`
  - `60`-day horizon: pass probability `0.715000`, average pass day `37.83`, median pass day `37`, min pass day `8`
  - `66`-day horizon: pass probability `0.781500`, average pass day `39.3`, median pass day `39`, min pass day `9`
  - `90`-day horizon: pass probability `0.913000`, average pass day `45.62`, median pass day `43`, min pass day `10`
  - `120`-day horizon: pass probability `0.971500`, average pass day `48.72`, median pass day `45`, min pass day `10`

## Daily Consistency

- Profitable days: `44`
- Losing days: `24`
- Positive day rate: `0.647059`
- Average daily return: `0.197875%`
- Median daily return: `0.296619%`
- Best day: `2025-09-23` | `$2,509.83` | `5.00R` | `2.2669%` | `3` trades
- Worst day: `2025-09-02` | `$-1,457.51` | `-3.00R` | `-1.3439%` | `3` trades

## Streaks

- Longest win streak: `5` trades
- Longest loss streak: `5` trades
- Longest positive-day streak: `5` days
- Longest negative-day streak: `3` days

## Start Timing

- After `flat_or_unknown` streak `0`: `1` starts, pass rate `1.000000`, average days to pass `57.0`, median days to pass `57.0`
- After `win` streak `2`: `10` starts, pass rate `0.200000`, average days to pass `59.5`, median days to pass `59.5`
- After `loss` streak `1`: `16` starts, pass rate `0.125000`, average days to pass `57.5`, median days to pass `57.5`
- After `loss` streak `2`: `8` starts, pass rate `0.125000`, average days to pass `61.0`, median days to pass `61.0`
- After `loss` streak `3`: `10` starts, pass rate `0.100000`, average days to pass `60.0`, median days to pass `60.0`
- After `win` streak `1`: `17` starts, pass rate `0.058824`, average days to pass `63.0`, median days to pass `63.0`
- After `win` streak `3`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `5`: `2` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `4`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `2.382353`
- Median trades per day: `2.000000`
- Days at max-trade cap: `32` / `68`
- Capacity utilization on active days: `79.4118%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`

## Breakdown By Setup

- `long_reversal`: trades `72`, win rate `0.527778`, expectancy `0.407407R`, total `29.333333R`, PnL `$10,163.65`
- `short_reversal`: trades `90`, win rate `0.422222`, expectancy `0.125926R`, total `11.333333R`, PnL `$4,341.80`

## Breakdown By Market Session

- `asia`: trades `160`, win rate `0.462500`, expectancy `0.233333R`, total `37.333333R`
- `europe`: trades `2`, win rate `1.000000`, expectancy `1.666667R`, total `3.333333R`

## Breakdown By Session Phase

- `opening_0_20`: trades `70`, win rate `0.514286`, expectancy `0.371429R`, total `26.000000R`
- `build_20_40`: trades `90`, win rate `0.422222`, expectancy `0.125926R`, total `11.333333R`
- `late_60_80`: trades `2`, win rate `1.000000`, expectancy `1.666667R`, total `3.333333R`

## Best Days

- `2025-09-23`: `$2,509.83` | `5.00R` | `2.2669%` | `3` trades
- `2025-09-08`: `$2,072.95` | `5.00R` | `1.9285%` | `3` trades
- `2024-12-17`: `$1,545.74` | `3.33R` | `1.5056%` | `2` trades
- `2025-09-15`: `$1,374.59` | `2.33R` | `1.2518%` | `3` trades
- `2025-04-02`: `$1,340.26` | `2.33R` | `1.2519%` | `3` trades
- `2025-03-07`: `$1,240.87` | `3.33R` | `1.1698%` | `2` trades
- `2025-09-19`: `$1,148.68` | `2.33R` | `1.0489%` | `3` trades
- `2025-01-03`: `$1,092.20` | `2.33R` | `1.0489%` | `3` trades
- `2024-12-13`: `$1,068.64` | `2.33R` | `1.0488%` | `3` trades
- `2025-09-09`: `$1,004.55` | `2.33R` | `0.9169%` | `3` trades

## Worst Days

- `2025-09-02`: `$-1,457.51` | `-3.00R` | `-1.3439%` | `3` trades
- `2025-03-27`: `$-1,229.58` | `-3.00R` | `-1.1457%` | `3` trades
- `2024-12-18`: `$-1,193.95` | `-3.00R` | `-1.1457%` | `3` trades
- `2025-09-17`: `$-1,001.33` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-09-11`: `$-999.95` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-09-18`: `$-992.34` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-01-29`: `$-965.22` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-01-17`: `$-962.16` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-02-13`: `$-954.77` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-02-10`: `$-750.44` | `-2.00R` | `-0.6989%` | `2` trades

## Sequence Diagnostics


### After Loss Streaks

- Prior `loss` streak `1`: `43` samples, next-trade win probability `0.488372`, next-trade expectancy `0.302326R`, `next_5_trade_avg_r` `0.277519R`
- Prior `loss` streak `2`: `22` samples, next-trade win probability `0.454545`, next-trade expectancy `0.212121R`, `next_5_trade_avg_r` `0.212121R`
- Prior `loss` streak `3`: `12` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.244444R`
- Prior `loss` streak `4`: `6` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.422222R`
- Prior `loss` streak `5`: `3` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.777778R`

### After Win Streaks

- Prior `win` streak `1`: `44` samples, next-trade win probability `0.431818`, next-trade expectancy `0.151515R`, `next_5_trade_avg_r` `0.236364R`
- Prior `win` streak `2`: `19` samples, next-trade win probability `0.473684`, next-trade expectancy `0.263158R`, `next_5_trade_avg_r` `0.178947R`
- Prior `win` streak `3`: `9` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.185185R`
- Prior `win` streak `4`: `3` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.422222R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
