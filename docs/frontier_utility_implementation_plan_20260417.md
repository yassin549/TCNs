# Frontier Utility Implementation Plan

Date: `2026-04-17`

## Objective

Re-architect the repo from a setup-classification pipeline with a post-hoc manager into a prop-firm utility system that:

- trains for challenge utility instead of mainly setup classification
- feeds account state directly into model decisions
- allocates daily risk jointly across candidate trades
- keeps continuation experts disabled until they prove additive utility after slot competition
- evaluates all frontier changes through full integrated replay, not only recorded-trade reapplication

## Target End State

The target system has five layers:

1. Feature and label generation
2. Utility-aware sequence model
3. Candidate-generation and expert routing
4. Constrained daily allocator
5. Full integrated replay and reporting

At the end of this plan, the repo should be able to answer:

- which trades increase pass probability the most from the current account state
- which subset of same-day trades should actually be taken
- whether continuation setups add net utility after competing for limited slots
- whether a new artifact is better under true replay, not only path re-filtering

## Current Constraints

### Source constraints already visible in repo

- `specialist_tcn_pipeline.py` is still wrapper-based and not fully text-auditable.
- `frontier_prop_manager.py` is the strongest source-level policy implementation.
- `frontier_research_workbench.py` already provides an orchestration entry point.
- `learned_moe_tcn_pipeline.py` and `learned_moe_pipeline.py` are auditable, but their current artifacts are not competitive.

### What this means for implementation

- the first production path should extend the specialist frontier workflow, not replace it outright with MoE
- new utility-aware logic should be introduced in source-level modules that can be fully controlled
- full replay must become the acceptance path before larger model experiments are trusted

## Workstreams

## Workstream 1. Utility-Centric Data Model

Goal:

- change the dataset from "setup present or not" into "trade utility from this state"

### Deliverables

1. A new dataset schema version with:
   - setup labels preserved as auxiliary targets
   - trade outcome fields
   - account-state fields
   - utility labels
2. A dataset build command for utility training
3. Schema and label reports written to artifact output

### New columns to add

Market-state additions:

- `session_range_expansion_state`
- `prior_session_imbalance`
- `opening_drive_strength`
- `volatility_regime_percentile`
- `intraday_trend_persistence`
- `intraday_chop_score`

Account-state additions:

- `account_return_pct_to_date`
- `account_drawdown_pct`
- `account_distance_to_target_pct`
- `account_profitable_days_so_far`
- `account_profitable_days_remaining`
- `account_days_elapsed`
- `day_pnl_pct_so_far`
- `day_loss_budget_remaining_pct`
- `total_drawdown_budget_remaining_pct`
- `trades_taken_today`
- `trade_slots_remaining_today`
- `last_trade_pnl_r`
- `win_streak`
- `loss_streak`

Utility-label additions:

- `trade_realized_pnl_r`
- `trade_realized_pnl_cash`
- `trade_passed`
- `trade_days_to_pass_if_taken`
- `delta_pass_prob_30`
- `delta_pass_prob_60`
- `delta_profitable_day_hit_prob`
- `delta_drawdown_risk`
- `trade_challenge_utility`

### File scope

Primary files:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:740)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)

Likely new files:

- `scripts/frontier_utility_dataset.py`
- `scripts/frontier_account_state.py`

### Implementation steps

1. Create a canonical account-state simulator that can walk a historical path and emit account-state features per candidate bar.
2. Build a utility-label generator that compares:
   - no trade
   - taking the trade
   under the same account state.
3. Preserve current setup labels for compatibility and interpretability.
4. Write `dataset_schema.json` and `label_report.json` for the new utility dataset.

### Acceptance criteria

- a new utility dataset can be built from the current feature export
- every utility row is generated with no future leakage beyond the allowed trade outcome horizon
- the dataset contains both market state and account state
- schema docs clearly distinguish auxiliary setup labels from primary utility targets

## Workstream 2. Utility-Aware Model Training

Goal:

- move the learning objective from setup probability toward challenge utility ranking

### Model strategy

Do not throw away the current specialist framing immediately. Use a hybrid objective:

- auxiliary heads:
  - `long_reversal`
  - `long_continuation`
  - `short_reversal`
  - `short_continuation`
