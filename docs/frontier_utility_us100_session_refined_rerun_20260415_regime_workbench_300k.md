# Current Baseline Report

Generated at `2026-04-20T15:49:58.639484+00:00` from `frontier_utility/us100_session_refined_rerun_20260415_regime_workbench_300k`.

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
- Feature count: `74`
- Train / val split: `70%` / `15%`
- Epochs: `6`
- Batch size: `256`
- Negative ratio: `0.0`
- Channels: `64, 64, 96`
- Hidden dim: `128`
- Dropout: `0.15`

## Backtest Summary

- Trades: `66`
- Active trading days: `33`
- First trade date: `2020-10-23`
- Last trade date: `2020-12-11`
- Calendar span covered by active trades: `50` days
- Win rate: `0.31818`
- Loss rate: `0.00000`
- Expectancy: `0.463918R` per trade
- Average R per trade: `0.463918R`
- Total R: `30.62R`
- Profit factor: `0.000000`
- Average win: `1.458030R`
- Average loss: `n/a`
- Realized payoff ratio: `n/a`
- Average hold time: `1.000000` bars
- Ending balance: `$117,015.03`
- Return: `17.0150%`
- Max drawdown: `1.1942%`
- Drawdown peak date: `None`
- Drawdown trough date: `None`
- Best trade: `2020-11-06` | `long_reversal` | `$1,272.76` | `1.50R` | `utility_label`
- Worst trade: `2020-10-23` | `long_reversal` | `$0.00` | `0.00R` | `utility_label`

## Distribution

- Median trade: `0.0`R
- Trade R std dev: `0.686175`
- Mean daily return: `0.478743`%
- Daily return std dev: `0.549009`%
- Daily Sharpe proxy: `0.872`
- Daily Sortino proxy: `None`

## Acceptance Metrics

- Pass probability 30 / 60 / 90: `0.938` / `1.0` / `1.0`
- Median / avg days to pass: `11.0` / `15.888889`
- Profitable-day hit rate day 10 / 20: `0.848485` / `0.909091`
- Longest trade loss streak: `0`
- Longest negative day streak: `0`
- Worst month return %: `2.670171`
- Loss cluster penalty: `0.0`

## Prop-Firm Metrics

- Policy: `FundedHive`
- Profit target: `10.00%`
- Minimum profitable days: `3`
- Max total drawdown: `10.00%`
- Max daily loss: `5.00%`
- Hard max loss per trade: `3.00%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `True`
- Days to pass on the recorded test path: `12` active trading days
- Profitable days on the recorded test path: `8`
- Historical rolling-start pass rate: `0.272727` (9/33)
- Fastest historical rolling-start pass: `10` active trading days
- Average historical rolling-start pass: `15.44` active trading days
- Median historical rolling-start pass: `12` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.955000`, average pass day `20.52`, median pass day `20`, min pass day `8`
  - `60`-day horizon: pass probability `1.000000`, average pass day `21.18`, median pass day `21`, min pass day `8`
  - `66`-day horizon: pass probability `1.000000`, average pass day `21.13`, median pass day `21`, min pass day `9`
  - `90`-day horizon: pass probability `1.000000`, average pass day `21.27`, median pass day `21`, min pass day `9`
  - `120`-day horizon: pass probability `1.000000`, average pass day `21.29`, median pass day `21`, min pass day `8`

## Daily Consistency

- Profitable days: `17`
- Losing days: `0`
- Positive day rate: `0.515152`
- Average daily return: `0.478743%`
- Median daily return: `0.449484%`
- Best day: `2020-11-06` | `$2,525.32` | `2.98R` | `0.0000%` | `2` trades
- Worst day: `2020-10-23` | `$0.00` | `0.00R` | `0.0000%` | `2` trades

## Streaks

- Longest win streak: `3` trades
- Longest loss streak: `0` trades
- Longest positive-day streak: `6` days
- Longest negative-day streak: `0` days

## Start Timing

