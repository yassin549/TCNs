# Current Baseline Report

Generated at `2026-04-14T15:24:19.892613+00:00` from `specialist_tcns/us100_session_refined_fundedhive`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_fundedhive`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_fundedhive\manager_policy.json`
- Dataset: `C:\Users\khoua\OneDrive\Desktop\TCNs\data\features\us100_specialist_tcn_dataset_session_refined.csv.gz`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined\backtest_summary.json`

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

- Trades: `391`
- Active trading days: `66`
- First trade date: `2024-12-06`
- Last trade date: `2025-09-10`
- Calendar span covered by active trades: `279` days
- Win rate: `0.40665`
- Loss rate: `0.59335`
- Expectancy: `0.084399R` per trade
- Average R per trade: `0.084399R`
- Total R: `33.00R`
- Profit factor: `1.142241`
- Average win: `1.666667R`
- Average loss: `-1.000000R`
- Realized payoff ratio: `1.666667`
- Average hold time: `3.173913` bars
- Ending balance: `$108,371.77`
- Return: `8.3718%`
- Max drawdown: `5.4092%`
- Drawdown peak date: `2025-01-30`
- Drawdown trough date: `2025-03-03`
- Best trade: `2025-09-10` | `long_continuation` | `$449.68` | `1.67R` | `target`
- Worst trade: `2025-09-09` | `short_reversal` | `$-268.24` | `-1.00R` | `stop`

## Distribution

- Median trade: `-1.0`R
- Trade R std dev: `1.311567`
- Mean daily return: `0.125598`%
- Daily return std dev: `0.869086`%
- Daily Sharpe proxy: `0.1445`
- Daily Sortino proxy: `0.2708`

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
- Profitable days on the recorded test path: `32`
- Historical rolling-start pass rate: `0.000000` (0/66)
- Fastest historical rolling-start pass: `None` active trading days
- Average historical rolling-start pass: `None` active trading days
- Median historical rolling-start pass: `None` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.139000`, average pass day `23.75`, median pass day `25`, min pass day `10`
  - `60`-day horizon: pass probability `0.463000`, average pass day `37.82`, median pass day `37`, min pass day `8`
  - `66`-day horizon: pass probability `0.503000`, average pass day `40.93`, median pass day `41`, min pass day `6`
  - `90`-day horizon: pass probability `0.684000`, average pass day `48.41`, median pass day `47`, min pass day `8`
  - `120`-day horizon: pass probability `0.804500`, average pass day `57.61`, median pass day `53`, min pass day `6`

## Daily Consistency

- Profitable days: `32`
- Losing days: `34`
- Positive day rate: `0.484848`
- Average daily return: `0.125598%`
- Median daily return: `-0.169500%`
- Best day: `2025-03-04` | `$2,560.27` | `10.00R` | `2.5262%` | `6` trades
- Worst day: `2025-01-31` | `$-1,597.15` | `-6.00R` | `-1.4907%` | `6` trades

## Streaks

- Longest win streak: `8` trades
- Longest loss streak: `7` trades
- Longest positive-day streak: `4` days
- Longest negative-day streak: `6` days

## Start Timing

- After `win` streak `1`: `18` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `1`: `12` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `2`: `10` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `2`: `7` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `3`: `6` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `4`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `6`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `5`: `2` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `flat_or_unknown` streak `0`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `3`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `5.924242`
- Median trades per day: `6.000000`
- Days at max-trade cap: `65` / `66`
- Capacity utilization on active days: `98.7374%`
- Skip counts: `cooldown=2799`, `ineligible=12180`, `session_end_buffer=2015`, `daily_trade_cap=51716`

## Breakdown By Setup

- `short_reversal`: trades `131`, win rate `0.419847`, expectancy `0.119593R`, total `15.666667R`, PnL `$3,986.58`
- `long_reversal`: trades `99`, win rate `0.424242`, expectancy `0.131313R`, total `13.000000R`, PnL `$3,370.36`
- `short_continuation`: trades `36`, win rate `0.416667`, expectancy `0.111111R`, total `4.000000R`, PnL `$1,038.65`
- `long_continuation`: trades `125`, win rate `0.376000`, expectancy `0.002667R`, total `0.333333R`, PnL `$-23.82`

## Breakdown By Market Session