- primary heads:
  - expected utility
  - pass-probability delta
  - profitable-day delta
  - drawdown-risk penalty

This preserves structure while making the optimization target prop-firm relevant.

### Deliverables

1. A utility-aware training module
2. A training summary that reports both setup metrics and challenge-utility metrics
3. A scorer that emits candidate-level utility predictions, not only probabilities

### File scope

Best path:

- add a new source-level training path instead of overloading the current wrapper

Likely new files:

- `scripts/frontier_utility_model.py`
- `scripts/frontier_utility_pipeline.py`

Reference files:

- [scripts/learned_moe_tcn_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/learned_moe_tcn_pipeline.py:145)
- [scripts/learned_moe_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/learned_moe_pipeline.py:145)

### Implementation steps

1. Start from the TCN sequence encoder path, not the pointwise MoE path.
2. Expand context inputs to include account-state tensors.
3. Replace the primary loss with a weighted objective combining:
   - setup BCE loss
   - utility regression loss
   - pass-probability delta regression loss
   - profitable-day delta regression loss
   - ranking loss across same-day candidates
4. Emit candidate-level outputs:
   - `predicted_setup_probs`
   - `predicted_trade_utility`
   - `predicted_delta_pass_prob_30`
   - `predicted_delta_pass_prob_60`
   - `predicted_delta_profitable_day_prob`
   - `predicted_drawdown_penalty`

### Recommended training objective

Primary score:

```text
predicted_frontier_score =
  w1 * predicted_trade_utility
  + w2 * predicted_delta_pass_prob_30
  + w3 * predicted_delta_pass_prob_60
  + w4 * predicted_delta_profitable_day_prob
  - w5 * predicted_drawdown_penalty
```

Auxiliary regularization:

- keep setup classification heads for expert semantics
- keep calibration reports for auditability

### Acceptance criteria

- the model can train end to end on the new dataset
- the scorer emits utility-centric predictions
- training summaries rank checkpoints primarily by challenge utility on validation, not by mean AP alone

## Workstream 3. Account-State Integration

Goal:

- make account state part of the decision function, not only a manager overlay

### Deliverables

1. A reusable account-state engine
2. Shared account-state schema across dataset generation, model scoring, allocator, and replay
3. Account-state-aware analysis reports

### File scope

Likely new file:

- `scripts/frontier_account_state.py`

Likely touched files:

- `scripts/frontier_prop_manager.py`
- `scripts/frontier_research_workbench.py`
- `scripts/generate_baseline_report.py`

### Implementation steps

1. Define a canonical `AccountState` dataclass used across all frontier modules.
2. Support deterministic updates after each accepted trade and after each day close.
3. Provide serialization helpers for:
   - dataset generation
   - replay summaries
   - debug traces
4. Update reporting to show account-state-conditioned diagnostics:
   - utility by drawdown bucket
   - utility by distance-to-target bucket
   - utility by profitable-days-remaining bucket

### Acceptance criteria

- account state is computed once and reused everywhere
- there is no mismatch between dataset-time account state and replay-time account state
- analysis reports can slice model utility by account state

## Workstream 4. Constrained Daily Allocation

Goal:

- replace independent trade filtering with joint daily subset selection

### Design requirement

The allocator should choose `0..N` trades for a day under constraints, not simply accept each trade independently when it clears a threshold.

### Deliverables

1. A candidate-ranking layer
2. A same-day constrained allocator
3. Allocator diagnostics explaining why trades were taken or rejected

### Constraints to support

- `max_trades_per_day`
- `max_daily_loss_pct`
- `max_total_drawdown_pct`
- `max_loss_per_trade_pct`
- concentration limits by setup
- optional concentration limits by session and phase
- reserve capacity for later higher-value opportunities

### File scope

Primary file to evolve:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:498)

Likely new file:

- `scripts/frontier_allocator.py`

### Implementation steps

1. Define a candidate object per signal containing:
   - timestamp
   - setup
   - predicted frontier score
   - required risk
   - expected pass contribution
   - expected profitable-day contribution
   - expected drawdown penalty
2. Group candidates by `session_date_utc`.
3. Replace row-wise threshold accept/reject with:
   - rank all daily candidates
   - allocate a subset under constraints
