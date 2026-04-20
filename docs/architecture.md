# Architecture

## Overview

This repository is a small, single-purpose market-data preparation pipeline.

The codebase has one executable Python script, `scripts/prepare_market_data.py`, and a data workspace under `data/`. The script validates raw OHLC files, segments the minute stream into contiguous sessions, classifies data gaps, and writes organized outputs for feature engineering and ML training.

At a high level:

1. Raw CSV files are expected in `data/raw/`.
2. The script treats `1m` as the canonical source.
3. Higher intraday timeframes are validated against strict resamples of `1m`.
4. The `1m` stream is segmented wherever continuity breaks.
5. Clean minute bars, strict ML bars, and metadata reports are written back into `data/`.

## Repository Layout

```text
TCNs/
+-- data/
|   +-- clean/
|   |   +-- us100_1m_clean.csv.gz
|   |   \-- us500_1m_clean.csv.gz
|   +-- strict_ml/
|   |   +-- us100_1m_strict_ml.csv.gz
|   |   \-- us500_1m_strict_ml.csv.gz
|   +-- metadata/
|   |   +-- data_quality_report.json
|   |   +-- model_readiness.md
|   |   +-- gap_events.csv
|   |   +-- unexpected_gaps.csv
|   |   +-- contiguous_segments.csv
|   |   +-- us100_session.csv
|   |   \-- us500_session.csv
|   +-- raw/
|   |   \-- <input CSVs go here>
|   \-- README.md
+-- docs/
|   \-- architecture.md
\-- scripts/
    \-- prepare_market_data.py
```

## Runtime Architecture

### Entry Point

`scripts/prepare_market_data.py` is both the CLI and the full pipeline implementation.

- `main()` parses CLI arguments and resolves paths.
- `build_report()` orchestrates the full workflow and writes all outputs.

Default paths:

- `--data-dir`: `data/raw`
- `--report-dir`: `data/metadata`
- `--prepared-dir`: `data`

### Processing Stages

The pipeline is organized as a sequence of deterministic stages:

1. Load raw CSVs
   - `load_ohlc_csv()`
   - Enforces the expected schema: `timestamp`, `open`, `high`, `low`, `close`
   - Parses timestamps as UTC and coerces numeric columns

2. Structural validation
   - `validate_frame()`
   - Checks duplicates, parse failures, null numeric cells, non-positive values, OHLC consistency, and timestamp ordering

3. Cross-timeframe verification
   - `frame_to_indexed()`
   - `compare_frames()`
   - `build_report()`
   - Verifies `5m`, `15m`, `1h`, and `4h` files against strict `1m` resamples
   - Verifies `1d` as a calendar-day aggregation of `1m`

4. Gap classification and session segmentation
   - `classify_gap()`
   - `build_segments()`
   - `build_segment_record()`
   - Splits the minute stream on gaps greater than 60 seconds
   - Labels gaps as:
     - `routine_session_close`
     - `weekend_session_close`
     - `holiday_or_early_close`
     - `unexpected_intraday_gap`

5. Strict ML eligibility logic
   - `infer_expected_session_rows()`
   - `classify_strict_ml_exclusion()`
   - Marks each session as full-length or partial
   - Excludes sessions that begin the dataset or follow unexpected gaps

6. Bar-level export assembly
   - `build_prepared_bars()`
   - Joins per-bar OHLC rows with session metadata and continuity features

7. Reporting and artifact writing
   - `write_markdown_report()`
   - `build_report()`
   - Writes machine-readable and human-readable readiness outputs

## Core Data Model

### Canonical Dataset

The architecture is centered on the `1m` timeframe.

`1m` is treated as the source of truth because:

- it preserves the highest available temporal resolution
- it can be resampled into higher intraday bars deterministically
- continuity and gap logic are easiest to define at the minute level

All downstream clean and strict ML datasets are derived from this minute stream.

### Session Model

The pipeline defines a session as a contiguous run of minute bars with no gap greater than one minute.

Each session receives:

- `segment_id`
- start and end timestamps
- row count
- previous gap category
- previous gap duration
- full-length flag
- strict-ML eligibility flag

This session model is the main architectural boundary for feature engineering and modeling. Lookbacks and targets should stay inside one `segment_id`.