- After `win` streak `2`: `3` starts, pass rate `0.333333`, average days to pass `15.0`, median days to pass `15.0`
- After `flat_or_unknown` streak `0`: `23` starts, pass rate `0.304348`, average days to pass `14.1428571429`, median days to pass `12.0`
- After `win` streak `1`: `7` starts, pass rate `0.142857`, average days to pass `25.0`, median days to pass `25.0`

## Operating Profile

- Average trades per day: `2.000000`
- Median trades per day: `2.000000`
- Days at max-trade cap: `33` / `33`
- Capacity utilization on active days: `100.0000%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`, `allocator_low_utility=26131`

## Breakdown By Setup

- `long_reversal`: trades `32`, win rate `0.343750`, expectancy `0.509416R`, total `16.301312R`, PnL `$9,195.95`
- `short_continuation`: trades `29`, win rate `0.310345`, expectancy `0.441510R`, total `12.803797R`, PnL `$6,740.93`
- `long_continuation`: trades `3`, win rate `0.333333`, expectancy `0.504504R`, total `1.513511R`, PnL `$1,078.16`
- `short_reversal`: trades `2`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`, PnL `$0.00`

## Breakdown By Market Session

- `europe`: trades `22`, win rate `0.409091`, expectancy `0.593020R`, total `13.046444R`
- `us`: trades `36`, win rate `0.222222`, expectancy `0.328778R`, total `11.835993R`
- `asia`: trades `8`, win rate `0.500000`, expectancy `0.717023R`, total `5.736183R`

## Breakdown By Session Phase

- `late_60_80`: trades `31`, win rate `0.322581`, expectancy `0.481134R`, total `14.915158R`
- `mid_40_60`: trades `15`, win rate `0.400000`, expectancy `0.569003R`, total `8.535051R`
- `build_20_40`: trades `6`, win rate `0.333333`, expectancy `0.496686R`, total `2.980118R`
- `opening_0_20`: trades `4`, win rate `0.500000`, expectancy `0.689016R`, total `2.756065R`
- `close_80_100`: trades `10`, win rate `0.100000`, expectancy `0.143223R`, total `1.432228R`

## Best Days

- `2020-11-06`: `$2,525.32` | `2.98R` | `0.0000%` | `2` trades
- `2020-10-29`: `$2,290.29` | `2.90R` | `0.0000%` | `2` trades
- `2020-11-30`: `$1,286.85` | `3.08R` | `0.0000%` | `2` trades
- `2020-10-30`: `$1,249.16` | `1.57R` | `0.0000%` | `2` trades
- `2020-11-04`: `$1,183.79` | `1.59R` | `0.0000%` | `2` trades
- `2020-12-11`: `$1,095.04` | `2.80R` | `0.9447%` | `2` trades
- `2020-11-05`: `$1,083.33` | `1.44R` | `0.0000%` | `2` trades
- `2020-11-03`: `$1,078.16` | `1.51R` | `1.0307%` | `2` trades
- `2020-10-26`: `$1,060.74` | `1.35R` | `1.0607%` | `2` trades
- `2020-11-09`: `$562.00` | `1.61R` | `0.0000%` | `2` trades

## Worst Days

- `2020-10-23`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-12-09`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-12-02`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-12-01`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-11-25`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-11-24`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-11-23`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-11-20`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-11-18`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-11-13`: `$0.00` | `0.00R` | `0.0000%` | `2` trades

## Sequence Diagnostics


### After Loss Streaks


### After Win Streaks

- Prior `win` streak `1`: `13` samples, next-trade win probability `0.384615`, next-trade expectancy `0.561123R`, `next_5_trade_avg_r` `0.538129R`
- Prior `win` streak `2`: `5` samples, next-trade win probability `0.600000`, next-trade expectancy `0.915936R`, `next_5_trade_avg_r` `0.708159R`
- Prior `win` streak `3`: `2` samples, next-trade win probability `0.000000`, next-trade expectancy `0.000000R`, `next_5_trade_avg_r` `0.304689R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
