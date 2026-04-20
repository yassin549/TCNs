# Current Baseline Report

Generated at `2026-04-17T20:11:53.523930+00:00` from `specialist_tcns/us100_session_refined`.

## Baseline Snapshot

- Artifact: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench`
- Trade log: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\backtest_trades_rerun_20260417.csv.gz`
- Manager policy: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\manager_policy.json`
- Dataset: `None`
- Test split summary: `C:\Users\khoua\OneDrive\Desktop\TCNs\artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_workbench\backtest_summary_rerun_20260417.json`
- Execution mode: `frontier_managed`
- Policy selection: `frontier_contextual_abstention_manager`
- Raw source summary: `{'trades': 453, 'trading_days': 76, 'win_rate': 0.408389, 'expectancy_r': 0.089036, 'total_r': 40.333333, 'profit_factor': 1.150498, 'average_hold_bars': 3.196468, 'ending_balance': 110339.63, 'total_return_pct': 10.3396, 'max_drawdown_pct': 4.7929, 'reached_profit_target': True, 'days_to_target': 76, 'breached_total_drawdown': False, 'skip_counts': {'cooldown': 3254, 'ineligible': 14030, 'session_end_buffer': 2325, 'daily_lock': 0, 'daily_trade_cap': 63649, 'daily_risk_budget': 0, 'total_drawdown_budget': 0}}`

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

- Trades: `207`
- Active trading days: `76`
- First trade date: `2024-12-06`
- Last trade date: `2025-09-24`
- Calendar span covered by active trades: `293` days
- Win rate: `0.48309`
- Loss rate: `0.51691`
- Expectancy: `0.288245R` per trade
- Average R per trade: `0.288245R`
- Total R: `59.67R`
- Profit factor: `1.557632`
- Average win: `1.666667R`
- Average loss: `-1.000000R`
- Realized payoff ratio: `1.666667`
- Average hold time: `3.246377` bars
- Ending balance: `$123,985.57`
- Return: `23.9856%`
- Max drawdown: `2.0266%`
- Drawdown peak date: `2025-01-27`
- Drawdown trough date: `2025-02-03`
- Best trade: `2025-09-22` | `long_reversal` | `$914.57` | `1.67R` | `target`
- Worst trade: `2025-08-21` | `long_reversal` | `$-527.19` | `-1.00R` | `stop`

## Distribution

- Median trade: `-1.0`R
- Trade R std dev: `1.335801`
- Mean daily return: `0.285449`%
- Daily return std dev: `0.662687`%
- Daily Sharpe proxy: `0.4307`
- Daily Sortino proxy: `1.0764`

## Acceptance Metrics

- Pass probability 30 / 60 / 90: `0.402` / `0.946` / `0.996`
- Median / avg days to pass: `35.5` / `34.980769`
- Profitable-day hit rate day 10 / 20: `0.973684` / `0.973684`
- Longest trade loss streak: `5`
- Longest negative day streak: `5`
- Worst month return %: `-0.698875`
- Loss cluster penalty: `0.659176`

## Prop-Firm Metrics

- Policy: `FundedHive`
- Profit target: `10.00%`
- Minimum profitable days: `3`
- Max total drawdown: `10.00%`
- Max daily loss: `5.00%`
- Hard max loss per trade: `3.00%`
- Configured base risk per trade: `0.25%`
- Actual test path passed: `True`
- Days to pass on the recorded test path: `47` active trading days
- Profitable days on the recorded test path: `25`
- Historical rolling-start pass rate: `0.684211` (52/76)
- Fastest historical rolling-start pass: `23` active trading days
- Average historical rolling-start pass: `34.98` active trading days
- Median historical rolling-start pass: `35` active trading days
- Bootstrap pass probabilities from active-day return resampling:
  - `30`-day horizon: pass probability `0.427000`, average pass day `23.72`, median pass day `24`, min pass day `11`
  - `60`-day horizon: pass probability `0.948000`, average pass day `33.56`, median pass day `32`, min pass day `11`
  - `66`-day horizon: pass probability `0.963500`, average pass day `34.04`, median pass day `32`, min pass day `9`
  - `90`-day horizon: pass probability `0.997500`, average pass day `35.67`, median pass day `33`, min pass day `11`
  - `120`-day horizon: pass probability `1.000000`, average pass day `35.85`, median pass day `33`, min pass day `11`

## Daily Consistency

- Profitable days: `47`
- Losing days: `29`
- Positive day rate: `0.618421`
- Average daily return: `0.285449%`
- Median daily return: `0.246882%`
- Best day: `2025-02-21` | `$2,079.52` | `5.00R` | `1.9286%` | `3` trades
- Worst day: `2025-09-02` | `$-1,047.26` | `-2.00R` | `-0.8980%` | `2` trades

## Streaks

- Longest win streak: `5` trades
- Longest loss streak: `5` trades
- Longest positive-day streak: `7` days
- Longest negative-day streak: `5` days

## Start Timing

- After `loss` streak `4`: `3` starts, pass rate `1.000000`, average days to pass `32.3333333333`, median days to pass `29.0`
- After `flat_or_unknown` streak `0`: `1` starts, pass rate `1.000000`, average days to pass `47.0`, median days to pass `47.0`
- After `loss` streak `2`: `8` starts, pass rate `0.875000`, average days to pass `33.1428571429`, median days to pass `31.0`
- After `win` streak `2`: `11` starts, pass rate `0.727273`, average days to pass `37.125`, median days to pass `36.5`
- After `loss` streak `1`: `21` starts, pass rate `0.714286`, average days to pass `37.7333333333`, median days to pass `36.0`
- After `win` streak `3`: `3` starts, pass rate `0.666667`, average days to pass `27.0`, median days to pass `27.0`
- After `loss` streak `3`: `8` starts, pass rate `0.625000`, average days to pass `27.2`, median days to pass `24.0`
- After `win` streak `1`: `18` starts, pass rate `0.555556`, average days to pass `36.5`, median days to pass `38.5`
- After `loss` streak `5`: `2` starts, pass rate `0.500000`, average days to pass `25.0`, median days to pass `25.0`
- After `win` streak `4`: `1` starts, pass rate `0.000000`, average days to pass `None`, median days to pass `None`

## Operating Profile

- Average trades per day: `2.723684`
- Median trades per day: `3.000000`
- Days at max-trade cap: `56` / `76`
- Capacity utilization on active days: `90.7895%`
- Skip counts: `cooldown=0`, `ineligible=0`, `session_end_buffer=0`, `daily_trade_cap=0`, `allocator_low_utility=0`

## Breakdown By Setup

- `long_reversal`: trades `61`, win rate `0.573770`, expectancy `0.530055R`, total `32.333333R`, PnL `$12,616.37`
- `short_reversal`: trades `51`, win rate `0.529412`, expectancy `0.411765R`, total `21.000000R`, PnL `$6,057.72`
- `short_continuation`: trades `35`, win rate `0.457143`, expectancy `0.219048R`, total `7.666667R`, PnL `$5,999.85`
- `long_continuation`: trades `60`, win rate `0.366667`, expectancy `-0.022222R`, total `-1.333333R`, PnL `$-688.37`

## Breakdown By Market Session

- `asia`: trades `196`, win rate `0.474490`, expectancy `0.265306R`, total `52.000000R`
- `europe`: trades `11`, win rate `0.636364`, expectancy `0.696970R`, total `7.666667R`

## Breakdown By Session Phase

- `opening_0_20`: trades `123`, win rate `0.455285`, expectancy `0.214092R`, total `26.333333R`
- `build_20_40`: trades `73`, win rate `0.506849`, expectancy `0.351598R`, total `25.666667R`
- `mid_40_60`: trades `11`, win rate `0.636364`, expectancy `0.696970R`, total `7.666667R`

## Best Days

- `2025-02-21`: `$2,079.52` | `5.00R` | `1.9286%` | `3` trades
- `2025-09-19`: `$1,507.73` | `2.33R` | `1.2519%` | `3` trades
- `2025-03-04`: `$1,397.92` | `5.00R` | `1.2552%` | `3` trades
- `2025-02-28`: `$1,383.87` | `2.33R` | `1.2519%` | `3` trades
- `2025-02-25`: `$1,369.26` | `5.00R` | `1.2552%` | `3` trades
- `2025-02-12`: `$1,350.95` | `2.33R` | `1.2519%` | `3` trades
- `2025-01-21`: `$1,308.42` | `2.33R` | `1.2519%` | `3` trades
- `2024-12-13`: `$1,264.67` | `2.33R` | `1.2519%` | `3` trades
- `2025-09-11`: `$1,082.55` | `2.33R` | `0.9169%` | `3` trades
- `2024-12-27`: `$1,074.72` | `2.33R` | `1.0489%` | `3` trades

## Worst Days

- `2025-09-02`: `$-1,047.26` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-02-20`: `$-1,031.03` | `-3.00R` | `-0.9471%` | `3` trades
- `2025-01-31`: `$-958.84` | `-2.00R` | `-0.8980%` | `2` trades
- `2025-02-24`: `$-822.25` | `-3.00R` | `-0.7481%` | `3` trades
- `2025-08-21`: `$-820.80` | `-2.00R` | `-0.6989%` | `2` trades
- `2024-12-18`: `$-719.36` | `-2.00R` | `-0.6989%` | `2` trades
- `2025-09-12`: `$-595.01` | `-2.00R` | `-0.4994%` | `2` trades
- `2025-09-05`: `$-581.55` | `-2.00R` | `-0.4994%` | `2` trades
- `2025-03-03`: `$-558.94` | `-2.00R` | `-0.4994%` | `2` trades
- `2025-02-13`: `$-545.65` | `-2.00R` | `-0.4994%` | `2` trades

