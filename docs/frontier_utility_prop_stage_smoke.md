# Current Baseline Report

Generated at `2026-04-20T12:08:41.501826+00:00` from `frontier_utility/prop_stage_smoke`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\prop_stage_smoke`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\prop_stage_smoke\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\prop_stage_smoke\manager_policy.json`
- Dataset: `artifacts\frontier_utility\prop_stage_smoke\utility_dataset.csv.gz`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\prop_stage_smoke\backtest_summary.json`
- Execution mode: `frontier_managed`
- Policy selection: `frontier_daily_allocator`
- Raw source summary: `None`

## Training Snapshot

- Lookback: `96` bars
- Feature count: `74`
- Train / val split: `70%` / `15%`
- Epochs: `3`
- Batch size: `256`
- Negative ratio: `0.0`
- Channels: `64, 64, 96`
- Hidden dim: `128`
- Dropout: `0.15`

## Backtest Summary

- Trades: `14`
- Active trading days: `7`
- First trade date: `2020-02-28`
- Last trade date: `2020-03-11`
- Calendar span covered by active trades: `13` days
- Win rate: `0.07143`
- Loss rate: `0.00000`
- Expectancy: `0.114290R` per trade
- Average R per trade: `0.114290R`
- Total R: `1.60R`
- Profit factor: `0.000000`
- Average win: `1.600062R`
- Average loss: `n/a`
- Realized payoff ratio: `n/a`
- Average hold time: `1.000000` bars
- Ending balance: `$101,044.83`
- Return: `1.0448%`
- Max drawdown: `0.0000%`
- Drawdown peak date: `None`
- Drawdown trough date: `None`
- Best trade: `2020-03-02` | `long_reversal` | `$1,044.83` | `1.60R` | `utility_label`
- Worst trade: `2020-02-28` | `long_reversal` | `$0.00` | `0.00R` | `utility_label`

## Distribution

- Median trade: `0.0`R
- Trade R std dev: `0.427635`
- Mean daily return: `0.149261`%
- Daily return std dev: `0.394909`%
- Daily Sharpe proxy: `0.378`
- Daily Sortino proxy: `None`

## Acceptance Metrics

- Pass probability 30 / 60 / 90: `0.006` / `0.338` / `0.854`
- Median / avg days to pass: `None` / `None`
- Profitable-day hit rate day 10 / 20: `0.0` / `0.0`
- Longest trade loss streak: `0`
- Longest negative day streak: `0`
- Worst month return %: `0.0`
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
- Profitable days on the recorded test path: `1`
- Historical rolling-start pass rate: `0.000000` (0/7)
- Fastest historical rolling-start pass: `None` active trading days
- Average historical rolling-start pass: `None` active trading days
- Median historical rolling-start pass: `None` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.007000`, average pass day `26.93`, median pass day `27`, min pass day `21`
  - `60`-day horizon: pass probability `0.354500`, average pass day `48.82`, median pass day `50`, min pass day `24`
  - `66`-day horizon: pass probability `0.481000`, average pass day `53.33`, median pass day `55`, min pass day `20`
  - `90`-day horizon: pass probability `0.848500`, average pass day `63.65`, median pass day `64`, min pass day `20`
  - `120`-day horizon: pass probability `0.979500`, average pass day `68.84`, median pass day `67`, min pass day `20`

## Daily Consistency

- Profitable days: `1`
- Losing days: `0`
- Positive day rate: `0.142857`
- Average daily return: `0.149261%`
- Median daily return: `0.000000%`
- Best day: `2020-03-02` | `$1,044.83` | `1.60R` | `0.0000%` | `2` trades
- Worst day: `2020-02-28` | `$0.00` | `0.00R` | `0.0000%` | `2` trades

## Streaks

- Longest win streak: `1` trades
- Longest loss streak: `0` trades
- Longest positive-day streak: `1` days
- Longest negative-day streak: `0` days

## Start Timing

- After `flat_or_unknown` streak `0`: `6` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `1`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `2.000000`
- Median trades per day: `2.000000`
- Days at max-trade cap: `7` / `7`
- Capacity utilization on active days: `100.0000%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`, `allocator_low_utility=0`

## Breakdown By Setup

- `long_reversal`: trades `14`, win rate `0.071429`, expectancy `0.114290R`, total `1.600062R`, PnL `$1,044.83`

## Breakdown By Market Session

- `us`: trades `8`, win rate `0.125000`, expectancy `0.200008R`, total `1.600062R`
- `europe`: trades `6`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`

## Breakdown By Session Phase

- `late_60_80`: trades `4`, win rate `0.250000`, expectancy `0.400016R`, total `1.600062R`
- `close_80_100`: trades `4`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`
- `mid_40_60`: trades `6`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`

## Best Days

- `2020-03-02`: `$1,044.83` | `1.60R` | `0.0000%` | `2` trades
- `2020-02-28`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-03`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-04`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-05`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-06`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-11`: `$0.00` | `0.00R` | `0.0000%` | `2` trades

## Worst Days

- `2020-02-28`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-03`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-04`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-05`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-06`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-11`: `$0.00` | `0.00R` | `0.0000%` | `2` trades
- `2020-03-02`: `$1,044.83` | `1.60R` | `0.0000%` | `2` trades

## Sequence Diagnostics


### After Loss Streaks


### After Win Streaks

- Prior `win` streak `1`: `1` samples, next-trade win probability `0.000000`, next-trade expectancy `0.000000R`, `next_5_trade_avg_r` `0.000000R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
