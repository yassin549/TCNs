from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd


OHLC_COLUMNS = ["open", "high", "low", "close"]
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
CANONICAL_TIMEFRAME = "1m"
GAP_THRESHOLD_SECONDS = 60
STRICT_INTRADAY_RULES = {
    "5m": ("5min", 5),
    "15m": ("15min", 15),
    "1h": ("1h", 60),
    "4h": ("4h", 240),
}
STRICT_ML_ALLOWED_PREVIOUS_GAPS = {
    "routine_session_close",
    "weekend_session_close",
    "holiday_or_early_close",
}


@dataclass
class GapRecord:
    symbol: str
    previous_timestamp: str
    next_timestamp: str
    gap_minutes: float
    category: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate market OHLC data and prepare clean, ML-ready minute bars."
    )
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Directory containing the raw CSV files.",
    )
    parser.add_argument(
        "--report-dir",
        default="data/metadata",
        help="Directory where metadata and validation reports should be written.",
    )
    parser.add_argument(
        "--prepared-dir",
        default="data",
        help="Root directory where organized prepared artifacts should be written.",
    )
    return parser.parse_args()


def ensure_utc(timestamp: pd.Timestamp) -> str:
    return timestamp.tz_convert("UTC").isoformat().replace("+00:00", "Z")


def format_utc_series(timestamps: pd.Series) -> pd.Series:
    return timestamps.dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_ohlc_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    expected_columns = {"timestamp", *OHLC_COLUMNS}
    missing_columns = sorted(expected_columns.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"{path.name} is missing columns: {', '.join(missing_columns)}")

    cleaned = frame.loc[:, ["timestamp", *OHLC_COLUMNS]].copy()
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], utc=True, errors="coerce")
    for column in OHLC_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def validate_frame(frame: pd.DataFrame) -> Dict[str, object]:
    sorted_frame = frame.sort_values("timestamp").reset_index(drop=True)
    timestamp_deltas = sorted_frame["timestamp"].diff().dt.total_seconds()
    order_issues = int((timestamp_deltas.fillna(1) <= 0).sum())

    numeric = sorted_frame[OHLC_COLUMNS]
    row_min = numeric.min(axis=1)
    row_max = numeric.max(axis=1)
    ohlc_violations = int(
        ((sorted_frame["low"] > row_min) | (sorted_frame["high"] < row_max)).sum()
    )

    start = sorted_frame["timestamp"].iloc[0] if not sorted_frame.empty else None
    end = sorted_frame["timestamp"].iloc[-1] if not sorted_frame.empty else None

    return {
        "rows": int(len(sorted_frame)),
        "start": ensure_utc(start) if start is not None else None,
        "end": ensure_utc(end) if end is not None else None,
        "duplicate_timestamps": int(sorted_frame["timestamp"].duplicated().sum()),
        "timestamp_parse_failures": int(sorted_frame["timestamp"].isna().sum()),
        "null_numeric_cells": int(numeric.isna().sum().sum()),
        "non_positive_rows": int((numeric <= 0).any(axis=1).sum()),
        "ohlc_violations": ohlc_violations,
        "order_issues": order_issues,
    }


