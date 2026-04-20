# Current Baseline Report

Generated at `2026-04-18T11:45:36.710771+00:00` from `specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\backtest_trades.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\manager_policy.json`
- Dataset: `C:\Users\khoua\OneDrive\Desktop\TCNs\data\features\us100_specialist_tcn_dataset_session_refined_rerun_20260415.csv.gz`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\backtest_summary.json`
- Execution mode: `None`
- Policy selection: `gated_moe_highest_probability_above_threshold`
- Raw source summary: `None`

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

- Trades: `418`
- Active trading days: `70`
- First trade date: `2024-12-06`
- Last trade date: `2025-09-16`
- Calendar span covered by active trades: `285` days
- Win rate: `0.40431`
- Loss rate: `0.59569`
- Expectancy: `0.078150R` per trade
- Average R per trade: `0.078150R`
- Total R: `32.67R`
- Profit factor: `1.131191`
- Average win: `1.666667R`
- Average loss: `-1.000000R`
- Realized payoff ratio: `1.666667`
- Average hold time: `3.224880` bars
- Ending balance: `$108,266.36`
- Return: `8.2664%`
- Max drawdown: `4.7929%`
- Drawdown peak date: `2025-01-27`
- Drawdown trough date: `2025-03-03`
- Best trade: `2025-09-16` | `long_continuation` | `$449.24` | `1.67R` | `target`
- Worst trade: `2025-09-10` | `short_reversal` | `$-268.90` | `-1.00R` | `stop`

## Distribution

- Median trade: `-1.0`R
- Trade R std dev: `1.310254`
- Mean daily return: `0.117335`%
- Daily return std dev: `0.880035`%
- Daily Sharpe proxy: `0.1333`
- Daily Sortino proxy: `0.2465`

## Acceptance Metrics

- Pass probability 30 / 60 / 90: `0.255` / `0.5825` / `0.729`
- Median / avg days to pass: `69` / `69.5`
- Profitable-day hit rate day 10 / 20: `0.0` / `0.0`
- Longest trade loss streak: `9`
- Longest negative day streak: `4`
- Worst month return %: `-1.152446`
- Loss cluster penalty: `0.692957`

## Prop-Firm Metrics

- Policy: `legacy_prop_policy`
- Profit target: `8.00%`
- Minimum profitable days: `0`
- Max total drawdown: `6.00%`
- Max daily loss: `2.00%`
- Hard max loss per trade: `0.25%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `True`
- Days to pass on the recorded test path: `70` active trading days
- Profitable days on the recorded test path: `31`
- Historical rolling-start pass rate: `0.028571` (2/70)
- Fastest historical rolling-start pass: `69` active trading days
- Average historical rolling-start pass: `69.5` active trading days
- Median historical rolling-start pass: `69` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.255000`, average pass day `20.84`, median pass day `21`, min pass day `6`
  - `60`-day horizon: pass probability `0.582500`, average pass day `33.71`, median pass day `33`, min pass day `5`
  - `66`-day horizon: pass probability `0.625500`, average pass day `36.99`, median pass day `36`, min pass day `6`
  - `90`-day horizon: pass probability `0.729000`, average pass day `42.9`, median pass day `40`, min pass day `7`
  - `120`-day horizon: pass probability `0.792500`, average pass day `48.15`, median pass day `43`, min pass day `5`

## Daily Consistency

- Profitable days: `31`
- Losing days: `39`
- Positive day rate: `0.442857`
- Average daily return: `0.117335%`
- Median daily return: `-0.169502%`
- Best day: `2025-03-04` | `$2,543.26` | `10.00R` | `2.5262%` | `6` trades
- Worst day: `2025-09-12` | `$-1,592.66` | `-6.00R` | `-1.4907%` | `6` trades

## Streaks

- Longest win streak: `8` trades
- Longest loss streak: `9` trades
- Longest positive-day streak: `3` days
- Longest negative-day streak: `4` days

## Start Timing

- After `flat_or_unknown` streak `0`: `1` starts, pass rate `1.000000`, average days to pass `70.0`, median days to pass `70.0`
- After `loss` streak `1`: `9` starts, pass rate `0.111111`, average days to pass `69.0`, median days to pass `69.0`
- After `win` streak `1`: `22` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `2`: `11` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `3`: `8` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `2`: `6` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `4`: `4` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `6`: `3` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `win` streak `4`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`
- After `loss` streak `5`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `5.971429`
- Median trades per day: `6.000000`
- Days at max-trade cap: `69` / `70`
- Capacity utilization on active days: `99.5238%`
- Skip counts: `cooldown=3014`, `ineligible=12920`, `session_end_buffer=2139`, `daily_trade_cap=58072`, `allocator_low_utility=0`

## Breakdown By Setup

