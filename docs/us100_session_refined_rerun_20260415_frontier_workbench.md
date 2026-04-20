# Current Baseline Report

Generated at `2026-04-18T12:42:56.290116+00:00` from `specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\manager_policy.json`
- Dataset: `None`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\backtest_summary.json`
- Execution mode: `frontier_managed`
- Policy selection: `frontier_contextual_abstention_manager`
- Raw source summary: `{'trades': 418, 'trading_days': 70, 'win_rate': 0.404306, 'expectancy_r': 0.07815, 'total_r': 32.666667, 'profit_factor': 1.131191, 'average_hold_bars': 3.22488, 'ending_balance': 108266.36, 'total_return_pct': 8.2664, 'max_drawdown_pct': 4.7929, 'reached_profit_target': True, 'days_to_target': 70, 'breached_total_drawdown': False, 'skip_counts': {'cooldown': 3014, 'ineligible': 12920, 'session_end_buffer': 2139, 'daily_lock': 0, 'daily_trade_cap': 58072, 'daily_risk_budget': 0, 'total_drawdown_budget': 0}}`

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

- Trades: `180`
- Active trading days: `68`
- First trade date: `2024-12-06`
- Last trade date: `2025-09-15`
- Calendar span covered by active trades: `284` days
- Win rate: `0.50556`
- Loss rate: `0.49444`
- Expectancy: `0.348148R` per trade
- Average R per trade: `0.348148R`
- Total R: `62.67R`
- Profit factor: `1.704120`
- Average win: `1.666667R`
- Average loss: `-1.000000R`
- Realized payoff ratio: `1.666667`
- Average hold time: `3.333333` bars
- Ending balance: `$123,825.42`
- Return: `23.8254%`
- Max drawdown: `2.2716%`
- Drawdown peak date: `2025-01-24`
- Drawdown trough date: `2025-02-03`
- Best trade: `2025-09-11` | `short_continuation` | `$917.23` | `1.67R` | `target`
- Worst trade: `2025-08-21` | `long_reversal` | `$-547.89` | `-1.00R` | `stop`

## Distribution

- Median trade: `1.666667`R
- Trade R std dev: `1.33697`
- Mean daily return: `0.317473`%
- Daily return std dev: `0.742524`%
- Daily Sharpe proxy: `0.4276`
- Daily Sortino proxy: `0.9251`

## Acceptance Metrics

- Pass probability 30 / 60 / 90: `0.552` / `0.968` / `1.0`
- Median / avg days to pass: `31.0` / `30.190476`
- Profitable-day hit rate day 10 / 20: `0.955882` / `0.955882`
- Longest trade loss streak: `6`
- Longest negative day streak: `6`
- Worst month return %: `-0.154066`
- Loss cluster penalty: `0.782025`

## Prop-Firm Metrics

- Policy: `FundedHive`
- Profit target: `10.00%`
- Minimum profitable days: `3`
- Max total drawdown: `10.00%`
- Max daily loss: `5.00%`
- Hard max loss per trade: `3.00%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `True`
- Days to pass on the recorded test path: `24` active trading days
- Profitable days on the recorded test path: `16`
- Historical rolling-start pass rate: `0.617647` (42/68)
- Fastest historical rolling-start pass: `23` active trading days
- Average historical rolling-start pass: `30.05` active trading days
- Median historical rolling-start pass: `31` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.514500`, average pass day `22.59`, median pass day `23`, min pass day `9`
  - `60`-day horizon: pass probability `0.962500`, average pass day `30.28`, median pass day `28`, min pass day `9`
  - `66`-day horizon: pass probability `0.982500`, average pass day `30.86`, median pass day `29`, min pass day `9`
  - `90`-day horizon: pass probability `0.998500`, average pass day `31.74`, median pass day `29`, min pass day `10`
  - `120`-day horizon: pass probability `1.000000`, average pass day `31.44`, median pass day `29`, min pass day `9`

## Daily Consistency

- Profitable days: `42`
- Losing days: `26`
- Positive day rate: `0.617647`
- Average daily return: `0.317473%`
- Median daily return: `0.582973%`
- Best day: `2025-02-21` | `$2,540.44` | `5.00R` | `2.2669%` | `3` trades
- Worst day: `2025-09-02` | `$-1,633.75` | `-3.00R` | `-1.3439%` | `3` trades

## Streaks

- Longest win streak: `5` trades
- Longest loss streak: `6` trades
- Longest positive-day streak: `7` days
- Longest negative-day streak: `6` days

## Start Timing

- After `loss` streak `4`: `2` starts, pass rate `1.000000`, average days to pass `26.0`, median days to pass `26.0`
- After `flat_or_unknown` streak `0`: `1` starts, pass rate `1.000000`, average days to pass `24.0`, median days to pass `24.0`
- After `loss` streak `6`: `1` starts, pass rate `1.000000`, average days to pass `23.0`, median days to pass `23.0`
- After `win` streak `2`: `11` starts, pass rate `0.818182`, average days to pass `31.7777777778`, median days to pass `33.0`
- After `loss` streak `2`: `5` starts, pass rate `0.800000`, average days to pass `30.0`, median days to pass `29.5`
- After `loss` streak `1`: `18` starts, pass rate `0.722222`, average days to pass `30.9230769231`, median days to pass `32.0`
- After `win` streak `1`: `16` starts, pass rate `0.625000`, average days to pass `30.0`, median days to pass `30.5`
- After `loss` streak `3`: `8` starts, pass rate `0.250000`, average days to pass `27.5`, median days to pass `27.5`
- After `win` streak `3`: `5` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `5`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `2.647059`
- Median trades per day: `3.000000`
- Days at max-trade cap: `48` / `68`
- Capacity utilization on active days: `88.2353%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`, `allocator_low_utility=0`

## Breakdown By Setup

- `short_reversal`: trades `54`, win rate `0.537037`, expectancy `0.432099R`, total `23.333333R`, PnL `$6,528.53`
- `long_reversal`: trades `59`, win rate `0.508475`, expectancy `0.355932R`, total `21.000000R`, PnL `$7,945.50`
- `short_continuation`: trades `35`, win rate `0.514286`, expectancy `0.371429R`, total `13.000000R`, PnL `$7,748.84`
- `long_continuation`: trades `32`, win rate `0.437500`, expectancy `0.166667R`, total `5.333333R`, PnL `$2,101.93`

## Breakdown By Market Session

- `asia`: trades `169`, win rate `0.502959`, expectancy `0.341223R`, total `57.666667R`
- `europe`: trades `11`, win rate `0.545455`, expectancy `0.454545R`, total `5.000000R`

## Breakdown By Session Phase

- `build_20_40`: trades `77`, win rate `0.532468`, expectancy `0.419913R`, total `32.333333R`
- `opening_0_20`: trades `92`, win rate `0.478261`, expectancy `0.275362R`, total `25.333333R`
- `mid_40_60`: trades `11`, win rate `0.545455`, expectancy `0.454545R`, total `5.000000R`

## Best Days

- `2025-02-21`: `$2,540.44` | `5.00R` | `2.2669%` | `3` trades
- `2025-09-15`: `$1,534.99` | `5.00R` | `1.2552%` | `3` trades
- `2025-04-02`: `$1,505.34` | `2.33R` | `1.2519%` | `3` trades
- `2025-03-04`: `$1,444.40` | `5.00R` | `1.2552%` | `3` trades
- `2025-02-28`: `$1,429.88` | `2.33R` | `1.2519%` | `3` trades
- `2025-02-25`: `$1,427.82` | `5.00R` | `1.2552%` | `3` trades
- `2025-02-19`: `$1,313.45` | `3.33R` | `1.1698%` | `2` trades
- `2025-02-07`: `$1,291.28` | `3.33R` | `1.1698%` | `2` trades
- `2025-01-23`: `$1,143.03` | `2.33R` | `1.0489%` | `3` trades
- `2025-02-05`: `$1,139.11` | `2.33R` | `1.0488%` | `3` trades

## Worst Days

- `2025-09-02`: `$-1,633.75` | `-3.00R` | `-1.3439%` | `3` trades
- `2025-02-20`: `$-1,526.62` | `-3.00R` | `-1.3439%` | `3` trades
- `2025-09-04`: `$-1,146.32` | `-3.00R` | `-0.9471%` | `3` trades
- `2025-02-26`: `$-861.67` | `-3.00R` | `-0.7481%` | `3` trades
- `2025-02-24`: `$-857.41` | `-3.00R` | `-0.7481%` | `3` trades
- `2025-01-31`: `$-764.29` | `-2.00R` | `-0.6989%` | `2` trades
- `2025-02-03`: `$-758.94` | `-2.00R` | `-0.6989%` | `2` trades
- `2025-09-12`: `$-613.75` | `-2.00R` | `-0.4994%` | `2` trades
- `2025-09-05`: `$-598.67` | `-2.00R` | `-0.4994%` | `2` trades
- `2025-03-03`: `$-577.52` | `-2.00R` | `-0.4994%` | `2` trades

## Sequence Diagnostics


### After Loss Streaks

- Prior `loss` streak `1`: `48` samples, next-trade win probability `0.541667`, next-trade expectancy `0.444444R`, `next_5_trade_avg_r` `0.377778R`
- Prior `loss` streak `2`: `22` samples, next-trade win probability `0.454545`, next-trade expectancy `0.212121R`, `next_5_trade_avg_r` `0.303030R`
- Prior `loss` streak `3`: `12` samples, next-trade win probability `0.750000`, next-trade expectancy `1.000000R`, `next_5_trade_avg_r` `0.555556R`
- Prior `loss` streak `4`: `3` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.422222R`
- Prior `loss` streak `5`: `2` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `0.333333R`
- Prior `loss` streak `6`: `2` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.866667R`

### After Win Streaks

- Prior `win` streak `1`: `49` samples, next-trade win probability `0.551020`, next-trade expectancy `0.469388R`, `next_5_trade_avg_r` `0.349660R`
- Prior `win` streak `2`: `27` samples, next-trade win probability `0.370370`, next-trade expectancy `-0.012346R`, `next_5_trade_avg_r` `0.362963R`
- Prior `win` streak `3`: `9` samples, next-trade win probability `0.444444`, next-trade expectancy `0.185185R`, `next_5_trade_avg_r` `0.185185R`
- Prior `win` streak `4`: `4` samples, next-trade win probability `0.250000`, next-trade expectancy `-0.333333R`, `next_5_trade_avg_r` `0.066667R`
- Prior `win` streak `5`: `1` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `0.600000R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