4. Start with a simple greedy constrained allocator:
   - sort by frontier score adjusted for marginal risk
   - accept only if budgets remain
5. Later extend to a knapsack-style or beam-search allocator if greedy behavior is insufficient.

### Diagnostics to emit

- `rejected_by_allocator_budget`
- `rejected_by_allocator_slot_competition`
- `rejected_by_allocator_setup_concentration`
- `rejected_by_allocator_low_marginal_utility`
- `accepted_rank_within_day`

### Acceptance criteria

- the allocator sees all same-day candidates before final selection
- continuation experts compete for slots against reversal experts
- allocator decisions are reproducible and logged
- same-day slot competition is visible in output artifacts

## Workstream 5. Continuation Expert Governance

Goal:

- keep continuation disabled by default until it proves additive utility after daily slot competition

### Policy rule

Continuation experts remain disabled in the mainline policy unless they improve the frontier scorecard under full replay after allocator competition.

### Required scorecard for continuation re-entry

A continuation family can only be re-enabled if it improves at least:

- rolling-start pass rate
- median days to pass or actual days to pass
- profitable-day accumulation

And does not worsen:

- max drawdown
- drawdown cluster severity
- payout smoothness on funded-mode evaluation

### File scope

Current default behavior starts here:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:14)

### Implementation steps

1. Preserve `DEFAULT_DISABLED_SETUPS` for both continuation experts.
2. Add a re-qualification report that compares:
   - reversal-only baseline
   - reversal-plus-selected-continuation candidate set
3. Evaluate continuation after allocator competition, not before.
4. Record explicit enablement justification in `manager_policy.json`.

### Acceptance criteria

- continuation stays off by default
- any re-enable decision is backed by replay metrics and written into artifact metadata
- continuation never re-enters based only on classification lift or isolated setup expectancy

## Workstream 6. Full Integrated Replay

Goal:

- make full replay the single source of truth for frontier evaluation

### Why this is required

Recorded-trade reapplication is useful for fast estimation, but it misses:

- skipped-trade effects on future cooldowns
- changed balance path effects on future sizing
- daily slot reservation effects
- ordering interactions among same-day candidates

### Deliverables

1. A full replay engine that consumes raw scored candidates
2. A fast estimate mode and a strict acceptance mode
3. Replay summaries and trade logs aligned with the existing reporting stack

### File scope

Likely new file:

- `scripts/frontier_replay.py`

Likely touched files:

- `scripts/frontier_research_workbench.py`
- `scripts/frontier_prop_manager.py`
- `scripts/generate_baseline_report.py`

### Implementation steps

1. Define an input contract for replay:
   - candidate timestamps
   - predicted utility outputs
   - setup metadata
   - simulated trade outcomes
2. Build a deterministic replay loop:
   - update account state
   - build candidate set for the current day
   - run allocator
   - simulate accepted trades
   - update budgets and account state
3. Emit:
   - replayed trade log
   - replay summary JSON
   - markdown summary
   - baseline report
4. Keep recorded-trade reapplication only as:
   - `estimate-policy`
   not as acceptance-grade evaluation

### Acceptance criteria

- all new frontier artifacts are accepted only if they pass the full replay path
- the workbench exposes a strict replay command
- reports clearly label `estimate` versus `full_replay`

## Workstream 7. Research Workbench Upgrade

Goal:

- make the new architecture runnable from one reproducible workflow

### Deliverables

1. New commands in `frontier_research_workbench.py`
2. Artifact and report conventions for utility-model runs
3. A compare command centered on challenge utility deltas

### Command surface to add

```powershell
python -B scripts\frontier_research_workbench.py build-utility-dataset ...
python -B scripts\frontier_research_workbench.py train-utility-model ...
python -B scripts\frontier_research_workbench.py score-candidates ...
python -B scripts\frontier_research_workbench.py replay-frontier ...
python -B scripts\frontier_research_workbench.py compare-frontier-runs ...
python -B scripts\frontier_research_workbench.py full-utility-cycle ...
```

### Full-cycle contract

`full-utility-cycle` should orchestrate:

1. utility dataset build
2. optional regime enrichment
3. utility-model train
4. validation analysis
5. candidate scoring
6. full integrated replay
7. baseline report generation
8. comparison against prior frontier baselines

