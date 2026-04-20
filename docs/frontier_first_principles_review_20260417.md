# Frontier First-Principles Review

Date: `2026-04-17`

## Executive View

The current repo is not bottlenecked by "having no predictive signal." It is bottlenecked by a mismatch between:

- what the models are trained to predict
- how the backtester converts those predictions into trades
- what a prop-firm account actually rewards

The best checked-in result is still the specialist-TCN line, and even there the largest measured gain comes from stricter manager logic, not from a stronger base model.

The key evidence is already in the artifacts:

- latest baseline: `453` trades, `10.3396%` return, `4.7929%` max DD, pass in `76` days
- frontier-managed path: `162` trades, `14.1709%` return, `3.3916%` max DD, pass in `57` days

That means the system improves by trading much less and allocating risk more selectively. A frontier prop model in this repo should therefore be designed as a challenge-utility optimizer, not as a generic signal maximizer.

## What The Current Architecture Really Is

### 1. The profitable path is mostly a specialist classifier plus a policy layer

The documented specialist design is four setup-specific TCNs:

- `long_reversal`
- `long_continuation`
- `short_reversal`
- `short_continuation`

See:

- [docs/specialist_tcn_design.md](C:/Users/khoua/OneDrive/Desktop/TCNs/docs/specialist_tcn_design.md)

The active source-level policy layer now lives in:

- [scripts/frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:18)

Important source facts:

- continuation experts are disabled by default in `DEFAULT_DISABLED_SETUPS`
- path-aware context stats are computed in `compute_context_path_stats`
- the manager builds context thresholds in `build_policy_payload`
- live trade filtering and risk sizing happen in `apply_frontier_policy`

This is the strongest part of the current stack.

### 2. The auditable learned-MoE paths are still far from viable

The auditable MoE pipelines are:

- [scripts/learned_moe_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/learned_moe_pipeline.py:145)
- [scripts/learned_moe_tcn_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/learned_moe_tcn_pipeline.py:145)

The TCN-MoE smoke artifact is materially negative:

- test trades: `7`
- test expectancy: `-1.077901R`
- test return: `-4.3605%`
- bootstrap pass probability: `0.0`

This is not a parameter-tuning miss. It indicates the training objective and backtest mapping are not yet aligned with executable edge.

### 3. The repo optimizes too late for prop-firm utility

FundedHive rules are encoded cleanly in:

- [scripts/prop_firm_rules.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/prop_firm_rules.py:24)

But in the MoE pipelines, the model is still trained first on setup/event labels and only later tuned through a validation backtest policy search. That sequence is too weak. The system needs challenge utility to shape the modeling target earlier.

## Main Findings From The Existing Results

### 1. The manager is the current edge bottleneck

Measured artifact comparison:

- baseline: `453` trades, expectancy `0.089036R`
- frontier-managed: `162` trades, expectancy `0.251029R`

The model already emits more candidate trades than should ever be taken. The current frontier gain comes from refusing mediocre trades.

Implication:

- do not prioritize "make the model fire more often"
- prioritize "rank candidate trades better and abstain more aggressively"

### 2. The continuation specialists are structurally suspect under prop constraints

The docs show continuation setups can look good on classification-style slices while still being weak or negative on realized challenge utility. That is exactly what happens when labels capture local event success but execution reality punishes path shape, cost drag, and slot usage.

Implication:

- continuation should not be treated as a core pillar until it is positive on recorded challenge utility after slot competition
- the repo is currently right to default them off

### 3. The system still uses a thin state representation for account lifecycle

The frontier manager adds post-win tightening, drawdown controls, and recovery mode, but account state is still a shallow overlay applied after scoring. The base models do not directly condition on:

- distance to pass
- profitable-days remaining
- account drawdown state
- daily loss budget remaining
- trade-slot scarcity for the current day

That is a structural miss for prop trading. The correct action for the same market state is different when the account is up `9.4%` with two profitable days versus down `2.3%` after two losses.

### 4. The label design is executable, but still not aligned enough with account utility

The specialist design labels a bar positive if target hits before stop inside a bounded horizon. That is reasonable for setup discovery, but it still collapses several very different cases into the same target:

- a fast clean move early in the day
- a noisy move that consumes a scarce trade slot
- a win that comes after a long give-back sequence
- a win in a state where the account should have abstained

For prop firms, these are not equivalent.

### 5. The backtest architecture likely overstates deployable confidence

The frontier manager evaluation is applied to recorded trades, not a full raw-market replay. That is useful for ranking manager ideas, but it is not a sufficient final truth surface. It can miss:

- interactions between abstention and later trade availability
- queueing effects when the first skipped trade changes cooldown state
- altered balance trajectory effects on later sizing and lockouts

This does not invalidate the result. It means the repo needs a full integrated replay path before claiming frontier performance.

## First-Principles Improvement Direction

The model should be redesigned around the real objective:

`maximize expected discounted prop-firm utility subject to strict risk-of-ruin constraints`

In practice that means the system should optimize for:

- pass probability within `30/60/90` trading-day horizons
- median days to pass
- profitable-day accumulation rate
- probability of ruin or severe path degradation
- payout stability after passing