## Sequence Diagnostics


### After Loss Streaks

- Prior `loss` streak `1`: `58` samples, next-trade win probability `0.551724`, next-trade expectancy `0.471264R`, `next_5_trade_avg_r` `0.351724R`
- Prior `loss` streak `2`: `26` samples, next-trade win probability `0.576923`, next-trade expectancy `0.538462R`, `next_5_trade_avg_r` `0.333333R`
- Prior `loss` streak `3`: `11` samples, next-trade win probability `0.363636`, next-trade expectancy `-0.030303R`, `next_5_trade_avg_r` `0.551515R`
- Prior `loss` streak `4`: `7` samples, next-trade win probability `0.285714`, next-trade expectancy `-0.238095R`, `next_5_trade_avg_r` `0.523810R`
- Prior `loss` streak `5`: `5` samples, next-trade win probability `1.000000`, next-trade expectancy `1.666667R`, `next_5_trade_avg_r` `0.600000R`

### After Win Streaks

- Prior `win` streak `1`: `58` samples, next-trade win probability `0.500000`, next-trade expectancy `0.333333R`, `next_5_trade_avg_r` `0.266667R`
- Prior `win` streak `2`: `28` samples, next-trade win probability `0.321429`, next-trade expectancy `-0.142857R`, `next_5_trade_avg_r` `0.187302R`
- Prior `win` streak `3`: `9` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `0.007407R`
- Prior `win` streak `4`: `3` samples, next-trade win probability `0.333333`, next-trade expectancy `-0.111111R`, `next_5_trade_avg_r` `-0.111111R`
- Prior `win` streak `5`: `1` samples, next-trade win probability `0.000000`, next-trade expectancy `-1.000000R`, `next_5_trade_avg_r` `0.600000R`

## Notes

- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.
- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.
- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.
- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.
- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.
