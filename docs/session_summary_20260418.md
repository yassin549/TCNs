# Session Summary 2026-04-18

Date: `2026-04-18`

## Objective

Continue improving the frontier-managed specialist TCN stack while keeping continuation enabled, reducing Asia-open continuation bleed, and regenerating the canonical workbench outputs from the updated manager logic.

## What Was Implemented

### 1. Continuation stayed enabled

We did not revert to the earlier default of globally disabling continuation experts.

Instead, the work in [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1) focused on making continuation more selective inside the weakest realized slice.

### 2. Added targeted bucket controls for `long_continuation / asia / opening_0_20`

The manager builder now supports reusable bucket-rule generation for fragile slices and applies it to:

- `short_reversal / asia / build_20_40`
- `long_continuation / asia / opening_0_20`

The `long_continuation / asia / opening_0_20` control adds:

- probability-bucket blacklisting for negative buckets
- a stricter minimum probability surplus
- tighter risk handling for fragile continuation buckets

This reduced the Asia-open long-continuation bleed without disabling continuation overall.

### 3. Ran the full downstream frontier workbench rerun

The interrupted full-cycle training run was allowed to complete as far as its written artifacts, then the canonical downstream stages were resumed manually:

1. `analyze`
2. legacy backtest
3. legacy baseline report
4. frontier policy rebuild
5. frontier-managed backtest
6. canonical baseline report
7. diagnostics and comparison outputs

This regenerated the active canonical workbench artifact and report set.

## Canonical Outputs Updated

Primary refreshed outputs:

- [manager_policy.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench/manager_policy.json:1)
- [backtest_summary.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench/backtest_summary.json:1)
- [baseline_report.json](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench/baseline_report.json:1)
- [backtest_diagnostics_20260418.md](C:/Users/khoua/OneDrive/Desktop/TCNs/artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_workbench/backtest_diagnostics_20260418.md:1)
- [us100_session_refined_rerun_20260415_frontier_workbench.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/us100_session_refined_rerun_20260415_frontier_workbench.md:1)
- [us100_session_refined_rerun_20260415_frontier_workbench_compare_20260418.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/us100_session_refined_rerun_20260415_frontier_workbench_compare_20260418.md:1)

## Main Results

### Policy-level isolated validation before the full rerun

Before the canonical rerun, we tested the targeted Asia-open continuation control directly on the prior rerun trade path.

That isolated evaluation showed:

- `long_continuation` improved from `60` trades at `-0.022222R` expectancy to `28` trades at `0.428571R`
- estimated return improved from `23.9856%` to `28.6035%`
- estimated max drawdown improved from `2.0266%` to `1.2295%`
- estimated days to pass improved from `47` to `32`

This confirmed the direction of the manager change before rerunning the canonical artifact.

### Final canonical frontier-managed rerun

The refreshed canonical workbench artifact finished at:

- trades: `180`
- win rate: `0.505556`
- expectancy: `0.348148R`
- total return: `23.8254%`
- max drawdown: `2.2716%`
- days to pass: `24`
- pass probability 30: `0.552`
- pass probability 60: `0.968`
- pass probability 90: `1.000`
- worst month return: `-0.154066%`

### Comparison vs prior frontier rerun (`2026-04-17`)

Relative to the prior canonical frontier rerun:

- trades decreased from `207` to `180`
- win rate improved from `0.483092` to `0.505556`
- expectancy improved from `0.288245R` to `0.348148R`
- return was nearly flat: `23.9856%` to `23.8254%`
- max drawdown worsened slightly: `2.0266%` to `2.2716%`
- days to pass improved sharply: `47` to `24`
- pass probability 30 improved from `0.402` to `0.552`
- pass probability 60 improved from `0.946` to `0.968`
- worst month improved from `-0.698875%` to `-0.154066%`

## Slice-Level Findings

### `long_continuation / asia / opening_0_20`

This remained the main continuation weakness, but the rerun materially reduced its drag:

- prior rerun: `50` trades, `-0.146667R`, total `-7.333333R`
- current rerun: `21` trades, `0.015873R`, total `0.333333R`

So the Asia-open long-continuation bleed was not fully eliminated, but it was compressed from meaningfully negative to roughly flat.

### `short_continuation / asia / opening_0_20`

This slice did not emerge as the next urgent problem:

- prior rerun: `13` trades, `0.230769R`, total `3.000000R`
- current rerun: `12` trades, `0.333333R`, total `4.000000R`

### `short_continuation / asia / build_20_40`

This slice remained healthy:

- prior rerun: `22` trades, `0.212121R`, total `4.666667R`
- current rerun: `23` trades, `0.391304R`, total `9.000000R`

## Practical Outcome

At the end of this session:

- continuation remained enabled
- Asia-open long-continuation bleed was materially reduced
- the canonical frontier workbench artifact was fully regenerated
- the refreshed frontier-managed path is faster to pass and more selective
- the next bottleneck is no longer `short_continuation / asia / opening_0_20`

## Recommended Next Step

The next high-value step should be utility-ranking calibration rather than another immediate `short_continuation / asia / opening_0_20` cleanup pass.

If another narrow policy pass is desired before calibration, the only slice that still clearly justifies it is:

- `long_continuation / asia / opening_0_20`