- `asia`: trades `326`, win rate `0.401840`, expectancy `0.071575R`, total `23.333333R`
- `europe`: trades `64`, win rate `0.421875`, expectancy `0.125000R`, total `8.000000R`
- `us`: trades `1`, win rate `1.000000`, expectancy `1.666667R`, total `1.666667R`

## Breakdown By Session Phase

- `build_20_40`: trades `167`, win rate `0.419162`, expectancy `0.117764R`, total `19.666667R`
- `mid_40_60`: trades `58`, win rate `0.413793`, expectancy `0.103448R`, total `6.000000R`
- `opening_0_20`: trades `159`, win rate `0.383648`, expectancy `0.023061R`, total `3.666667R`
- `late_60_80`: trades `6`, win rate `0.500000`, expectancy `0.333333R`, total `2.000000R`
- `close_80_100`: trades `1`, win rate `1.000000`, expectancy `1.666667R`, total `1.666667R`

## Best Days

- `2025-03-04`: `$2,560.27` | `10.00R` | `2.5262%` | `6` trades
- `2025-09-08`: `$1,933.01` | `7.33R` | `1.8455%` | `6` trades
- `2025-02-25`: `$1,898.95` | `7.33R` | `1.8455%` | `6` trades
- `2024-12-09`: `$1,842.39` | `7.33R` | `1.8455%` | `6` trades
- `2025-09-09`: `$1,247.41` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-03`: `$1,231.06` | `4.67R` | `1.1694%` | `6` trades
- `2024-12-19`: `$1,222.81` | `4.67R` | `1.1694%` | `6` trades
- `2025-03-06`: `$1,221.12` | `4.67R` | `1.1694%` | `6` trades
- `2024-12-16`: `$1,220.86` | `4.67R` | `1.1694%` | `6` trades
- `2025-02-21`: `$1,207.32` | `4.67R` | `1.1694%` | `6` trades

## Worst Days

- `2025-01-31`: `$-1,597.15` | `-6.00R` | `-1.4907%` | `6` trades
- `2024-12-18`: `$-1,582.36` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-02-24`: `$-1,557.03` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-03-03`: `$-1,533.62` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-09-04`: `$-886.44` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-03-27`: `$-883.65` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-02`: `$-883.55` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-02-04`: `$-882.82` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-01-21`: `$-880.16` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-05`: `$-879.06` | `-3.33R` | `-0.8323%` | `6` trades

## Sequence Diagnostics


### After Loss Streaks

- Prior `loss` streak `1`: `103` samples, next-trade win probability `0.436893`, next-trade expectancy `0.165049R`, `next_5_trade_avg_r` `0.040777R`
- Prior `loss` streak `2`: `58` samples, next-trade win probability `0.465517`, next-trade expectancy `0.241379R`, `next_5_trade_avg_r` `-0.006897R`
- Prior `loss` streak `3`: `31` samples, next-trade win probability `0.354839`, next-trade expectancy `-0.053763R`, `next_5_trade_avg_r` `0.169892R`
- Prior `loss` streak `4`: `20` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.253333R`
- Prior `loss` streak `5`: `10` samples, next-trade win probability `0.400000`, next-trade expectancy `0.066667R`, `next_5_trade_avg_r` `0.280000R`
- Prior `loss` streak `6`: `6` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.688889R`
- Prior `loss` streak `7`: `4` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.733333R`

### After Win Streaks

- Prior `win` streak `1`: `103` samples, next-trade win probability `0.320388`, next-trade expectancy `-0.145631R`, `next_5_trade_avg_r` `0.009709R`
- Prior `win` streak `2`: `33` samples, next-trade win probability `0.363636`, next-trade expectancy `-0.030303R`, `next_5_trade_avg_r` `0.159596R`
- Prior `win` streak `3`: `11` samples, next-trade win probability `0.454545`, next-trade expectancy `0.212121R`, `next_5_trade_avg_r` `0.357576R`
- Prior `win` streak `4`: `5` samples, next-trade win probability `0.600000`, next-trade expectancy `0.600000R`, `next_5_trade_avg_r` `0.386667R`
- Prior `win` streak `5`: `3` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.244444R`
- Prior `win` streak `6`: `1` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.066667R`
- Prior `win` streak `7`: `1` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.066667R`
- Prior `win` streak `8`: `1` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `0.066667R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
