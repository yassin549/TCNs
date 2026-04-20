# Current Baseline Report

Generated at `2026-04-17T17:25:46.071834+00:00` from `frontier_utility/real_2h`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\real_2h`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\real_2h\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\real_2h\manager_policy.json`
- Dataset: `artifacts\frontier_utility\real_2h\utility_dataset.csv.gz`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\frontier_utility\real_2h\backtest_summary.json`

## Training Snapshot

- Lookback: `96` bars
- Feature count: `70`
- Train / val split: `70%` / `15%`
- Epochs: `10`
- Batch size: `256`
- Negative ratio: `0.0`
- Channels: `64, 64, 96`
- Hidden dim: `128`
- Dropout: `0.15`

## Backtest Summary

- Trades: `3`
- Active trading days: `3`
- First trade date: `2021-08-11`
- Last trade date: `2021-08-24`
- Calendar span covered by active trades: `14` days
- Win rate: `0.33333`
- Loss rate: `0.00000`
- Expectancy: `0.427181R` per trade
- Average R per trade: `0.427181R`
- Total R: `1.28R`
- Profit factor: `0.000000`
- Average win: `1.281543R`
- Average loss: `n/a`
- Realized payoff ratio: `n/a`
- Average hold time: `1.000000` bars
- Ending balance: `$100,320.39`
- Return: `0.3204%`
- Max drawdown: `0.0000%`
- Drawdown peak date: `None`
- Drawdown trough date: `None`
- Best trade: `2021-08-24` | `short_reversal` | `$320.39` | `1.28R` | `utility_label`
- Worst trade: `2021-08-11` | `short_reversal` | `$0.00` | `0.00R` | `utility_label`

## Distribution

- Median trade: `0.0`R
- Trade R std dev: `0.739899`
- Mean daily return: `0.106797`%
- Daily return std dev: `0.184977`%
- Daily Sharpe proxy: `0.5774`
- Daily Sortino proxy: `None`

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
- Historical rolling-start pass rate: `0.000000` (0/3)
- Fastest historical rolling-start pass: `None` active trading days
- Average historical rolling-start pass: `None` active trading days
- Median historical rolling-start pass: `None` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.000000`, average pass day `None`, median pass day `None`, min pass day `None`
  - `60`-day horizon: pass probability `0.006000`, average pass day `58.25`, median pass day `59`, min pass day `55`
  - `66`-day horizon: pass probability `0.028000`, average pass day `62.88`, median pass day `64`, min pass day `54`
  - `90`-day horizon: pass probability `0.546500`, average pass day `80.5`, median pass day `82`, min pass day `53`
  - `120`-day horizon: pass probability `0.983000`, average pass day `89.15`, median pass day `89`, min pass day `51`

## Daily Consistency

- Profitable days: `1`
- Losing days: `0`
- Positive day rate: `0.333333`
- Average daily return: `0.106797%`
- Median daily return: `0.000000%`
- Best day: `2021-08-24` | `$320.39` | `1.28R` | `0.3204%` | `1` trades
- Worst day: `2021-08-11` | `$0.00` | `0.00R` | `0.0000%` | `1` trades

## Streaks

- Longest win streak: `1` trades
- Longest loss streak: `0` trades
- Longest positive-day streak: `1` days
- Longest negative-day streak: `0` days

## Start Timing

- After `flat_or_unknown` streak `0`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `1.000000`
- Median trades per day: `1.000000`
- Days at max-trade cap: `0` / `3`
- Capacity utilization on active days: `33.3333%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`, `allocator_low_utility=19908`

## Breakdown By Setup

- `short_reversal`: trades `3`, win rate `0.333333`, expectancy `0.427181R`, total `1.281543R`, PnL `$320.39`

## Breakdown By Market Session

- `asia`: trades `1`, win rate `1.000000`, expectancy `1.281543R`, total `1.281543R`
- `europe`: trades `1`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`
- `us`: trades `1`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`

## Breakdown By Session Phase

- `build_20_40`: trades `1`, win rate `1.000000`, expectancy `1.281543R`, total `1.281543R`
- `late_60_80`: trades `2`, win rate `0.000000`, expectancy `0.000000R`, total `0.000000R`

## Best Days

- `2021-08-24`: `$320.39` | `1.28R` | `0.3204%` | `1` trades
- `2021-08-11`: `$0.00` | `0.00R` | `0.0000%` | `1` trades
- `2021-08-19`: `$0.00` | `0.00R` | `0.0000%` | `1` trades

## Worst Days

- `2021-08-11`: `$0.00` | `0.00R` | `0.0000%` | `1` trades
- `2021-08-19`: `$0.00` | `0.00R` | `0.0000%` | `1` trades
- `2021-08-24`: `$320.39` | `1.28R` | `0.3204%` | `1` trades

## Sequence Diagnostics


### After Loss Streaks


### After Win Streaks


## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
