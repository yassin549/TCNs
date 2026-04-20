# Data Layout

Use `clean/` as the starting point for feature engineering and `strict_ml/` for direct model training.

## Directories

- `clean/`: Canonical minute bars with session and continuity metadata on every row.
- `strict_ml/`: Conservative subset of `clean/` that keeps only full-length eligible sessions.
- `metadata/`: Session summaries, gap diagnostics, and readiness reports.
- `raw/`: Reserved for future raw imports. It is intentionally empty right now.

## Primary Files

- `clean/us100_1m_clean.csv.gz`
- `clean/us500_1m_clean.csv.gz`
- `strict_ml/us100_1m_strict_ml.csv.gz`
- `strict_ml/us500_1m_strict_ml.csv.gz`

## Key Columns In `clean/`

- `segment_id`: Do not let rolling windows cross this boundary.
- `session_date_utc`: Session label for grouping and daily feature rolls.
- `bar_index_in_segment`: Position of the bar inside the contiguous session.
- `bars_remaining_in_segment`: Useful for horizon filtering near session end.
- `is_full_length_segment`: Flags sessions shorter than the expected full session length.
- `follows_unexpected_gap`: Marks sessions that start after a non-routine data gap.
- `eligible_for_strict_ml`: `True` only for bars already accepted into `strict_ml/`.

## Recommended Workflow

1. Build exploratory and feature datasets from `clean/`.
2. Filter to `eligible_for_strict_ml == True` or use `strict_ml/` directly for training.
3. Keep every lookback window and target horizon inside one `segment_id`.
4. Use `metadata/unexpected_gaps.csv` and `metadata/*_session.csv` when you need to audit exclusions.
