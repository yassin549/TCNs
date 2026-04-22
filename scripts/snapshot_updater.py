from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


REQUIRED_SNAPSHOT_COLUMNS = [
    "timestamp",
    "session_date_utc",
    "segment_id",
    "bar_index_in_segment",
    "bars_remaining_in_segment",
    "open",
    "high",
    "low",
    "close",
    "atr_14",
    "return_1",
    "return_5",
    "return_15",
    "body_return",
    "upper_wick_pct",
    "lower_wick_pct",
    "true_range_pct",
    "atr_pct",
    "rolling_vol_15",
    "rolling_vol_60",
    "rolling_range_15_atr",
    "rolling_range_60_atr",
    "trend_score_10",
    "trend_score_30",
    "trend_score_60",
    "pullback_score_5",
    "pullback_score_10",
    "session_progress",
    "bars_remaining_pct",
    "session_range_pos",
    "session_range_atr",
    "distance_to_session_high_atr",
    "distance_to_session_low_atr",
    "session_open_return_atr",
    "minute_sin",
    "minute_cos",
    "weekday_sin",
    "weekday_cos",
    "london_minute_sin",
    "london_minute_cos",
    "new_york_minute_sin",
    "new_york_minute_cos",
    "is_asia_session",
    "is_europe_session",
    "is_us_session",
    "is_session_open_window",
    "is_session_close_window",
    "is_london_open_window",
    "is_new_york_open_window",
    "is_london_new_york_overlap",
    "prev_session_body_return_1",
    "prev_session_body_return_2",
    "prev_session_body_return_3",
    "prev_session_body_return_4",
    "prev_session_body_return_5",
    "prev_session_direction_1",
    "prev_session_direction_2",
    "prev_session_direction_3",
    "prev_session_direction_4",
    "prev_session_direction_5",
    "prev5_bullish_fraction",
    "prev5_bearish_fraction",
    "prev5_net_body_return",
    "prev_session_streak_sign",
    "prev_session_streak_length",
    "model_sample_eligible",
]


@dataclass(frozen=True)
class SnapshotUpdaterConfig:
    instrument_id: str
    epic: str
    snapshot_path: Path
    log_dir: Path
    expected_session_rows: int = 1335
    max_fetch: int = 240
    stale_after_seconds: int = 120
    min_required_rows: int = 120
    reset_if_older_than_seconds: int = 6 * 60 * 60
    reset_backfill_rows: int = 9000
    history_page_rows: int = 1000


@dataclass(frozen=True)
class SnapshotUpdateResult:
    instrument_id: str
    fetch_epic: str
    snapshot_path: str
    rows_before: int
    rows_after: int
    rows_appended: int
    fetched_rows: int
    duplicate_rows: int
    out_of_order_rows: int
    latest_timestamp_utc: Optional[str]
    latest_age_seconds: Optional[float]
    stale: bool
    history_reset: bool
    missing_data_alerts: List[str]
    last_update_time_utc: str


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(parsed):
        return default
    return float(parsed)


def _compression(path: Path) -> Optional[str]:
    return "gzip" if str(path).endswith(".gz") else None


def _mid(price_block: Dict[str, object]) -> float:
    bid = _safe_float(price_block.get("bid"), np.nan)
    ask = _safe_float(price_block.get("ask"), np.nan)
    if np.isfinite(bid) and np.isfinite(ask):
        return (bid + ask) / 2.0
    if np.isfinite(bid):
        return bid
    if np.isfinite(ask):
        return ask
    return np.nan


