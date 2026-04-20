# Specialist TCN Design

## Objective

Train four independent Temporal Convolutional Network classifiers on `US100` minute data:

- `long_reversal`
- `long_continuation`
- `short_reversal`
- `short_continuation`

Each model estimates the probability that its setup is present on the current bar. At decision time, the execution layer takes the highest calibrated probability that is above that model's validation-derived threshold.

## Why Specialist Models

Continuation and reversal setups live in different parts of the state space.

- Continuations want same-direction regime plus a recent counter-move.
- Reversals want opposite-direction regime plus range-extreme location.

One monolithic directional model tends to blur these cases together. Separate binary models let each TCN specialize on one micro-structure template.

## Label Philosophy

Labels are built from explicit, tradeable future events, not from arbitrary candle-color sequences.

### Event Layer

For each bar:

- Look ahead `30` bars within the same `segment_id`
- Require the move to complete in at least `5` bars
- Define the profit target as `1.25 x ATR(14)`
- Define the adverse move / stop barrier as `0.75 x ATR(14)`
- Long event: upside target is reached before downside stop
- Short event: downside target is reached before upside stop

This creates move labels that are:

- segment-safe
- horizon-bounded
- risk-defined
- closer to actual executable setups

### Setup Layer

The event direction is then split into specialist setup types:

- `long_reversal`
  - long event
  - prior `60`-bar trend score is negative enough
  - price sits in the lower portion of the session range

- `long_continuation`
  - long event
  - prior `60`-bar trend score is positive enough
  - recent `10`-bar pullback is negative
  - price sits in the upper half of the session range

- `short_reversal`
  - short event
  - prior `60`-bar trend score is positive enough
  - price sits in the upper portion of the session range

- `short_continuation`
  - short event
  - prior `60`-bar trend score is negative enough
  - recent `10`-bar pullback is positive
  - price sits in the lower half of the session range

Thresholds are set from dataset quantiles instead of fixed magic numbers.

Bars that satisfy zero or multiple setup rules are assigned to `none`.

## Features

The TCN receives a rolling `96`-bar window of normalized features:

- short-horizon returns
- candle body and wick structure
- true range and ATR percentage
- rolling volatility
- rolling range expansion
- trend scores over `10`, `30`, and `60` bars
- pullback scores over `5` and `10` bars
- session progress
- remaining session fraction
- current location inside the session range
- distance to session high and session low in ATR units
- return from session open in ATR units
- time-of-day cyclical features
- day-of-week cyclical features
- London local-time cyclical features
- New York local-time cyclical features
- explicit Asia / Europe / US session flags
- explicit session-open / session-close window flags
- explicit London-open / New York-open / London-New-York-overlap flags

This directly addresses the original requirement that the model must understand:

- day of week
- time of day
- the range currently being traded inside
- when London and New York are active
- when the session is opening or nearing close

## Training

Training is chronological and segment-safe.

- Input source: `data/features/us100_specialist_tcn_dataset.csv.gz`
- Split method: walk-forward by contiguous session order
- Loss: binary cross-entropy with class weighting
- Model family: dilated causal TCN with residual blocks
- Calibration: logistic calibration on validation logits
- Selection threshold: chosen from validation precision/recall trade-off

The script supports both:

- full training for research runs
- capped train/eval samples for quick smoke validation on CPU

## Execution Layer

The model layer only answers:

`Which setup is most likely right now?`

The execution layer must still enforce prop-firm constraints.

### Mandatory Live Filters

- Never trade without a stop loss placed at entry.
- Never let modeled trade risk exceed FundedHive's `3%` max loss per trade.
- If the server already enforces a news shutdown, keep that concern outside the model layer.
- Skip setups too close to session end.
- Hard-stop new risk once the FundedHive static daily loss budget (`5%`) is exhausted.
- Keep total realized drawdown above the FundedHive static account floor (`10%`).

### Practical Recommendation

For funded prop deployment, the model output should feed a stricter policy layer:

- choose best setup by calibrated probability
- require setup probability above that model's threshold
- require expected reward-to-risk above a fixed minimum
- treat `3%` as a hard ceiling, not a default operating size
- stop after the daily loss budget or after low-quality market regime detection
- track profitable-day count because FundedHive requires at least `3` profitable days to pass

## Commands

Build the labeled dataset:

```powershell
python -B scripts\specialist_tcn_pipeline.py build-dataset
```

Train the four specialist models:

```powershell
python -B scripts\specialist_tcn_pipeline.py train
```

Score a dataset and select the highest-probability setup:

```powershell
python -B scripts\specialist_tcn_pipeline.py score
```

Analyze scored performance by setup, session bucket, and session phase:

```powershell
python -B scripts\specialist_tcn_pipeline.py analyze
```

## Current US100 Label Snapshot

Using the current default label configuration on the strict `US100` set:

- eligible model rows: `1,432,803`
- `long_reversal`: `24,384`
- `long_continuation`: `9,120`
- `short_reversal`: `32,905`
- `short_continuation`: `8,062`

The median successful move reaches its target in `6` bars across all four setup types.
