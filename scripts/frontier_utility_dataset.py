from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from frontier_account_state import AccountStateConfig, AccountStateTracker
from prop_firm_rules import fundedhive_backtest_defaults


SETUPS = [
    "long_reversal",
    "long_continuation",
    "short_reversal",
    "short_continuation",
]
LABEL_COLUMNS = [f"label_{setup}" for setup in SETUPS]
CHALLENGE_TARGET_COLUMNS = [
    "challenge_pass_prob_5d",
    "challenge_pass_prob_10d",
    "challenge_pass_prob_20d",
    "challenge_fail_prob_5d",
    "challenge_fail_prob_10d",
    "challenge_expected_days_to_resolution",
    "challenge_distance_to_target_delta",
    "challenge_daily_loss_budget_consumption",
    "challenge_total_drawdown_budget_consumption",
]
FUNDED_TARGET_COLUMNS = [
    "funded_expected_return_5d",
    "funded_expected_return_20d",
    "funded_breach_risk_5d",
    "funded_breach_risk_20d",
    "funded_expected_drawdown",
    "funded_expected_payout_growth",
]
BASE_REQUIRED_COLUMNS = [
    "timestamp",
    "session_date_utc",
    "atr_14",
    "model_sample_eligible",
]


def _read_csv(path: Path, max_rows: Optional[int]) -> pd.DataFrame:
    kwargs = {"compression": "gzip"} if str(path).endswith(".gz") else {}
    if max_rows and max_rows > 0:
        kwargs["nrows"] = int(max_rows)
    frame = pd.read_csv(path, **kwargs)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["session_date_utc"] = pd.to_datetime(frame["session_date_utc"]).dt.date
    frame = frame.sort_values(["timestamp"]).reset_index(drop=True)
    return frame


def _validate_columns(frame: pd.DataFrame) -> None:
    required = set(BASE_REQUIRED_COLUMNS + LABEL_COLUMNS)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Utility dataset build is missing required columns: {missing}")


def _safe_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.fillna(False).astype(bool)


def _build_reference_trade_lookup(path: Optional[Path]) -> Dict[pd.Timestamp, List[Dict[str, float]]]:
    if path is None or not path.exists():
        return {}
    trades = pd.read_csv(path, compression="gzip" if str(path).endswith(".gz") else None)
    trades["entry_timestamp"] = pd.to_datetime(trades["entry_timestamp"], utc=True)
    trades["session_date_utc"] = pd.to_datetime(trades["session_date_utc"]).dt.date
    lookup: Dict[pd.Timestamp, List[Dict[str, float]]] = {}
    for row in trades.to_dict("records"):
        lookup.setdefault(row["entry_timestamp"], []).append(
            {
                "session_date_utc": row["session_date_utc"],
                "pnl_cash": float(row.get("pnl_cash", 0.0)),
                "pnl_r": float(row.get("pnl_r", 0.0)),
            }
        )
    return lookup


