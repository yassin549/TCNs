# Current Baseline Report

Generated at `2026-04-20T06:28:10.960507+00:00` from `frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k\manager_policy.json`
- Dataset: `artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k\utility_dataset.csv.gz`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\us100_session_refined_rerun_20260415_regime_workbench_300k\backtest_summary.json`
- Execution mode: `frontier_managed`
- Policy selection: `frontier_daily_allocator`
- Raw source summary: `None`

## Training Snapshot

- Lookback: `96` bars
- Feature count: `70`
- Train / val split: `70%` / `15%`
- Epochs: `4`
- Batch size: `64`
- Negative ratio: `0.0`
- Channels: `32, 32, 48`
- Hidden dim: `64`
- Dropout: `0.15`

## Backtest Summary

- Trades: `100`
- Active trading days: `34`
- First trade date: `2020-10-23`
- Last trade date: `2020-12-11`
- Calendar span covered by active trades: `50` days
- Win rate: `0.26000`
- Loss rate: `0.00000`
- Expectancy: `0.369627R` per trade
- Average R per trade: `0.369627R`
- Total R: `36.96R`
- Profit factor: `0.000000`
- Average win: `1.421644R`
- Average loss: `n/a`
- Realized payoff ratio: `n/a`
- Average hold time: `1.000000` bars
- Ending balance: `$109,662.94`
- Return: `9.6629%`
- Max drawdown: `0.7993%`
- Drawdown peak date: `None`
- Drawdown trough date: `None`
- Best trade: `2020-11-09` | `long_reversal` | `$416.74` | `1.62R` | `utility_label`
- Worst trade: `2020-10-23` | `long_reversal` | `$0.00` | `0.00R` | `utility_label`

## Distribution

- Median trade: `0.0`R
- Trade R std dev: `0.631345`
- Mean daily return: `0.272057`%
- Daily return std dev: `0.284527`%
- Daily Sharpe proxy: `0.9562`
- Daily Sortino proxy: `None`

## Acceptance Metrics

- Pass probability 30 / 60 / 90: `0.158` / `1.0` / `1.0`
- Median / avg days to pass: `None` / `None`
- Profitable-day hit rate day 10 / 20: `0.911765` / `0.911765`
- Longest trade loss streak: `0`
- Longest negative day streak: `0`
- Worst month return %: `1.859173`
- Loss cluster penalty: `0.0`

## Prop-Firm Metrics

- Policy: `FundedHive`
- Profit target: `10.00%`
- Minimum profitable days: `3`
- Max total drawdown: `10.00%`
- Max daily loss: `5.00%`
- Hard max loss per trade: `3.00%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `False`
- Days to pass on the recorded test path: `None` active trading days
- Profitable days on the recorded test path: `20`
- Historical rolling-start pass rate: `0.000000` (0/34)
- Fastest historical rolling-start pass: `None` active trading days
- Average historical rolling-start pass: `None` active trading days
- Median historical rolling-start pass: `None` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.177500`, average pass day `27.52`, median pass day `28`, min pass day `17`
  - `60`-day horizon: pass probability `0.999500`, average pass day `36.12`, median pass day `36`, min pass day `20`
  - `66`-day horizon: pass probability `1.000000`, average pass day `35.92`, median pass day `36`, min pass day `18`
  - `90`-day horizon: pass probability `1.000000`, average pass day `36.21`, median pass day `36`, min pass day `17`
  - `120`-day horizon: pass probability `1.000000`, average pass day `36.07`, median pass day `36`, min pass day `18`

## Daily Consistency

- Profitable days: `21`
- Losing days: `0`
- Positive day rate: `0.617647`
- Average daily return: `0.272057%`
- Median daily return: `0.341835%`
- Best day: `2020-11-09` | `$826.29` | `3.22R` | `-0.3978%` | `3` trades
- Worst day: `2020-10-26` | `$0.00` | `0.00R` | `0.0000%` | `3` trades

## Streaks

- Longest win streak: `2` trades
- Longest loss streak: `0` trades
- Longest positive-day streak: `5` days
- Longest negative-day streak: `0` days

## Start Timing

- After `flat_or_unknown` streak `0`: `26` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `1`: `5` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `2`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `2.941176`
- Median trades per day: `3.000000`
- Days at max-trade cap: `33` / `34`
- Capacity utilization on active days: `98.0392%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`, `allocator_low_utility=34870`

## Breakdown By Setup

- `short_continuation`: trades `43`, win rate `0.325581`, expectancy `0.461176R`, total `19.830585R`, PnL `$5,131.34`
- `long_reversal`: trades `43`, win rate `0.232558`, expectancy `0.332742R`, total `14.307918R`, PnL `$3,800.45`
- `long_continuation`: trades `8`, win rate `0.250000`, expectancy `0.353031R`, total `2.824245R`, PnL `$731.16`
- `short_reversal`: trades `6`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`, PnL `$0.00`

## Breakdown By Market Session

- `europe`: trades `32`, win rate `0.375000`, expectancy `0.524456R`, total `16.782608R`
- `us`: trades `48`, win rate `0.229167`, expectancy `0.340705R`, total `16.353852R`
- `asia`: trades `20`, win rate `0.150000`, expectancy `0.191314R`, total `3.826288R`

## Breakdown By Session Phase

- `late_60_80`: trades `43`, win rate `0.348837`, expectancy `0.519283R`, total `22.329161R`
- `mid_40_60`: trades `20`, win rate `0.350000`, expectancy `0.468147R`, total `9.362946R`
- `opening_0_20`: trades `8`, win rate `0.250000`, expectancy `0.341925R`, total `2.735398R`
- `close_80_100`: trades `16`, win rate `0.062500`, expectancy `0.090272R`, total `1.444353R`
- `build_20_40`: trades `13`, win rate `0.076923`, expectancy `0.083915R`, total `1.090890R`

## Best Days

- `2020-11-09`: `$826.29` | `3.22R` | `-0.3978%` | `3` trades
- `2020-11-30`: `$814.30` | `3.06R` | `0.3844%` | `3` trades
- `2020-11-10`: `$801.99` | `3.10R` | `0.0000%` | `3` trades
- `2020-10-23`: `$753.37` | `3.01R` | `0.3731%` | `3` trades
- `2020-12-07`: `$640.10` | `2.37R` | `0.0000%` | `3` trades
- `2020-11-16`: `$405.41` | `1.55R` | `0.3880%` | `3` trades
- `2020-10-30`: `$398.38` | `1.57R` | `0.3926%` | `3` trades
- `2020-11-04`: `$396.07` | `1.55R` | `0.0000%` | `3` trades
- `2020-12-08`: `$393.00` | `1.45R` | `0.0000%` | `3` trades
- `2020-11-23`: `$392.58` | `1.48R` | `0.0000%` | `3` trades

## Worst Days

- `2020-11-11`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-11-12`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-11-25`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-12-09`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-11-20`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-11-05`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-12-04`: `$0.00` | `0.00R` | `0.0000%` | `1` trades
- `2020-11-06`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-11-02`: `$0.00` | `0.00R` | `0.0000%` | `3` trades
- `2020-12-01`: `$0.00` | `0.00R` | `0.0000%` | `3` trades

## Sequence Diagnostics


### After Loss Streaks


### After Win Streaks

- Prior `win` streak `1`: `20` samples, next-trade win probability `0.250000`, next-trade expectancy `0.363772R`, `next_5_trade_avg_r` `0.319492R`
- Prior `win` streak `2`: `5` samples, next-trade win probability `0.000000`, next-trade expectancy `0.000000R`, `next_5_trade_avg_r` `0.229386R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