### Output Layers

The repository produces three output layers with distinct roles:

1. `data/clean/`
   - Canonical working set for feature engineering
   - Contains all bars plus continuity metadata

2. `data/strict_ml/`
   - Conservative training set
   - Contains only bars from full-length eligible sessions

3. `data/metadata/`
   - Diagnostics, audit trails, and readiness reports
   - Used to explain exclusions and inspect gap behavior

## Key Functions

### Ingestion and Validation

- `load_ohlc_csv(path)`
  - Reads a CSV and normalizes types

- `validate_frame(frame)`
  - Produces frame-level quality metrics

- `compare_frames(target, reference)`
  - Compares existing higher-timeframe files to `1m`-derived references

### Gap and Segment Logic

- `classify_gap(previous_ts, next_ts, gap_seconds)`
  - Encodes domain rules for expected versus unexpected breaks

- `build_segments(symbol, base_frame)`
  - Converts raw `1m` bars into gap events, session summaries, and segment-tagged minute rows

- `build_segment_record(...)`
  - Produces one session summary record

### ML-Ready Export Logic

- `infer_expected_session_rows(segment_rows)`
  - Uses the modal session length as the expected full session size

- `classify_strict_ml_exclusion(previous_gap_category, is_full_length_segment)`
  - Explains why a session is excluded from the strict set

- `build_prepared_bars(symbol, segmented, segment_frame)`
  - Builds the final per-bar export schema

### Reporting

- `write_markdown_report(report_path, report)`
  - Writes the human-readable summary

- `build_report(data_dir, report_dir, prepared_dir)`
  - Orchestrates the end-to-end pipeline and writes every artifact

## Output Contracts

### `data/clean/*.csv.gz`

These are the main feature-engineering inputs.

Important columns:

- `symbol`
- `timestamp`
- `open`, `high`, `low`, `close`
- `session_date_utc`
- `segment_id`
- `bar_index_in_segment`
- `bars_remaining_in_segment`
- `segment_rows`
- `expected_session_rows`
- `previous_gap_category`
- `previous_gap_minutes`
- `is_full_length_segment`
- `follows_unexpected_gap`
- `eligible_for_strict_ml`

### `data/strict_ml/*.csv.gz`

These files are a filtered subset of `data/clean/`.

They contain only rows where:

- the session is full-length
- the session does not start the dataset
- the session does not follow an `unexpected_intraday_gap`

### `data/metadata/*`

Important files:

- `data_quality_report.json`
  - Full machine-readable readiness report

- `model_readiness.md`
  - Human-readable summary

- `gap_events.csv`
  - All detected gaps

- `unexpected_gaps.csv`
  - Only the gaps that should be considered anomalous

- `contiguous_segments.csv`
  - Cross-symbol session inventory

- `*_session.csv`
  - Per-symbol session summaries with strict-ML eligibility decisions

## Design Decisions

### Why a Single Script

The current codebase is intentionally compact. All logic lives in one script because:

- the pipeline has a single end-to-end responsibility
- the function boundaries are already clear
- operational simplicity is more valuable than package decomposition at this size

If the repository grows, the natural split would be:

- `io.py`
- `validation.py`
- `segmentation.py`
- `exports.py`
- `reporting.py`

### Why `1m` Is Canonical

Using `1m` as the source of truth avoids ambiguity:

- higher timeframes can be regenerated
- continuity rules are easiest to enforce
- feature engineering can be done once and resampled later if needed

### Why Strict ML Is Separate From Clean

Feature research and production training have different requirements.

- `clean/` is for exploration and flexible feature creation
- `strict_ml/` is for conservative training without continuity leaks

This separation keeps analysis broad while keeping training defensible.

## Operational Notes

- The script expects raw CSV inputs in `data/raw/`.
- `data/raw/` is currently empty because the old raw files were intentionally removed after preparation.
- Re-running the pipeline requires repopulating `data/raw/` with the expected symbol and timeframe CSVs.
- The repository currently has no automated test suite. Verification is done by running the pipeline and checking the generated metadata outputs.

## Recommended Next Step

Build feature-engineering code against `data/clean/` first, then promote only segment-safe features and targets into workflows that consume `data/strict_ml/`.