Not for:

- raw classifier AP
- raw label precision
- total trade count
- gross return on a single realized path

## Highest-Leverage Changes

### 1. Move from event classification to utility ranking

Current target:

- "Does setup X hit target before stop?"

Needed target:

- "What is the expected challenge utility of taking this trade now, given market state and account state?"

Recommended implementation:

- keep the current setup labels as auxiliary heads
- add a primary head for expected trade utility under account-state conditioning
- define the utility target from realized trade outcomes with penalties for:
  - consuming a trade slot
  - increasing drawdown pressure
  - failing to improve profitable-day odds
  - slowing pass time

This should replace the current setup-first, policy-later stack as the main training objective.

### 2. Train on account-state augmented observations

Add account-state features directly to model inputs:

- current account return to date
- drawdown from peak
- profitable days accumulated
- profitable days still required
- daily PnL so far
- daily loss budget remaining
- total drawdown budget remaining
- trades used today
- days elapsed since account start
- gap to target in percent

Without this, the model can only learn market edge, not whether the edge is worth deploying now.

### 3. Replace flat labels with horizon-aware path labels

A frontier prop model should distinguish:

- pass-accelerating wins
- low-value wins
- risk-damaging losses
- harmless small losses

Recommended label family:

- `trade_ev_r`
- `trade_ev_cash`
- `delta_pass_prob_30d`
- `delta_pass_prob_60d`
- `delta_profitable_day_prob`
- `delta_ruin_prob`

Train the model to predict these deltas or a weighted combination of them.

### 4. Make the manager a constrained allocator, not a post-filter

Right now the manager mostly filters and rescales. The next version should solve a daily allocation problem:

- choose the best `0..N` trades for the day
- allocate risk across them jointly
- reserve capacity for later higher-value contexts

That means scoring candidates relative to one another, not independently.

A practical approach:

- generate all candidate trades for a day
- assign each a challenge-utility score
- choose trades with a knapsack-style allocator under:
  - daily loss limit
  - total drawdown budget
  - max trades per day
  - regime concentration constraints

### 5. Rebuild continuation from scratch or drop it

Continuation should not be a default expert family until it shows additive utility after competition for slots.

Recommended standard:

- continuation earns inclusion only if it improves:
  - rolling-start pass rate
  - median days to pass
  - positive day rate
  - post-pass payout smoothness

If not, the frontier system should remain reversal-centric.

### 6. Add a true integrated market replay for frontier evaluation

The repo needs a single end-to-end backtest path where:

- model scores bars
- manager sees only currently available information
- skipped trades alter future cooldown and slot availability
- balance path feeds back into later decisions

This should become the only acceptance test for new frontier policies.

## Research Program That Is Actually Worth Running

### Phase 1. Tighten the current winning stack

- Keep specialist TCN as the working baseline.
- Make full replay the acceptance path for frontier policies.
- Add account-state features to the scorer and manager inputs.
- Promote context thresholds from static JSON artifacts to a trainable scoring layer.

Expected payoff:

- immediate improvement with limited architecture risk

### Phase 2. Build a contextual trade-value model

- Create a new dataset where each candidate bar is labeled with realized trade outcome and challenge-utility deltas.
- Train a sequence model to predict trade value directly, not only setup probability.
- Keep setup heads as regularizers so the model preserves interpretable structure.

Expected payoff:

- better ranking of scarce trade slots
- better pass speed and smoother path shape

### Phase 3. Build a daily allocation policy

- Score all same-day candidates
- choose a constrained subset jointly
- size positions from portfolio-level account utility instead of single-trade surplus only

Expected payoff:

- fewer path-damaging trade clusters
- better profitable-day efficiency
- better payout consistency after passing

### Phase 4. Extend from challenge passing to payout harvesting

Once passing is reliable, optimize funded-account behavior separately:

- lower tail-risk regime
- smaller but steadier daily target harvesting
- explicit payout-cycle utility
- anti-reset protection

Passing and payout farming are related but not identical problems.

## Concrete Repo Gaps To Address Next

1. The profitable specialist-TCN training path is not source-auditable from text in this repo.
2. Frontier evaluation still relies on trade-path reapplication rather than only full replay.
3. MoE training still optimizes mostly setup/event prediction instead of challenge utility.
4. Account-state is absent from model inputs.
5. There is no allocator that treats daily trade slots as scarce capital.
6. There is no post-pass funded-account objective.

## Recommended Immediate Build Order

1. Make a fully integrated replay path for the specialist frontier manager.
2. Add account-state features to the dataset and scoring path.
3. Train a direct challenge-utility head on top of the current specialist architecture.
4. Re-rank candidate trades by predicted utility instead of probability surplus alone.
5. Introduce daily subset selection under explicit budget constraints.
6. Only after that, revisit continuation experts or larger MoE architectures.

## Bottom Line

The current repo already proved an important point:

- the path to better prop performance is not more trades
- it is better abstention, better context ranking, and better path shaping

The next frontier leap will come from changing the learning target. The system should stop asking "is this setup present?" as the main question and start asking:

`is taking this trade now the highest-value action for passing and harvesting a prop account?`