def frame_to_indexed(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values("timestamp").set_index("timestamp")


def compare_frames(target: pd.DataFrame, reference: pd.DataFrame) -> Dict[str, object]:
    joined = target.join(reference, how="outer", lsuffix="_target", rsuffix="_reference")
    only_target = int(joined["open_reference"].isna().sum())
    only_reference = int(joined["open_target"].isna().sum())
    overlap = joined.dropna()

    if overlap.empty:
        mismatch_rows = 0
    else:
        mismatch_mask = np.column_stack(
            [
                ~np.isclose(
                    overlap[f"{column}_target"].to_numpy(),
                    overlap[f"{column}_reference"].to_numpy(),
                    rtol=0,
                    atol=1e-9,
                )
                for column in OHLC_COLUMNS
            ]
        ).any(axis=1)
        mismatch_rows = int(mismatch_mask.sum())

    return {
        "target_rows": int(len(target)),
        "reference_rows": int(len(reference)),
        "overlap_rows": int(len(overlap)),
        "mismatch_rows": mismatch_rows,
        "only_target_rows": only_target,
        "only_reference_rows": only_reference,
        "matches_reference": only_target == 0 and only_reference == 0 and mismatch_rows == 0,
    }


def classify_gap(previous_ts: pd.Timestamp, next_ts: pd.Timestamp, gap_seconds: float) -> str:
    previous_minutes = previous_ts.hour * 60 + previous_ts.minute
    next_minutes = next_ts.hour * 60 + next_ts.minute

    is_routine_close = (
        20 * 60 + 10 <= previous_minutes <= 21 * 60 + 15
        and 22 * 60 <= next_minutes <= 23 * 60 + 10
    )

    is_holiday_or_early_close = (
        13 * 60 <= previous_minutes <= 19 * 60 + 15
        and 22 * 60 <= next_minutes <= 23 * 60 + 59
        and gap_seconds >= 4 * 3600
    )

    if is_routine_close:
        if gap_seconds >= 36 * 3600:
            return "weekend_session_close"
        return "routine_session_close"

    if is_holiday_or_early_close:
        return "holiday_or_early_close"

    return "unexpected_intraday_gap"


def infer_expected_session_rows(segment_rows: Sequence[int]) -> int:
    if not segment_rows:
        return 0
    return int(pd.Series(segment_rows).mode().iloc[0])


def classify_strict_ml_exclusion(
    previous_gap_category: str,
    is_full_length_segment: bool,
) -> str:
    if not is_full_length_segment:
        return "partial_segment"
    if previous_gap_category == "dataset_start":
        return "dataset_start"
    if previous_gap_category == "unexpected_intraday_gap":
        return "follows_unexpected_gap"
    return "eligible"


def build_segments(
    symbol: str,
    base_frame: pd.DataFrame,
) -> Tuple[List[GapRecord], pd.DataFrame, pd.DataFrame]:
    segmented = base_frame.sort_values("timestamp").reset_index(drop=True).copy()
    deltas = segmented["timestamp"].diff().dt.total_seconds()
    gap_breaks = deltas.gt(GAP_THRESHOLD_SECONDS).fillna(False)
    segmented["segment_id"] = gap_breaks.cumsum().astype(np.int32)

    timestamps = segmented["timestamp"]
    gap_positions = np.flatnonzero(gap_breaks.to_numpy())
    previous_gap_category_by_segment = {0: "dataset_start"}
    previous_gap_minutes_by_segment = {0: 0.0}
    gap_list: List[GapRecord] = []

    for gap_position in gap_positions:
        previous_ts = timestamps.iloc[gap_position - 1]
        next_ts = timestamps.iloc[gap_position]
        gap_seconds = float(deltas.iloc[gap_position])
        gap_minutes = gap_seconds / 60.0
        category = classify_gap(previous_ts, next_ts, gap_seconds)
        next_segment_id = int(segmented["segment_id"].iloc[gap_position])
        previous_gap_category_by_segment[next_segment_id] = category
        previous_gap_minutes_by_segment[next_segment_id] = gap_minutes
        gap_list.append(
            GapRecord(
                symbol=symbol,
                previous_timestamp=ensure_utc(previous_ts),
                next_timestamp=ensure_utc(next_ts),
                gap_minutes=round(gap_minutes, 2),
                category=category,
            )
        )

    segment_rows: List[Dict[str, object]] = []
    for segment_id, segment in segmented.groupby("segment_id", sort=True):
        segment_rows.append(
            build_segment_record(
                symbol=symbol,
                segment_id=int(segment_id),
                segment=segment,
                previous_gap_category=previous_gap_category_by_segment.get(
                    int(segment_id), "dataset_start"
                ),
                previous_gap_minutes=previous_gap_minutes_by_segment.get(int(segment_id), 0.0),
            )
        )

    segment_frame = pd.DataFrame(segment_rows).sort_values("segment_id").reset_index(drop=True)
    expected_session_rows = infer_expected_session_rows(segment_frame["rows"].tolist())
    segment_frame["session_date_utc"] = (
        pd.to_datetime(segment_frame["end_timestamp"], utc=True).dt.strftime("%Y-%m-%d")
    )
    segment_frame["expected_session_rows"] = int(expected_session_rows)
    segment_frame["is_full_length_segment"] = segment_frame["rows"].eq(expected_session_rows)
    segment_frame["follows_unexpected_gap"] = segment_frame["previous_gap_category"].eq(
        "unexpected_intraday_gap"
    )
    segment_frame["eligible_for_strict_ml"] = (
        segment_frame["is_full_length_segment"]
        & segment_frame["previous_gap_category"].isin(STRICT_ML_ALLOWED_PREVIOUS_GAPS)
    )
    segment_frame["strict_ml_exclusion_reason"] = segment_frame.apply(
        lambda row: classify_strict_ml_exclusion(
            previous_gap_category=str(row["previous_gap_category"]),
            is_full_length_segment=bool(row["is_full_length_segment"]),
        ),
        axis=1,
    )
    return gap_list, segment_frame, segmented


def build_segment_record(
    *,
    symbol: str,
    segment_id: int,
    segment: pd.DataFrame,
    previous_gap_category: str,
    previous_gap_minutes: float,
) -> Dict[str, object]:
    start_ts = segment["timestamp"].iloc[0]
    end_ts = segment["timestamp"].iloc[-1]
    return {
        "symbol": symbol,
        "segment_id": int(segment_id),
        "start_timestamp": ensure_utc(start_ts),
        "end_timestamp": ensure_utc(end_ts),
        "rows": int(len(segment)),
        "calendar_minutes": int(((end_ts - start_ts).total_seconds() / 60) + 1),
        "open": float(segment["open"].iloc[0]),
        "high": float(segment["high"].max()),
        "low": float(segment["low"].min()),
        "close": float(segment["close"].iloc[-1]),
        "previous_gap_category": previous_gap_category,
        "previous_gap_minutes": round(previous_gap_minutes, 2),
    }


def build_prepared_bars(
    symbol: str,
    segmented: pd.DataFrame,
    segment_frame: pd.DataFrame,
) -> pd.DataFrame:
    prepared = segmented.copy()
    prepared["symbol"] = symbol
    prepared["bar_index_in_segment"] = prepared.groupby("segment_id").cumcount().astype(np.int32)
    segment_sizes = prepared.groupby("segment_id")["segment_id"].transform("size").astype(np.int32)
    prepared["bars_remaining_in_segment"] = (
        segment_sizes - prepared["bar_index_in_segment"] - 1
    ).astype(np.int32)

    segment_meta = segment_frame[
        [
            "segment_id",
            "session_date_utc",
            "rows",
            "expected_session_rows",
            "previous_gap_category",
            "previous_gap_minutes",
            "is_full_length_segment",
            "follows_unexpected_gap",
            "eligible_for_strict_ml",
        ]
    ].rename(columns={"rows": "segment_rows"})

    prepared = prepared.merge(
        segment_meta,
        on="segment_id",
        how="left",
        validate="many_to_one",
    )
    prepared["timestamp"] = format_utc_series(prepared["timestamp"])

    return prepared[
        [
            "symbol",
            "timestamp",
            *OHLC_COLUMNS,
            "session_date_utc",
            "segment_id",
            "bar_index_in_segment",
            "bars_remaining_in_segment",
            "segment_rows",
            "expected_session_rows",
            "previous_gap_category",
            "previous_gap_minutes",
            "is_full_length_segment",
            "follows_unexpected_gap",
            "eligible_for_strict_ml",
        ]
    ]


def write_markdown_report(report_path: Path, report: Dict[str, object]) -> None:
    lines: List[str] = []
    lines.append("# Data Readiness")
    lines.append("")
    lines.append(f"Generated at {report['generated_at_utc']} from `{report['data_dir']}`.")
    lines.append("")
    lines.append(f"Overall status: **{report['overall_status']}**.")
    lines.append(f"Raw source status: **{report['raw_data_status']}**.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for symbol, symbol_report in report["symbols"].items():
        gap_counts = symbol_report["gaps"]["category_counts"]
        strict_ml = symbol_report["strict_ml"]
        lines.append(f"### {symbol.upper()}")
        lines.append("")
        lines.append(
            f"- `1m` rows: {symbol_report['timeframes']['1m']['rows']:,} "
            f"from {symbol_report['timeframes']['1m']['start']} to {symbol_report['timeframes']['1m']['end']}"
        )
        lines.append(
            f"- Intraday resamples verified: "
            f"{'yes' if symbol_report['ready_flags']['intraday_timeframes_match_1m'] else 'no'}"
        )
        lines.append(
            f"- Strict ML bars retained: {strict_ml['rows']:,} across "
            f"{strict_ml['eligible_segments']:,} sessions "
            f"({strict_ml['bar_retention_pct']}% of canonical `1m` bars)"
        )
        lines.append(
            f"- Expected full session length: {strict_ml['expected_session_rows']:,} bars"
        )
        lines.append(
            f"- Unexpected intraday gaps: {gap_counts.get('unexpected_intraday_gap', 0)}"
        )
        lines.append(
            f"- Routine session closures: {gap_counts.get('routine_session_close', 0)}"
        )
        lines.append(
            f"- Weekend closures: {gap_counts.get('weekend_session_close', 0)}"
        )
        lines.append(
            f"- Holiday or early-close gaps: {gap_counts.get('holiday_or_early_close', 0)}"
        )
        lines.append(
            f"- Calendar-day `1d` rows have variable minute counts: "
            f"{symbol_report['timeframes']['1d']['minute_count_min']} min to "
            f"{symbol_report['timeframes']['1d']['minute_count_max']} min"
        )
        lines.append(
            f"- Session summary file: `{symbol_report['prepared_session_file']}`"
        )
        lines.append(
            f"- Clean canonical `1m` export: `{symbol_report['prepared_clean_1m_file']}`"
        )
        lines.append(
            f"- Strict ML `1m` export: `{symbol_report['prepared_strict_ml_1m_file']}`"
        )
        lines.append("")

    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report["recommendations"]:
        lines.append(f"- {recommendation}")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for artifact in report["artifacts"]:
        lines.append(f"- `{artifact}`")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def build_report(data_dir: Path, report_dir: Path, prepared_dir: Path) -> Dict[str, object]:
    report_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)
    clean_dir = prepared_dir / "clean"
    strict_ml_dir = prepared_dir / "strict_ml"
    clean_dir.mkdir(parents=True, exist_ok=True)
    strict_ml_dir.mkdir(parents=True, exist_ok=True)

    available_files = sorted(data_dir.glob("*.csv"))
    symbols = sorted({path.stem.split("_")[0] for path in available_files})

    report: Dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data_dir": str(data_dir.as_posix()),
        "overall_status": "not_ready",
        "raw_data_status": "not_ready",
        "symbols": {},
        "recommendations": [],
        "artifacts": [],
    }

    gap_events_output: List[Dict[str, object]] = []
    unexpected_gaps_output: List[Dict[str, object]] = []
    contiguous_segments_output: List[Dict[str, object]] = []
    has_blocking_issue = False
    raw_has_caveat = False

    for symbol in symbols:
        timeframe_frames = {
            timeframe: load_ohlc_csv(data_dir / f"{symbol}_{timeframe}.csv")
            for timeframe in TIMEFRAMES
        }

        timeframe_reports: Dict[str, Dict[str, object]] = {}
        for timeframe, frame in timeframe_frames.items():
            timeframe_reports[timeframe] = validate_frame(frame)
            issues = timeframe_reports[timeframe]
            if any(
                issues[key] > 0
                for key in [
                    "duplicate_timestamps",
                    "timestamp_parse_failures",
                    "null_numeric_cells",
                    "non_positive_rows",
                    "ohlc_violations",
                    "order_issues",
                ]
            ):
                has_blocking_issue = True

        base_indexed = frame_to_indexed(timeframe_frames[CANONICAL_TIMEFRAME])

        for timeframe, (rule, strict_count) in STRICT_INTRADAY_RULES.items():
            target = frame_to_indexed(timeframe_frames[timeframe])
            grouped = base_indexed.resample(rule, label="left", closed="left")
            resampled = grouped.agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            counts = grouped["open"].count()
            strict_reference = resampled[counts == strict_count]
            comparison = compare_frames(target, strict_reference)
            timeframe_reports[timeframe]["strict_1m_resample_check"] = comparison
            if not comparison["matches_reference"]:
                has_blocking_issue = True

        daily_target = frame_to_indexed(timeframe_frames["1d"])
        daily_grouped = base_indexed.resample("1D", label="left", closed="left")
        daily_reference = daily_grouped.agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        daily_counts = daily_grouped["open"].count()
        daily_comparison = compare_frames(daily_target, daily_reference)
        timeframe_reports["1d"]["calendar_1m_resample_check"] = daily_comparison
        timeframe_reports["1d"]["minute_count_min"] = int(daily_counts[daily_counts > 0].min())
        timeframe_reports["1d"]["minute_count_median"] = int(daily_counts[daily_counts > 0].median())
        timeframe_reports["1d"]["minute_count_max"] = int(daily_counts[daily_counts > 0].max())
        timeframe_reports["1d"]["minute_count_unique_values"] = int(daily_counts[daily_counts > 0].nunique())
        timeframe_reports["1d"]["calendar_day_warning"] = (
            "The daily bars are calendar-day UTC aggregations of the minute data, "
            "so active-minute counts vary across normal days, Sundays, and holidays."
        )
        if not daily_comparison["matches_reference"]:
            has_blocking_issue = True

        gaps, segment_frame, segmented_base = build_segments(symbol, timeframe_frames[CANONICAL_TIMEFRAME])
        gap_frame = pd.DataFrame([gap.__dict__ for gap in gaps])
        if not gap_frame.empty:
            gap_events_output.extend(gap_frame.to_dict(orient="records"))
            unexpected_only = gap_frame[gap_frame["category"] == "unexpected_intraday_gap"]
            if not unexpected_only.empty:
                unexpected_gaps_output.extend(unexpected_only.to_dict(orient="records"))
        contiguous_segments_output.extend(segment_frame.to_dict(orient="records"))

        gap_category_counts = gap_frame["category"].value_counts().to_dict() if not gap_frame.empty else {}
        raw_has_caveat = raw_has_caveat or gap_category_counts.get("unexpected_intraday_gap", 0) > 0

        prepared_session_path = report_dir / f"{symbol}_session.csv"
        prepared_clean_path = clean_dir / f"{symbol}_1m_clean.csv.gz"
        prepared_strict_ml_path = strict_ml_dir / f"{symbol}_1m_strict_ml.csv.gz"

        segment_frame.to_csv(prepared_session_path, index=False)
        prepared_bars = build_prepared_bars(symbol, segmented_base, segment_frame)
        prepared_bars.to_csv(prepared_clean_path, index=False, compression="gzip")
        strict_ml_bars = prepared_bars[prepared_bars["eligible_for_strict_ml"]].copy()
        strict_ml_bars.to_csv(prepared_strict_ml_path, index=False, compression="gzip")

        strict_ml_exclusion_counts = (
            segment_frame.loc[~segment_frame["eligible_for_strict_ml"], "strict_ml_exclusion_reason"]
            .value_counts()
            .to_dict()
        )
        strict_ml_summary = {
            "rows": int(len(strict_ml_bars)),
            "eligible_segments": int(segment_frame["eligible_for_strict_ml"].sum()),
            "total_segments": int(len(segment_frame)),
            "expected_session_rows": int(segment_frame["expected_session_rows"].iloc[0]),
            "bar_retention_pct": round((len(strict_ml_bars) / len(prepared_bars)) * 100, 2),
            "excluded_segment_counts": {
                key: int(value) for key, value in strict_ml_exclusion_counts.items()
            },
        }

        ready_flags = {
            "structurally_clean": not any(
                timeframe_reports[timeframe][metric] > 0
                for timeframe in TIMEFRAMES
                for metric in [
                    "duplicate_timestamps",
                    "timestamp_parse_failures",
                    "null_numeric_cells",
                    "non_positive_rows",
                    "ohlc_violations",
                    "order_issues",
                ]
            ),
            "intraday_timeframes_match_1m": all(
                timeframe_reports[timeframe]["strict_1m_resample_check"]["matches_reference"]
                for timeframe in STRICT_INTRADAY_RULES
            ),
            "daily_timeframe_matches_calendar_1m": daily_comparison["matches_reference"],
            "has_unexpected_intraday_gaps": gap_category_counts.get("unexpected_intraday_gap", 0) > 0,
            "strict_ml_dataset_ready": strict_ml_summary["rows"] > 0,
        }

        report["symbols"][symbol] = {
            "timeframes": timeframe_reports,
            "gaps": {
                "total_gaps_over_1m": int(len(gaps)),
                "category_counts": {key: int(value) for key, value in gap_category_counts.items()},
            },
            "strict_ml": strict_ml_summary,
            "ready_flags": ready_flags,
            "prepared_session_file": prepared_session_path.as_posix(),
            "prepared_clean_1m_file": prepared_clean_path.as_posix(),
            "prepared_strict_ml_1m_file": prepared_strict_ml_path.as_posix(),
        }

    gap_events_path = report_dir / "gap_events.csv"
    unexpected_gaps_path = report_dir / "unexpected_gaps.csv"
    contiguous_segments_path = report_dir / "contiguous_segments.csv"
    report_json_path = report_dir / "data_quality_report.json"
    report_markdown_path = report_dir / "model_readiness.md"

    gap_columns = ["symbol", "previous_timestamp", "next_timestamp", "gap_minutes", "category"]
    if gap_events_output:
        pd.DataFrame(gap_events_output).to_csv(gap_events_path, index=False)
    else:
        pd.DataFrame(columns=gap_columns).to_csv(gap_events_path, index=False)

    if unexpected_gaps_output:
        pd.DataFrame(unexpected_gaps_output).to_csv(unexpected_gaps_path, index=False)
    else:
        pd.DataFrame(columns=gap_columns).to_csv(unexpected_gaps_path, index=False)

    pd.DataFrame(contiguous_segments_output).to_csv(contiguous_segments_path, index=False)

    report["artifacts"] = [
        report_json_path.as_posix(),
        report_markdown_path.as_posix(),
        gap_events_path.as_posix(),
        unexpected_gaps_path.as_posix(),
        contiguous_segments_path.as_posix(),
        *(prepared["prepared_session_file"] for prepared in report["symbols"].values()),
        *(prepared["prepared_clean_1m_file"] for prepared in report["symbols"].values()),
        *(prepared["prepared_strict_ml_1m_file"] for prepared in report["symbols"].values()),
    ]

    report["recommendations"] = [
        "Use the `*_1m_clean.csv.gz` files as the canonical source for feature analysis. They include segment and session metadata on every bar.",
        "Use the `*_1m_strict_ml.csv.gz` files for model training, and keep every lookback window and forecast horizon inside a single `segment_id`.",
        "Treat the raw `5m`, `15m`, `1h`, and `4h` files as validated resamples of the raw minute feed. If you need those timeframes for training, derive them from the clean minute exports after filtering by `segment_id`.",
        "Review `data/metadata/unexpected_gaps.csv` only if you want to recover additional raw history. Those sessions are intentionally excluded from the strict ML exports.",
        "Avoid using the raw `1d` files as uniform trading-session bars. They are calendar-day UTC aggregations with variable active-minute counts.",
    ]

    if has_blocking_issue:
        report["raw_data_status"] = "not_ready"
        report["overall_status"] = "not_ready"
    else:
        report["raw_data_status"] = "ready_with_caveats" if raw_has_caveat else "ready"
        report["overall_status"] = (
            "ready"
            if all(
                symbol_report["ready_flags"]["strict_ml_dataset_ready"]
                for symbol_report in report["symbols"].values()
            )
            else "not_ready"
        )

    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown_report(report_markdown_path, report)
    return report


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir).resolve()
    report_dir = Path(args.report_dir).resolve()
    prepared_dir = Path(args.prepared_dir).resolve()

    report = build_report(data_dir=data_dir, report_dir=report_dir, prepared_dir=prepared_dir)
    return 1 if report["overall_status"] == "not_ready" else 0


if __name__ == "__main__":
    raise SystemExit(main())