- `short_reversal`: trades `140`, win rate `0.428571`, expectancy `0.142857R`, total `20.000000R`, PnL `$5,078.22`
- `long_reversal`: trades `88`, win rate `0.443182`, expectancy `0.181818R`, total `16.000000R`, PnL `$4,128.57`
- `short_continuation`: trades `73`, win rate `0.369863`, expectancy `-0.013699R`, total `-1.000000R`, PnL `$-313.38`
- `long_continuation`: trades `117`, win rate `0.367521`, expectancy `-0.019943R`, total `-2.333333R`, PnL `$-627.07`

## Breakdown By Market Session

- `asia`: trades `373`, win rate `0.407507`, expectancy `0.086685R`, total `32.333333R`
- `europe`: trades `45`, win rate `0.377778`, expectancy `0.007407R`, total `0.333333R`

## Breakdown By Session Phase

- `build_20_40`: trades `182`, win rate `0.423077`, expectancy `0.128205R`, total `23.333333R`
- `opening_0_20`: trades `191`, win rate `0.392670`, expectancy `0.047120R`, total `9.000000R`
- `late_60_80`: trades `3`, win rate `1.000000`, expectancy `1.666667R`, total `5.000000R`
- `mid_40_60`: trades `42`, win rate `0.333333`, expectancy `-0.111111R`, total `-4.666667R`

## Best Days

- `2025-03-04`: `$2,543.26` | `10.00R` | `2.5262%` | `6` trades
- `2025-02-25`: `$1,861.39` | `7.33R` | `1.8455%` | `6` trades
- `2024-12-09`: `$1,842.39` | `7.33R` | `1.8455%` | `6` trades
- `2025-09-16`: `$1,785.80` | `6.67R` | `1.6771%` | `4` trades
- `2025-09-09`: `$1,230.90` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-15`: `$1,230.75` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-03`: `$1,222.88` | `4.67R` | `1.1694%` | `6` trades
- `2025-03-07`: `$1,219.05` | `4.67R` | `1.1694%` | `6` trades
- `2025-09-08`: `$1,216.66` | `4.67R` | `1.1694%` | `6` trades
- `2025-03-06`: `$1,204.96` | `4.67R` | `1.1694%` | `6` trades

## Worst Days

- `2025-09-12`: `$-1,592.66` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-01-31`: `$-1,555.17` | `-6.00R` | `-1.4907%` | `6` trades
- `2024-12-18`: `$-1,551.05` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-02-20`: `$-1,531.39` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-02-24`: `$-1,526.21` | `-6.00R` | `-1.4907%` | `6` trades
- `2025-09-04`: `$-880.57` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-03-27`: `$-877.79` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-02`: `$-877.69` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-09-05`: `$-873.23` | `-3.33R` | `-0.8323%` | `6` trades
- `2025-01-28`: `$-872.72` | `-3.33R` | `-0.8323%` | `6` trades

## Sequence Diagnostics


### After Loss Streaks

- Prior `loss` streak `1`: `106` samples, next-trade win probability `0.443396`, next-trade expectancy `0.182390R`, `next_5_trade_avg_r` `0.021384R`
- Prior `loss` streak `2`: `59` samples, next-trade win probability `0.406780`, next-trade expectancy `0.084746R`, `next_5_trade_avg_r` `0.021469R`
- Prior `loss` streak `3`: `35` samples, next-trade win probability `0.428571`, next-trade expectancy `0.142857R`, `next_5_trade_avg_r` `0.081905R`
- Prior `loss` streak `4`: `20` samples, next-trade win probability `0.400000`, next-trade expectancy `0.066667R`, `next_5_trade_avg_r` `0.200000R`
- Prior `loss` streak `5`: `12` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.244444R`
- Prior `loss` streak `6`: `6` samples, next-trade win probability `0.166667`, next-trade expectancy `-0.555556R`, `next_5_trade_avg_r` `0.333333R`
- Prior `loss` streak `7`: `5` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `0.493333R`
- Prior `loss` streak `8`: `5` samples, next-trade win probability `0.800000`, next-trade expectancy `1.133333R`, `next_5_trade_avg_r` `0.813333R`
- Prior `loss` streak `9`: `1` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `1.666667R`

### After Win Streaks

- Prior `win` streak `1`: `106` samples, next-trade win probability `0.339623`, next-trade expectancy `-0.094340R`, `next_5_trade_avg_r` `-0.018868R`
- Prior `win` streak `2`: `36` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.155556R`
- Prior `win` streak `3`: `12` samples, next-trade win probability `0.583333`, next-trade expectancy `0.555556R`, `next_5_trade_avg_r` `0.466667R`
- Prior `win` streak `4`: `7` samples, next-trade win probability `0.571429`, next-trade expectancy `0.523810R`, `next_5_trade_avg_r` `0.295238R`
- Prior `win` streak `5`: `4` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.466667R`
- Prior `win` streak `6`: `1` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.600000R`
- Prior `win` streak `7`: `1` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.066667R`
- Prior `win` streak `8`: `1` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `-0.466667R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