def normalize_price_rows(payload: Dict[str, object]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for item in payload.get("prices", []):
        timestamp = item.get("snapshotTimeUTC") or item.get("snapshotTime")
        if not timestamp:
            continue
        rows.append(
            {
                "timestamp": pd.Timestamp(timestamp, tz="UTC"),
                "open": _mid(dict(item.get("openPrice", {}))),
                "high": _mid(dict(item.get("highPrice", {}))),
                "low": _mid(dict(item.get("lowPrice", {}))),
                "close": _mid(dict(item.get("closePrice", {}))),
                "volume": _safe_float(item.get("lastTradedVolume"), 0.0),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    frame = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return frame


def fetch_price_history(
    client,
    epic: str,
    max_rows: int,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
) -> pd.DataFrame:
    payload = client.get_historical_prices(
        epic,
        resolution="MINUTE",
        max_rows=int(max_rows),
        from_time=from_time,
        to_time=to_time,
    )
    return normalize_price_rows(payload)


def fetch_price_history_backfill(
    client,
    epic: str,
    target_rows: int,
    page_rows: int,
) -> pd.DataFrame:
    pages: List[pd.DataFrame] = []
    cursor_to_time: Optional[str] = None
    total_rows = 0
    for _ in range(max(1, int(np.ceil(target_rows / max(page_rows, 1)))) + 2):
        page = fetch_price_history(client, epic, max_rows=page_rows, to_time=cursor_to_time)
        if page.empty:
            break
        pages.append(page)
        total_rows += len(page)
        earliest = pd.Timestamp(page["timestamp"].iloc[0]) - timedelta(minutes=1)
        cursor_to_time = earliest.strftime("%Y-%m-%dT%H:%M:%S")
        if total_rows >= int(target_rows):
            break
        if len(page) < int(page_rows):
            break
    if not pages:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    combined = pd.concat(pages, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp").reset_index(drop=True)
    if len(combined) > int(target_rows):
        combined = combined.iloc[-int(target_rows) :].reset_index(drop=True)
    return combined


def load_existing_snapshot(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
    usecols = [column for column in ["timestamp", "open", "high", "low", "close"] if column]
    frame = pd.read_csv(path, compression=_compression(path), usecols=usecols)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    for column in ["open", "high", "low", "close"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("timestamp").reset_index(drop=True)


def append_monotonic_rows(existing: pd.DataFrame, incoming: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    if incoming.empty:
        return existing.copy(), 0, 0
    incoming = incoming.sort_values("timestamp").reset_index(drop=True)
    if not incoming["timestamp"].is_monotonic_increasing:
        raise ValueError("Incoming price rows are not monotonic.")
    duplicate_rows = 0
    out_of_order_rows = 0
    if existing.empty:
        combined = incoming.copy()
    else:
        last_timestamp = pd.Timestamp(existing["timestamp"].iloc[-1])
        new_rows = incoming.loc[incoming["timestamp"] > last_timestamp].copy()
        duplicate_rows = int((incoming["timestamp"] == last_timestamp).sum())
        out_of_order_rows = int((incoming["timestamp"] < last_timestamp).sum())
        combined = pd.concat([existing, new_rows], ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"], keep="first").sort_values("timestamp").reset_index(drop=True)
    return combined, duplicate_rows, out_of_order_rows


def _minutes_since_midnight(series: pd.Series, timezone_name: Optional[str] = None) -> np.ndarray:
    timestamps = pd.to_datetime(series, utc=True)
    if timezone_name:
        localized = timestamps.dt.tz_convert(timezone_name)
    else:
        localized = timestamps
    return (localized.dt.hour * 60 + localized.dt.minute).to_numpy(dtype=float)


def _cyclical(minutes: np.ndarray, period: float) -> tuple[np.ndarray, np.ndarray]:
    radians = 2.0 * np.pi * minutes / period
    return np.sin(radians), np.cos(radians)


def _session_flags(timestamps: pd.Series) -> pd.DataFrame:
    minutes = _minutes_since_midnight(timestamps)
    hours = np.floor(minutes / 60.0)
    asia = ((hours >= 23) | (hours < 7)).astype(float)
    europe = ((hours >= 7) & (hours < 13)).astype(float)
    us = ((hours >= 13) & (hours < 21)).astype(float)
    london_open = ((hours == 8) | ((hours == 9) & (minutes % 60 <= 30))).astype(float)
    new_york_open = ((hours == 13) | ((hours == 14) & (minutes % 60 <= 30))).astype(float)
    overlap = ((hours >= 13) & (hours < 16)).astype(float)
    return pd.DataFrame(
        {
            "is_asia_session": asia,
            "is_europe_session": europe,
            "is_us_session": us,
            "is_session_open_window": ((asia + europe + us) > 0.0).astype(float),
            "is_session_close_window": ((hours >= 20) | (hours < 1)).astype(float),
            "is_london_open_window": london_open,
            "is_new_york_open_window": new_york_open,
            "is_london_new_york_overlap": overlap,
        }
    )


def build_feature_snapshot(raw_bars: pd.DataFrame, expected_session_rows: int, min_required_rows: int) -> pd.DataFrame:
    if raw_bars.empty:
        return pd.DataFrame(columns=REQUIRED_SNAPSHOT_COLUMNS)
    frame = raw_bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    delta = frame["timestamp"].diff().dt.total_seconds()
    segment_break = delta.isna() | (delta > 60.0)
    frame["segment_id"] = segment_break.cumsum().astype(int)
    frame["bar_index_in_segment"] = frame.groupby("segment_id").cumcount()
    frame["bars_remaining_in_segment"] = np.maximum(expected_session_rows - frame["bar_index_in_segment"] - 1, 0)
    frame["session_date_utc"] = frame["timestamp"].dt.date

    prev_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr_14"] = true_range.rolling(14, min_periods=14).mean()
    frame["return_1"] = frame["close"].pct_change(1)
    frame["return_5"] = frame["close"].pct_change(5)
    frame["return_15"] = frame["close"].pct_change(15)
    frame["body_return"] = (frame["close"] - frame["open"]) / frame["open"].replace(0.0, np.nan)
    frame["upper_wick_pct"] = (frame["high"] - frame[["open", "close"]].max(axis=1)) / frame["close"].replace(0.0, np.nan)
    frame["lower_wick_pct"] = (frame[["open", "close"]].min(axis=1) - frame["low"]) / frame["close"].replace(0.0, np.nan)
    frame["true_range_pct"] = true_range / frame["close"].replace(0.0, np.nan)
    frame["atr_pct"] = frame["atr_14"] / frame["close"].replace(0.0, np.nan)
    frame["rolling_vol_15"] = frame["return_1"].rolling(15, min_periods=15).std()
    frame["rolling_vol_60"] = frame["return_1"].rolling(60, min_periods=60).std()
    frame["rolling_range_15_atr"] = (
        frame["high"].rolling(15, min_periods=15).max() - frame["low"].rolling(15, min_periods=15).min()
    ) / frame["atr_14"].replace(0.0, np.nan)
    frame["rolling_range_60_atr"] = (
        frame["high"].rolling(60, min_periods=60).max() - frame["low"].rolling(60, min_periods=60).min()
    ) / frame["atr_14"].replace(0.0, np.nan)
    frame["trend_score_10"] = (frame["close"] - frame["close"].shift(10)) / frame["atr_14"].replace(0.0, np.nan)
    frame["trend_score_30"] = (frame["close"] - frame["close"].shift(30)) / frame["atr_14"].replace(0.0, np.nan)
    frame["trend_score_60"] = (frame["close"] - frame["close"].shift(60)) / frame["atr_14"].replace(0.0, np.nan)
    frame["pullback_score_5"] = (frame["close"] - frame["close"].rolling(5, min_periods=5).mean()) / frame["atr_14"].replace(0.0, np.nan)
    frame["pullback_score_10"] = (frame["close"] - frame["close"].rolling(10, min_periods=10).mean()) / frame["atr_14"].replace(0.0, np.nan)
    frame["session_progress"] = frame["bar_index_in_segment"] / max(expected_session_rows - 1, 1)
    frame["bars_remaining_pct"] = frame["bars_remaining_in_segment"] / max(expected_session_rows - 1, 1)

    segment_groups = frame.groupby("segment_id", sort=False)
    session_high = segment_groups["high"].cummax()
    session_low = segment_groups["low"].cummin()
    session_open = segment_groups["open"].transform("first")
    session_range = (session_high - session_low).replace(0.0, np.nan)
    frame["session_range_pos"] = ((frame["close"] - session_low) / session_range).clip(0.0, 1.0)
    frame["session_range_atr"] = session_range / frame["atr_14"].replace(0.0, np.nan)
    frame["distance_to_session_high_atr"] = (session_high - frame["close"]) / frame["atr_14"].replace(0.0, np.nan)
    frame["distance_to_session_low_atr"] = (frame["close"] - session_low) / frame["atr_14"].replace(0.0, np.nan)
    frame["session_open_return_atr"] = (frame["close"] - session_open) / frame["atr_14"].replace(0.0, np.nan)

    minute_utc = _minutes_since_midnight(frame["timestamp"])
    weekday = pd.to_datetime(frame["timestamp"], utc=True).dt.weekday.to_numpy(dtype=float)
    minute_sin, minute_cos = _cyclical(minute_utc, 1440.0)
    weekday_sin, weekday_cos = _cyclical(weekday, 7.0)
    london_minutes = _minutes_since_midnight(frame["timestamp"], "Europe/London")
    london_minute_sin, london_minute_cos = _cyclical(london_minutes, 1440.0)
    new_york_minutes = _minutes_since_midnight(frame["timestamp"], "America/New_York")
    new_york_minute_sin, new_york_minute_cos = _cyclical(new_york_minutes, 1440.0)
    frame["minute_sin"] = minute_sin
    frame["minute_cos"] = minute_cos
    frame["weekday_sin"] = weekday_sin
    frame["weekday_cos"] = weekday_cos
    frame["london_minute_sin"] = london_minute_sin
    frame["london_minute_cos"] = london_minute_cos
    frame["new_york_minute_sin"] = new_york_minute_sin
    frame["new_york_minute_cos"] = new_york_minute_cos
    frame = pd.concat([frame, _session_flags(frame["timestamp"])], axis=1)

    segment_summary = (
        frame.groupby("segment_id", sort=True)
        .agg(
            session_close=("close", "last"),
            session_open=("open", "first"),
        )
        .reset_index(drop=False)
    )
    segment_summary["body_return"] = (segment_summary["session_close"] - segment_summary["session_open"]) / segment_summary["session_open"].replace(0.0, np.nan)
    segment_summary["direction"] = np.sign(segment_summary["body_return"]).replace(0.0, 0.0)
    for lag in range(1, 6):
        segment_summary[f"prev_session_body_return_{lag}"] = segment_summary["body_return"].shift(lag)
        segment_summary[f"prev_session_direction_{lag}"] = segment_summary["direction"].shift(lag)
    prev_dirs = [segment_summary[f"prev_session_direction_{lag}"] for lag in range(1, 6)]
    prev_bodies = [segment_summary[f"prev_session_body_return_{lag}"] for lag in range(1, 6)]
    segment_summary["prev5_bullish_fraction"] = pd.concat(prev_dirs, axis=1).eq(1.0).mean(axis=1)
    segment_summary["prev5_bearish_fraction"] = pd.concat(prev_dirs, axis=1).eq(-1.0).mean(axis=1)
    segment_summary["prev5_net_body_return"] = pd.concat(prev_bodies, axis=1).sum(axis=1, min_count=1)
    streak_sign: List[float] = []
    streak_length: List[float] = []
    running_sign = 0.0
    running_length = 0
    for direction in segment_summary["direction"].fillna(0.0).tolist():
        if direction == 0.0:
            running_sign = 0.0
            running_length = 0
        elif direction == running_sign:
            running_length += 1
        else:
            running_sign = direction
            running_length = 1
        streak_sign.append(running_sign)
        streak_length.append(float(running_length))
    segment_summary["prev_session_streak_sign"] = pd.Series(streak_sign).shift(1)
    segment_summary["prev_session_streak_length"] = pd.Series(streak_length).shift(1)
    frame = frame.merge(segment_summary.drop(columns=["session_close", "session_open", "body_return", "direction"]), on="segment_id", how="left")

    required_numeric = [column for column in REQUIRED_SNAPSHOT_COLUMNS if column not in {"timestamp", "session_date_utc", "model_sample_eligible"}]
    frame[required_numeric] = frame[required_numeric].replace([np.inf, -np.inf], np.nan)
    frame["model_sample_eligible"] = (
        frame["bar_index_in_segment"] >= max(min_required_rows - 1, 0)
    ) & frame[required_numeric].notna().all(axis=1)
    snapshot = frame[REQUIRED_SNAPSHOT_COLUMNS].copy()
    return snapshot


def validate_snapshot_freshness(snapshot: pd.DataFrame, now: datetime, stale_after_seconds: int) -> tuple[bool, Optional[float], Optional[str]]:
    if snapshot.empty:
        return False, None, None
    latest_timestamp = pd.Timestamp(snapshot["timestamp"].iloc[-1])
    age_seconds = max(0.0, (now - latest_timestamp.to_pydatetime()).total_seconds())
    return age_seconds <= float(stale_after_seconds), age_seconds, latest_timestamp.isoformat()


def update_snapshot(client, config: SnapshotUpdaterConfig) -> SnapshotUpdateResult:
    now = datetime.now(timezone.utc)
    existing = load_existing_snapshot(config.snapshot_path)
    rows_before = int(len(existing))
    from_ts: Optional[str] = None
    history_reset = False
    if rows_before < int(config.reset_backfill_rows):
        history_reset = True
    if not existing.empty:
        latest = pd.Timestamp(existing["timestamp"].iloc[-1])
        existing_age_seconds = max(0.0, (now - latest.to_pydatetime()).total_seconds())
        if not history_reset and existing_age_seconds <= float(config.reset_if_older_than_seconds):
            from_ts = (latest - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
        elif existing_age_seconds > float(config.reset_if_older_than_seconds):
            history_reset = True
    try:
        if history_reset:
            incoming = fetch_price_history_backfill(
                client,
                config.epic,
                target_rows=int(config.reset_backfill_rows),
                page_rows=int(config.history_page_rows),
            )
        else:
            incoming = fetch_price_history(client, config.epic, max_rows=int(config.max_fetch), from_time=from_ts)
    except Exception:
        if from_ts is None:
            raise
        history_reset = True
        incoming = fetch_price_history_backfill(
            client,
            config.epic,
            target_rows=int(config.reset_backfill_rows),
            page_rows=int(config.history_page_rows),
        )
    fetched_rows = int(len(incoming))
    duplicate_rows = 0
    out_of_order_rows = 0
    if history_reset:
        combined = incoming.copy()
        rows_appended = int(len(combined))
    else:
        combined, duplicate_rows, out_of_order_rows = append_monotonic_rows(existing, incoming)
        rows_appended = max(0, int(len(combined)) - rows_before)
        if not existing.empty and not incoming.empty:
            existing_latest = pd.Timestamp(existing["timestamp"].iloc[-1])
            incoming_latest = pd.Timestamp(incoming["timestamp"].iloc[-1])
            gap_seconds = max(0.0, (incoming_latest - existing_latest).total_seconds())
            if gap_seconds > float(config.reset_if_older_than_seconds):
                history_reset = True
                combined = incoming.copy()
                rows_appended = int(len(combined))
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)
    alerts: List[str] = []
    if history_reset and rows_before > 0:
        alerts.append(f"Snapshot history reset for {config.instrument_id}; reseeded from recent broker bars.")
    deltas = combined["timestamp"].diff().dt.total_seconds()
    for gap in combined.loc[deltas > 60.0, "timestamp"]:
        alerts.append(f"Gap detected before {pd.Timestamp(gap).isoformat()}")
    snapshot = build_feature_snapshot(combined, expected_session_rows=int(config.expected_session_rows), min_required_rows=int(config.min_required_rows))
    config.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(config.snapshot_path, index=False, compression=_compression(config.snapshot_path))
    fresh, latest_age_seconds, latest_timestamp = validate_snapshot_freshness(snapshot, now, int(config.stale_after_seconds))
    result = SnapshotUpdateResult(
        instrument_id=config.instrument_id,
        fetch_epic=config.epic,
        snapshot_path=str(config.snapshot_path),
        rows_before=rows_before,
        rows_after=int(len(snapshot)),
        rows_appended=rows_appended,
        fetched_rows=fetched_rows,
        duplicate_rows=duplicate_rows,
        out_of_order_rows=out_of_order_rows,
        latest_timestamp_utc=latest_timestamp,
        latest_age_seconds=None if latest_age_seconds is None else round(float(latest_age_seconds), 3),
        stale=not fresh,
        history_reset=history_reset,
        missing_data_alerts=alerts,
        last_update_time_utc=now.isoformat(),
    )
    config.log_dir.mkdir(parents=True, exist_ok=True)
    (config.log_dir / "snapshot_status.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    with (config.log_dir / "snapshot_updates.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(result)) + "\n")
    return result