### Acceptance criteria

- a single command can run the new frontier cycle
- artifacts are reproducible and named consistently
- comparison reports focus on prop utility metrics first

## Rollout Phases

## Phase 1. Foundations

Scope:

- account-state engine
- utility dataset builder
- schema docs

Files:

- `scripts/frontier_account_state.py`
- `scripts/frontier_utility_dataset.py`
- `scripts/frontier_research_workbench.py`

Exit criteria:

- utility dataset builds successfully
- account-state features are present and validated

## Phase 2. Utility Scoring

Scope:

- utility-aware training path
- candidate scoring outputs

Files:

- `scripts/frontier_utility_model.py`
- `scripts/frontier_utility_pipeline.py`

Exit criteria:

- validation can rank checkpoints by challenge utility metrics
- candidate scorer emits frontier scores

## Phase 3. Allocator and Replay

Scope:

- daily constrained allocator
- full replay engine

Files:

- `scripts/frontier_allocator.py`
- `scripts/frontier_replay.py`
- `scripts/frontier_prop_manager.py`

Exit criteria:

- replay path works end to end
- allocator decisions are logged and reproducible

## Phase 4. Governance and Acceptance

Scope:

- continuation re-entry rules
- estimate versus replay labeling
- new workbench full cycle

Files:

- `scripts/frontier_research_workbench.py`
- `scripts/generate_baseline_report.py`
- `docs/*`

Exit criteria:

- continuation stays disabled unless replay proves additive utility
- workbench produces acceptance-grade frontier artifacts

## Recommended File Map

### Keep and evolve

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)
- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)
- [scripts/generate_baseline_report.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/generate_baseline_report.py:1)
- [scripts/prop_firm_rules.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/prop_firm_rules.py:1)

### Add

- `scripts/frontier_account_state.py`
- `scripts/frontier_utility_dataset.py`
- `scripts/frontier_utility_model.py`
- `scripts/frontier_utility_pipeline.py`
- `scripts/frontier_allocator.py`
- `scripts/frontier_replay.py`

### Leave unchanged initially

- `scripts/learned_moe_pipeline.py`
- `scripts/learned_moe_tcn_pipeline.py`

Those two files are useful references but should not be the first production target.

## Acceptance Scorecard

All major changes should be judged primarily on:

- rolling-start pass rate
- bootstrap pass probability at `30`, `60`, `90`
- actual days to pass
- median days to pass
- profitable days accumulated
- positive day rate
- max drawdown
- loss-cluster severity
- funded-mode payout smoothness

And only secondarily on:

- mean AP
- ROC AUC
- raw trade count
- isolated setup precision

## Risks

### Risk 1. Label leakage through account-state simulation

Mitigation:

- generate account state from only prior realized path information
- freeze the trade outcome horizon for utility labels

### Risk 2. Too many simultaneous architecture changes

Mitigation:

- ship in phases
- keep specialist framing as the initial scaffold
- preserve old reports for comparison

### Risk 3. Allocator instability

Mitigation:

- begin with deterministic greedy allocation
- add richer search only after stable baselines exist

### Risk 4. Continuation overfitting to isolated slices

Mitigation:

- continuation is judged only after slot competition and full replay

### Risk 5. Replay becoming too slow for research iteration

Mitigation:

- keep a cheap estimate path for research triage
- reserve full replay for acceptance and milestone comparisons

## Definition Of Done

Done means:

- the primary training target is challenge utility, not only setup classification
- account state is part of model input, allocator input, and replay state
- trade selection is performed as constrained daily allocation
- continuation experts are disabled by default and governed by replay-based re-entry rules
- frontier evaluation requires full integrated replay for acceptance
- the workbench can run the new utility cycle reproducibly from one command

## Immediate Next Build Order

1. Implement `frontier_account_state.py`.
2. Implement `frontier_utility_dataset.py`.
3. Add `build-utility-dataset` to the workbench.
4. Implement `frontier_utility_model.py` and a minimal scorer.
5. Implement `frontier_allocator.py`.
6. Implement `frontier_replay.py`.
7. Upgrade reports and comparison tooling.
8. Run a smoke `full-utility-cycle`.
9. Run a full replay comparison against the current frontier baseline.