def _compute_trade_utility_columns(
    frame: pd.DataFrame,
    target_atr_multiple: float,
    stop_atr_multiple: float,
    round_trip_cost_points: float,
) -> pd.DataFrame:
    enriched = frame.copy()
    atr = pd.to_numeric(enriched["atr_14"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(1.0)
    stop_distance = np.maximum(stop_atr_multiple * atr.to_numpy(dtype=float), 0.25)
    cost_r = round_trip_cost_points / stop_distance
    win_r = (target_atr_multiple / stop_atr_multiple) - cost_r
    loss_r = -1.0 - cost_r

    utility_columns: List[str] = []
    positive_matrix = []
    for idx, setup in enumerate(SETUPS):
        label_col = LABEL_COLUMNS[idx]
        labels = _safe_bool_series(enriched[label_col]).to_numpy(dtype=bool)
        utility = np.where(labels, win_r, loss_r)
        enriched[f"utility_{setup}_r"] = np.round(utility, 6)
        utility_columns.append(f"utility_{setup}_r")
        positive_matrix.append(labels)

    positive_mask = np.column_stack(positive_matrix) if positive_matrix else np.zeros((len(enriched), 0), dtype=bool)
    utilities = enriched[utility_columns].to_numpy(dtype=float)
    best_idx = np.argmax(utilities, axis=1)
    has_positive = positive_mask.any(axis=1)
    best_setup = np.where(has_positive, np.array(SETUPS, dtype=object)[best_idx], "none")
    best_utility = utilities[np.arange(len(enriched)), best_idx]
    action_target = np.where(has_positive, np.maximum(best_utility, 0.0), 0.0)

    enriched["utility_best_setup"] = best_setup
    enriched["utility_best_setup_r"] = np.round(best_utility, 6)
    enriched["trade_challenge_utility"] = np.round(action_target, 6)
    enriched["trade_realized_pnl_r"] = np.round(action_target, 6)
    enriched["trade_realized_pnl_cash"] = 0.0
    enriched["trade_reference_taken"] = has_positive.astype(int)
    enriched["trade_passed"] = (action_target > 0.0).astype(int)

    return enriched


def _annotate_account_stage(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    stage = enriched.get("account_stage")
    if stage is None:
        stage = pd.Series(["challenge"] * len(enriched), index=enriched.index)
    stage = stage.fillna("challenge").astype(str)
    enriched["account_stage"] = stage
    enriched["is_challenge_stage"] = (stage == "challenge").astype(float)
    enriched["is_funded_stage"] = (stage == "funded").astype(float)
    return enriched


def _compute_stage_targets(
    frame: pd.DataFrame,
    profit_target_pct: float,
    min_profitable_days: int,
    max_daily_loss_pct: float,
    max_total_drawdown_pct: float,
) -> pd.DataFrame:
    enriched = frame.copy()
    positive_utility = pd.to_numeric(enriched["trade_challenge_utility"], errors="coerce").fillna(0.0).clip(lower=0.0)
    negative_utility = (
        pd.to_numeric(enriched["utility_best_setup_r"], errors="coerce").fillna(0.0).clip(upper=0.0).abs()
    )
    target_distance = (
        pd.to_numeric(enriched["account_distance_to_target_pct"], errors="coerce").fillna(0.0)
        / max(float(profit_target_pct), 1e-6)
    ).clip(0.0, 1.5)
    target_closeness = (1.0 - (target_distance / 1.5)).clip(0.0, 1.0)
    profitable_day_pressure = (
        pd.to_numeric(enriched["account_profitable_days_remaining"], errors="coerce").fillna(0.0)
        / max(float(min_profitable_days), 1.0)
    ).clip(0.0, 1.5)
    drawdown_pressure = (
        pd.to_numeric(enriched["account_drawdown_pct"], errors="coerce").fillna(0.0)
        / max(float(max_total_drawdown_pct), 1e-6)
    ).clip(0.0, 1.5)
    daily_loss_pressure = (
        1.0
        - (
            pd.to_numeric(enriched["day_loss_budget_remaining_pct"], errors="coerce").fillna(max_daily_loss_pct)
            / max(float(max_daily_loss_pct), 1e-6)
        )
    ).clip(0.0, 1.5)
    total_drawdown_pressure = (
        1.0
        - (
            pd.to_numeric(enriched["total_drawdown_budget_remaining_pct"], errors="coerce").fillna(max_total_drawdown_pct)
            / max(float(max_total_drawdown_pct), 1e-6)
        )
    ).clip(0.0, 1.5)
    days_elapsed_pressure = (
        pd.to_numeric(enriched["account_days_elapsed"], errors="coerce").fillna(0.0) / 20.0
    ).clip(0.0, 2.0)

    # Challenge targets: optimize fast pass or fast failure, not slow stagnation.
    enriched["challenge_pass_prob_5d"] = np.round(
        np.clip(positive_utility * (0.18 + 0.40 * target_closeness + 0.10 * profitable_day_pressure), 0.0, 1.0),
        6,
    )
    enriched["challenge_pass_prob_10d"] = np.round(
        np.clip(positive_utility * (0.22 + 0.30 * target_closeness + 0.08 * profitable_day_pressure), 0.0, 1.0),
        6,
    )
    enriched["challenge_pass_prob_20d"] = np.round(
        np.clip(positive_utility * (0.28 + 0.18 * target_closeness + 0.06 * profitable_day_pressure), 0.0, 1.0),
        6,
    )
    enriched["challenge_fail_prob_5d"] = np.round(
        np.clip(
            negative_utility * (0.18 + 0.35 * daily_loss_pressure + 0.30 * total_drawdown_pressure),
            0.0,
            1.0,
        ),
        6,
    )
    enriched["challenge_fail_prob_10d"] = np.round(
        np.clip(
            negative_utility * (0.22 + 0.25 * daily_loss_pressure + 0.25 * total_drawdown_pressure),
            0.0,
            1.0,
        ),
        6,
    )
    enriched["challenge_expected_days_to_resolution"] = np.round(
        np.clip(
            8.0
            + 10.0 * target_distance
            + 2.0 * profitable_day_pressure
            + 3.0 * negative_utility
            - 8.0 * positive_utility
            - 1.5 * days_elapsed_pressure,
            1.0,
            40.0,
        ),
        6,
    )
    enriched["challenge_distance_to_target_delta"] = np.round(
        np.clip(positive_utility * (0.30 + 0.45 * target_distance + 0.10 * days_elapsed_pressure), 0.0, profit_target_pct),
        6,
    )
    enriched["challenge_daily_loss_budget_consumption"] = np.round(
        np.clip(
            negative_utility * (0.35 + 0.35 * daily_loss_pressure) + 0.05 * positive_utility,
            0.0,
            max_daily_loss_pct,
        ),
        6,
    )
    enriched["challenge_total_drawdown_budget_consumption"] = np.round(
        np.clip(
            negative_utility * (0.30 + 0.40 * total_drawdown_pressure) + 0.04 * positive_utility,
            0.0,
            max_total_drawdown_pct,
        ),
        6,
    )

    # Funded targets: maximize return while minimizing breach risk.
    funded_return_scale = 1.0 - 0.35 * total_drawdown_pressure
    enriched["funded_expected_return_5d"] = np.round(
        np.clip(positive_utility * (0.22 + 0.18 * funded_return_scale), 0.0, 2.0),
        6,
    )
    enriched["funded_expected_return_20d"] = np.round(
        np.clip(positive_utility * (0.55 + 0.25 * funded_return_scale), 0.0, 4.0),
        6,
    )
    enriched["funded_breach_risk_5d"] = np.round(
        np.clip(negative_utility * (0.18 + 0.30 * total_drawdown_pressure + 0.20 * daily_loss_pressure), 0.0, 1.0),
        6,
    )
    enriched["funded_breach_risk_20d"] = np.round(
        np.clip(negative_utility * (0.28 + 0.35 * total_drawdown_pressure + 0.15 * daily_loss_pressure), 0.0, 1.0),
        6,
    )
    enriched["funded_expected_drawdown"] = np.round(
        np.clip(negative_utility * (0.35 + 0.40 * total_drawdown_pressure), 0.0, max_total_drawdown_pct),
        6,
    )
    enriched["funded_expected_payout_growth"] = np.round(
        np.clip(positive_utility * (0.28 + 0.30 * funded_return_scale), 0.0, 4.0),
        6,
    )
    return enriched


def _apply_reference_account_state(
    frame: pd.DataFrame,
    reference_trade_lookup: Dict[pd.Timestamp, List[Dict[str, float]]],
    config: AccountStateConfig,
) -> pd.DataFrame:
    tracker = AccountStateTracker(config)
    account_rows: List[Dict[str, float]] = []
    reference_trade_count = 0

    for row in frame.itertuples(index=False):
        snapshot = tracker.observe_day(row.session_date_utc)
        account_rows.append(snapshot)
        for trade in reference_trade_lookup.get(row.timestamp, []):
            tracker.apply_trade(
                trade_day=trade["session_date_utc"],
                pnl_cash=trade["pnl_cash"],
                pnl_r=trade["pnl_r"],
            )
            reference_trade_count += 1

    account_frame = pd.DataFrame(account_rows, index=frame.index)
    enriched = pd.concat([frame, account_frame], axis=1)
    enriched.attrs["reference_trade_count"] = reference_trade_count
    enriched.attrs["account_state_summary"] = tracker.finalize()
    return enriched


def build_dataset_schema(
    input_path: Path,
    output_path: Path,
    frame: pd.DataFrame,
    config: AccountStateConfig,
    reference_trades_path: Optional[Path],
) -> Dict[str, object]:
    account_columns = [
        "account_stage",
        "account_stage_code",
        "account_passed_challenge",
        "is_challenge_stage",
        "is_funded_stage",
        "account_balance",
        "account_return_pct_to_date",
        "account_drawdown_pct",
        "account_distance_to_target_pct",
        "account_profitable_days_so_far",
        "account_profitable_days_remaining",
        "account_days_elapsed",
        "day_pnl_pct_so_far",
        "day_loss_budget_remaining_pct",
        "total_drawdown_budget_remaining_pct",
        "trades_taken_today",
        "trade_slots_remaining_today",
        "last_trade_pnl_r",
        "win_streak",
        "loss_streak",
    ]
    utility_columns = [f"utility_{setup}_r" for setup in SETUPS] + [
        "utility_best_setup",
        "utility_best_setup_r",
        "trade_challenge_utility",
        "trade_realized_pnl_r",
        "trade_realized_pnl_cash",
        "trade_reference_taken",
        "trade_passed",
    ] + CHALLENGE_TARGET_COLUMNS + FUNDED_TARGET_COLUMNS
    return {
        "schema_name": "frontier_utility_dataset",
        "schema_version": 3,
        "stage": "phase2_stage_aware_propfirm_targets",
        "input_path": str(input_path.resolve()),
        "output_path": str(output_path.resolve()),
        "reference_trades_path": str(reference_trades_path.resolve()) if reference_trades_path else None,
        "rows": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "auxiliary_setup_labels": LABEL_COLUMNS,
        "account_state_columns": account_columns,
        "utility_target_columns": utility_columns,
        "account_state_config": asdict(config),
        "notes": [
            "Setup labels are preserved as auxiliary targets for specialist structure.",
            "Account-state columns are generated from a reference account path when a trade log is provided.",
            "Challenge and funded targets are stage-aware surrogates for prop-firm-specific optimization.",
            "trade_challenge_utility remains an auxiliary scalar target for ranking candidate rows.",
        ],
    }


def build_label_report(frame: pd.DataFrame) -> Dict[str, object]:
    summary_by_setup = []
    for setup, label_col in zip(SETUPS, LABEL_COLUMNS):
        summary_by_setup.append(
            {
                "setup": setup,
                "positives": int(_safe_bool_series(frame[label_col]).sum()),
                "mean_utility_r": round(float(frame[f"utility_{setup}_r"].mean()), 6),
                "max_utility_r": round(float(frame[f"utility_{setup}_r"].max()), 6),
                "min_utility_r": round(float(frame[f"utility_{setup}_r"].min()), 6),
            }
        )
    return {
        "rows": int(len(frame)),
        "eligible_rows": int(_safe_bool_series(frame["model_sample_eligible"]).sum()),
        "reference_taken_rows": int(pd.to_numeric(frame["trade_reference_taken"], errors="coerce").fillna(0).sum()),
        "best_setup_counts": frame["utility_best_setup"].value_counts(dropna=False).to_dict(),
        "account_stage_counts": frame["account_stage"].value_counts(dropna=False).to_dict(),
        "trade_challenge_utility": {
            "mean": round(float(frame["trade_challenge_utility"].mean()), 6),
            "median": round(float(frame["trade_challenge_utility"].median()), 6),
            "positive_rate": round(float((frame["trade_challenge_utility"] > 0.0).mean()), 6),
        },
        "by_setup": summary_by_setup,
    }


def write_json(path: Optional[Path], payload: Dict[str, object]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_utility_dataset_command(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    reference_trades_path = Path(args.reference_trades) if args.reference_trades else None

    fundedhive_config = fundedhive_backtest_defaults()
    config = AccountStateConfig(
        starting_balance=float(args.starting_balance),
        profit_target_pct=float(fundedhive_config["profit_target_pct"]),
        min_profitable_days=int(fundedhive_config["min_profitable_days"]),
        max_daily_loss_pct=float(fundedhive_config["max_daily_loss_pct"]),
        max_total_drawdown_pct=float(fundedhive_config["max_total_drawdown_pct"]),
        max_trades_per_day=int(args.max_trades_per_day),
        risk_per_trade_pct=float(args.risk_per_trade_pct),
        initial_account_stage=str(args.account_stage),
    )

    frame = _read_csv(input_path, args.max_rows)
    _validate_columns(frame)
    reference_trade_lookup = _build_reference_trade_lookup(reference_trades_path)
    enriched = _compute_trade_utility_columns(
        frame,
        target_atr_multiple=float(args.target_atr_multiple),
        stop_atr_multiple=float(args.stop_atr_multiple),
        round_trip_cost_points=float(args.round_trip_cost_points),
    )
    enriched = _apply_reference_account_state(enriched, reference_trade_lookup, config)
    enriched = _annotate_account_stage(enriched)
    enriched = _compute_stage_targets(
        enriched,
        profit_target_pct=config.profit_target_pct,
        min_profitable_days=config.min_profitable_days,
        max_daily_loss_pct=config.max_daily_loss_pct,
        max_total_drawdown_pct=config.max_total_drawdown_pct,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(
        output_path,
        index=False,
        compression="gzip" if str(output_path).endswith(".gz") else None,
    )

    schema_payload = build_dataset_schema(
        input_path=input_path,
        output_path=output_path,
        frame=enriched,
        config=config,
        reference_trades_path=reference_trades_path,
    )
    label_report = build_label_report(enriched)
    label_report["account_state_summary"] = enriched.attrs.get("account_state_summary", {})
    label_report["reference_trade_count"] = int(enriched.attrs.get("reference_trade_count", 0))

    schema_output = Path(args.schema_output) if args.schema_output else None
    label_report_output = Path(args.label_report_output) if args.label_report_output else None
    write_json(schema_output, schema_payload)
    write_json(label_report_output, label_report)

    print(output_path)
    if schema_output:
        print(schema_output)
    if label_report_output:
        print(label_report_output)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a frontier utility dataset with account-state features.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build a utility-enriched dataset export.")
    build.add_argument("--input", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--reference-trades")
    build.add_argument("--schema-output")
    build.add_argument("--label-report-output")
    build.add_argument("--max-rows", type=int, default=0)
    build.add_argument("--starting-balance", type=float, default=100000.0)
    build.add_argument("--max-trades-per-day", type=int, default=3)
    build.add_argument("--risk-per-trade-pct", type=float, default=0.25)
    build.add_argument("--account-stage", choices=["challenge", "funded"], default="challenge")
    build.add_argument("--target-atr-multiple", type=float, default=1.25)
    build.add_argument("--stop-atr-multiple", type=float, default=0.75)
    build.add_argument("--round-trip-cost-points", type=float, default=1.50)
    build.set_defaults(func=build_utility_dataset_command)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
