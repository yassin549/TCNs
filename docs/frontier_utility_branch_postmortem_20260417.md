# Frontier Utility Branch Postmortem

Date: `2026-04-17`

## Decision

The active baseline remains:

- `artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_default`

The new source-level utility branch is not promoted and should be treated as a failed research branch for now:

- `artifacts/frontier_utility/real_2h`

## Why The Utility Branch Is Not Being Promoted

The new branch improved supervised model-fit metrics, but failed on the actual prop-firm objective.

### Utility branch replay result

- trades: `3`
- trading days: `3`
- win rate: `0.333333`
- expectancy: `0.427181R`
- return: `0.3204%`
- max drawdown: `0.0%`
- passed challenge: `False`
- rolling-start pass rate: `0.0`

### Current frontier-default benchmark

- trades: `162`
- trading days: `68`
- win rate: `0.469136`
- expectancy: `0.251029R`
- return: `14.1709%`
- max drawdown: `3.3916%`
- passed challenge: `True`
- days to pass: `57`
- rolling-start pass rate: `0.117647`

## Diagnosis

The utility branch learned a more selective model, but the full decision stack is miscalibrated.

Main failure mode:

- severe over-abstention

Observed evidence:

- only `3` accepted trades
- `19,908` candidates rejected as `rejected_by_allocator_low_marginal_utility`
- accepted setup count:
  - `short_reversal: 3`

This means the current problem is not "the model cannot rank anything at all." The problem is:

- surrogate utility targets are not yet aligned with real replay utility
- score-to-acceptance calibration is too strict
- allocator acceptance is not tuned against pass-rate outcomes

## Operational Stance

1. Keep the current frontier-default system as the active benchmark and default comparison target.
2. Treat `frontier_utility/real_2h` as a research artifact only.
3. Do not use the utility branch for active benchmark replacement until it beats frontier-default on full replay.

## Required Fixes Before Trusting The Utility Branch

### 1. Fix calibration on validation replay

The next version must tune acceptance against replay outcomes, not only raw predicted frontier score.

Required change:

- add validation-time threshold search for:
  - minimum frontier score
  - daily trade count
  - concentration constraints
  - continuation enablement

Selection objective:

- rolling-start pass rate
- days to pass
- profitable days
- return with bounded drawdown

### 2. Replace surrogate utility deltas with replay-derived labels

Current Phase-1 delta targets are only scaffolding.

Required change:

- derive pass-probability and profitable-day deltas from replay-consistent account-state transitions

### 3. Relax allocator acceptance carefully

The allocator is correctly conservative in spirit, but currently too harsh in practice.

Required change:

- search a lower acceptance floor
- consider top-`k` per day even when absolute score is weak
- tune acceptance using validation replay rather than fixed defaults

### 4. Re-test continuation only after slot competition

Continuation should remain disabled by default.

Re-enable only if validation replay and test replay both improve:

- pass rate
- days to pass
- profitable-day accumulation

## Acceptance Gate For Any Future Promotion

The utility branch may only replace frontier-default if, on full replay, it improves or matches:

- pass outcome
- rolling-start pass rate
- days to pass
- profitable-day accumulation
- max drawdown

If it only improves supervised metrics but fails replay utility, it remains a research branch.

## Bottom Line

The utility architecture built on `2026-04-17` is a valid source-level research stack, but it is not yet a better trading system.

The repo should continue to treat frontier-default as the benchmark to beat, and the utility branch should be iterated only through replay-calibrated acceptance and replay-derived labels.
