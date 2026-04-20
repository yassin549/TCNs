import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from prop_firm_rules import evaluate_propfirm_path


DEFAULT_ARTIFACT_DIR = Path("artifacts/specialist_tcns/us100_session_refined")
DEFAULT_DOC_PATH = Path("docs/current_baseline_us100_session_refined.md")


def load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def round_or_none(value: Optional[float], digits: int = 6) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def compute_longest_streak(values: List[float], predicate) -> int:
    best = 0
    current = 0
    for value in values:
        if predicate(value):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def safe_std(values: List[float], ddof: int = 1) -> Optional[float]:
    if len(values) <= ddof:
        return None
    return float(np.std(values, ddof=ddof))


def build_trade_streaks(trades: pd.DataFrame) -> List[Dict[str, object]]:
    streaks: List[Dict[str, object]] = []
    current_sign = 0
    current_length = 0

    for pnl_r in trades["pnl_r"].tolist():
        sign = 1 if pnl_r > 0 else -1 if pnl_r < 0 else 0
        if sign == 0:
            current_sign = 0
            current_length = 0
        elif sign == current_sign:
            current_length += 1
        else:
            current_sign = sign
            current_length = 1
        streaks.append(
            {
                "sign": current_sign,
                "length": current_length,
            }
        )
    return streaks


def build_streak_condition_table(
    trades: pd.DataFrame,
    streaks: List[Dict[str, object]],
    sign: int,
    max_streak: int = 10,
    forward_window: int = 5,
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    pnl_values = trades["pnl_r"].tolist()

    for streak_length in range(1, max_streak + 1):
        next_trade_values: List[float] = []
        forward_window_values: List[float] = []
        for index in range(len(trades) - 1):
            state = streaks[index]
            if state["sign"] != sign or int(state["length"]) != streak_length:
                continue
            next_trade_values.append(float(pnl_values[index + 1]))
            forward_end = min(len(pnl_values), index + 1 + forward_window)
            forward_window_values.append(
                float(np.mean(pnl_values[index + 1:forward_end]))
            )

        if not next_trade_values:
            continue

        label = "win" if sign > 0 else "loss"
        results.append(
            {
                "prior_streak_type": label,
                "prior_streak_length": streak_length,
                "samples": len(next_trade_values),
                "next_trade_win_probability": round_or_none(
                    float(np.mean([value > 0 for value in next_trade_values]))
                ),
                "next_trade_expectancy_r": round_or_none(float(np.mean(next_trade_values))),
                "next_trade_median_r": round_or_none(float(np.median(next_trade_values))),
                f"next_{forward_window}_trade_avg_r": round_or_none(
                    float(np.mean(forward_window_values))
                ),
            }
        )
    return results


def build_day_start_state_table(
    trades: pd.DataFrame,
    daily_returns_pct: List[float],
    daily_dates: List[str],
    starting_balance: float,
    profit_target_pct: float,
    max_total_drawdown_pct: float,
    min_profitable_days: int,
) -> List[Dict[str, object]]:
    if trades.empty:
        return []

    working = trades.copy()
    working["session_date_utc"] = pd.to_datetime(working["session_date_utc"]).dt.date
    working = working.sort_values(["entry_timestamp", "exit_timestamp", "entry_index"]).reset_index(drop=True)
    trade_streaks = build_trade_streaks(working)
    working["streak_sign"] = [item["sign"] for item in trade_streaks]
    working["streak_length"] = [item["length"] for item in trade_streaks]

    day_end = (
        working.groupby("session_date_utc", as_index=False)
        .agg(
            ending_streak_sign=("streak_sign", "last"),
            ending_streak_length=("streak_length", "last"),
        )
        .sort_values("session_date_utc")
        .reset_index(drop=True)
    )
    day_end["next_session_date_utc"] = day_end["session_date_utc"].shift(-1)
    trailing_by_start_date = {
        str(row.next_session_date_utc): {
            "streak_sign": int(row.ending_streak_sign),
            "streak_length": int(row.ending_streak_length),
        }
        for row in day_end.itertuples(index=False)
        if row.next_session_date_utc is not None
    }

    starts: List[Dict[str, object]] = []
    for start_index, start_date in enumerate(daily_dates):
        trailing = trailing_by_start_date.get(
            start_date,
            {"streak_sign": 0, "streak_length": 0},
        )
        evaluation = evaluate_propfirm_path(
            daily_returns_pct=daily_returns_pct[start_index:],
            starting_balance=starting_balance,
            profit_target_pct=profit_target_pct,
            max_total_drawdown_pct=max_total_drawdown_pct,
            min_profitable_days=min_profitable_days,
        )
        starts.append(
            {
                "start_date": start_date,
                "prior_streak_sign": int(trailing["streak_sign"]),
                "prior_streak_length": int(trailing["streak_length"]),
                "passed": bool(evaluation["passed"]),
                "days_to_pass": evaluation["days_to_pass"],
            }
        )

    if not starts:
        return []

    starts_frame = pd.DataFrame(starts)
    starts_frame["prior_streak_type"] = starts_frame["prior_streak_sign"].map(
        {1: "win", -1: "loss", 0: "flat_or_unknown"}
    )
    grouped = (
        starts_frame.groupby(["prior_streak_type", "prior_streak_length"], as_index=False)
        .agg(
            starts=("start_date", "size"),
            pass_rate=("passed", "mean"),
            pass_count=("passed", "sum"),
            avg_days_to_pass=("days_to_pass", "mean"),
            median_days_to_pass=("days_to_pass", "median"),
        )
        .sort_values(["pass_rate", "starts", "prior_streak_length"], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    return json.loads(grouped.to_json(orient="records"))


def build_daily_frame(trades: pd.DataFrame) -> pd.DataFrame:
    daily = (
        trades.groupby("session_date_utc", as_index=False)
        .agg(
            trades=("pnl_r", "size"),
            day_pnl_r=("pnl_r", "sum"),
            day_pnl_cash=("pnl_cash", "sum"),
            avg_trade_r=("pnl_r", "mean"),
            win_rate=("pnl_r", lambda s: float((s > 0).mean())),
            balance_start=("balance_before", "first"),
            balance_end=("balance_after", "last"),
        )
        .sort_values("session_date_utc")
        .reset_index(drop=True)
    )
    daily["day_return_pct"] = (
        (daily["balance_end"] / daily["balance_start"]) - 1.0
    ) * 100.0
    return daily


def build_daily_returns_pct(
    daily: pd.DataFrame,
    starting_balance: float,
) -> List[float]:
    previous_balance = starting_balance
    daily_returns_pct: List[float] = []
    for balance_end in daily["balance_end"]:
        day_return_pct = ((float(balance_end) / previous_balance) - 1.0) * 100.0
        daily_returns_pct.append(day_return_pct)
        previous_balance = float(balance_end)
    return daily_returns_pct


def compute_drawdown_timeline(
    daily: pd.DataFrame,
    starting_balance: float,
) -> Dict[str, object]:
    running_peak = starting_balance
    running_peak_date = None
    max_drawdown_pct = 0.0
    trough_date = None
    peak_before_trough_date = None

    for row in daily.itertuples(index=False):
        balance_end = float(row.balance_end)
        trade_day = row.session_date_utc
        if balance_end > running_peak:
            running_peak = balance_end
            running_peak_date = trade_day
        drawdown_pct = ((balance_end / running_peak) - 1.0) * 100.0
        if drawdown_pct < max_drawdown_pct:
            max_drawdown_pct = drawdown_pct
            trough_date = trade_day
            peak_before_trough_date = running_peak_date

    return {
        "max_drawdown_pct": round(abs(max_drawdown_pct), 4),
        "drawdown_trough_date": str(trough_date) if trough_date is not None else None,
        "peak_before_trough_date": (
            str(peak_before_trough_date)
            if peak_before_trough_date is not None
            else None
        ),
    }


def rolling_start_pass_metrics(
    daily_returns_pct: List[float],
    start_dates: List[str],
    starting_balance: float,
    profit_target_pct: float,
    max_total_drawdown_pct: float,
    min_profitable_days: int,
) -> Dict[str, object]:
    pass_windows = []

    for start_index, start_date in enumerate(start_dates):
        evaluation = evaluate_propfirm_path(
            daily_returns_pct=daily_returns_pct[start_index:],
            starting_balance=starting_balance,
            profit_target_pct=profit_target_pct,
            max_total_drawdown_pct=max_total_drawdown_pct,
            min_profitable_days=min_profitable_days,
        )
        if not evaluation["passed"]:
            continue
        days_to_pass = int(evaluation["days_to_pass"])
        pass_windows.append(
            {
                "start_date": start_date,
                "days_to_pass": days_to_pass,
                "end_date": start_dates[start_index + days_to_pass - 1],
            }
        )

    pass_days = [window["days_to_pass"] for window in pass_windows]
    return {
        "pass_rate": round_or_none(safe_div(len(pass_windows), len(start_dates))),
        "pass_count": len(pass_windows),
        "start_count": len(start_dates),
        "min_days_to_pass": min(pass_days) if pass_days else None,
        "avg_days_to_pass": (
            round_or_none(float(np.mean(pass_days)), 2) if pass_days else None
        ),
        "median_days_to_pass": (
            int(np.median(pass_days)) if pass_days else None
        ),
        "pass_windows": pass_windows,
    }


def bootstrap_pass_metrics(
    daily_returns_pct: List[float],
    starting_balance: float,
    profit_target_pct: float,
    max_total_drawdown_pct: float,
    min_profitable_days: int,
    horizons: List[int],
    simulations: int,
    seed: int,
) -> Dict[str, Dict[str, Optional[float]]]:
    rng = np.random.default_rng(seed)
    results: Dict[str, Dict[str, Optional[float]]] = {}

    if not daily_returns_pct:
        for horizon in horizons:
            results[str(horizon)] = {
                "pass_probability": 0.0,
                "median_days_to_pass": None,
                "min_days_to_pass": None,
                "max_days_to_pass": None,
            }
        return results

    for horizon in horizons:
        pass_days: List[int] = []
        for _ in range(simulations):
            sampled_returns = []
            for day in range(1, horizon + 1):
                day_return_pct = float(rng.choice(daily_returns_pct))
                sampled_returns.append(day_return_pct)
                evaluation = evaluate_propfirm_path(
                    daily_returns_pct=sampled_returns,
                    starting_balance=starting_balance,
                    profit_target_pct=profit_target_pct,
                    max_total_drawdown_pct=max_total_drawdown_pct,
                    min_profitable_days=min_profitable_days,
                )
                if evaluation["passed"]:
                    pass_days.append(day)
                    break
                if evaluation["breached_total_drawdown"]:
                    break

        results[str(horizon)] = {
            "pass_probability": round_or_none(
                safe_div(len(pass_days), simulations)
            ),
            "avg_days_to_pass": (
                round_or_none(float(np.mean(pass_days)), 2) if pass_days else None
            ),
            "median_days_to_pass": (
                int(np.median(pass_days)) if pass_days else None
            ),
            "min_days_to_pass": min(pass_days) if pass_days else None,
            "max_days_to_pass": max(pass_days) if pass_days else None,
        }

    return results


def summarize_group(frame: pd.DataFrame, group_column: str) -> List[Dict[str, object]]:
    grouped = (
        frame.groupby(group_column, as_index=False)
        .agg(
            trades=("pnl_r", "size"),
            win_rate=("pnl_r", lambda s: float((s > 0).mean())),
            expectancy_r=("pnl_r", "mean"),
            total_r=("pnl_r", "sum"),
            pnl_cash=("pnl_cash", "sum"),
            avg_probability=("probability", "mean"),
            avg_hold_bars=("bars_held", "mean"),
        )
        .sort_values("total_r", ascending=False)
        .reset_index(drop=True)
    )
    return json.loads(grouped.to_json(orient="records"))


def best_and_worst_trade(trades: pd.DataFrame) -> Dict[str, Dict[str, object]]:
    best_row = trades.loc[trades["pnl_cash"].idxmax()]
    worst_row = trades.loc[trades["pnl_cash"].idxmin()]

    def serialize_trade(row: pd.Series) -> Dict[str, object]:
        return {
            "entry_timestamp": str(row["entry_timestamp"]),
            "exit_timestamp": str(row["exit_timestamp"]),
            "session_date_utc": str(row["session_date_utc"]),
            "setup": row["setup"],
            "market_session": row["market_session"],
            "session_phase": row["session_phase"],
            "pnl_cash": round_or_none(float(row["pnl_cash"]), 2),
            "pnl_r": round_or_none(float(row["pnl_r"])),
            "probability": round_or_none(float(row["probability"])),
            "bars_held": int(row["bars_held"]),
            "exit_reason": row["exit_reason"],
        }

    return {
        "best_trade": serialize_trade(best_row),
        "worst_trade": serialize_trade(worst_row),
    }


def serialize_days(frame: pd.DataFrame, limit: int, ascending: bool) -> List[Dict[str, object]]:
    subset = (
        frame.sort_values("day_pnl_cash", ascending=ascending)
        .head(limit)
        .copy()
    )
    subset["session_date_utc"] = subset["session_date_utc"].astype(str)
    return json.loads(subset.to_json(orient="records"))


def format_pct(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}%"


def format_currency(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.{digits}f}"


def format_ratio(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}R"


def validate_canonical_summary(summary: Dict[str, object], policy: Dict[str, object], artifact_dir: Path) -> None:
    execution_mode = str(summary.get("execution_mode") or "")
    policy_selection = str(summary.get("policy_selection") or policy.get("selection") or "")
    is_frontier_artifact = "frontier" in artifact_dir.name.lower() or "frontier" in policy_selection.lower()
    if is_frontier_artifact and execution_mode == "raw_candidate_path":
        raise ValueError(
            f"Refusing to generate a frontier benchmark report from raw candidate outputs: {artifact_dir}"
        )


def infer_execution_metadata(summary: Dict[str, object], policy: Dict[str, object]) -> Dict[str, object]:
    policy_selection = summary.get("policy_selection") or policy.get("selection")
    execution_mode = summary.get("execution_mode")
    if execution_mode is None and str(policy_selection).startswith("frontier"):
        execution_mode = "frontier_managed"
    raw_source_summary = summary.get("raw_source_summary") or policy.get("raw_source_summary")
    return {
        "execution_mode": execution_mode,
        "policy_selection": policy_selection,
        "raw_source_summary": raw_source_summary,
    }


def write_markdown(report: Dict[str, object], output_path: Path) -> None:
    baseline = report["baseline"]
    training = report.get("training_snapshot") or {}
    analysis_scope = report.get("analysis_scope") or {}
    performance = report["performance"]
    distribution = report["distribution"]
    challenge = report["challenge"]
    daily = report["daily"]
    streaks = report["streaks"]
    start_timing = report["start_timing"]
    operating = report["operating_profile"]
    top_days = report["top_days"]
    bottom_days = report["bottom_days"]
    setup_breakdown = report["by_setup"]
    session_breakdown = report["by_market_session"]
    phase_breakdown = report["by_session_phase"]
    sequence = report["sequence"]
    challenge_metrics = report.get("challenge_metrics", {})
    skip_counts = operating.get("skip_counts", {})

    lines = [
        "# Current Baseline Report",
        "",
        f"Generated at `{report['generated_at_utc']}` from `{baseline['artifact_name']}`.",
        "",
        "## Baseline Snapshot",
        "",
        f"- Artifact: `{baseline['artifact_dir']}`",
        f"- Trade log: `{baseline['trades_path']}`",
        f"- Manager policy: `{baseline['policy_path']}`",
        f"- Dataset: `{baseline['dataset_path']}`",
        f"- Test split summary: `{baseline['summary_path']}`",
        f"- Execution mode: `{baseline.get('execution_mode')}`",
        f"- Policy selection: `{baseline.get('policy_selection')}`",
        f"- Raw source summary: `{baseline.get('raw_source_summary')}`",
    ]

    if training:
        lines.extend(
            [
                "",
                "## Training Snapshot",
                "",
                f"- Lookback: `{training['lookback']}` bars",
                f"- Feature count: `{training['feature_count']}`",
                f"- Train / val split: `{training['train_fraction']:.0%}` / `{training['val_fraction']:.0%}`",
                f"- Epochs: `{training['epochs']}`",
                f"- Batch size: `{training['batch_size']}`",
                f"- Negative ratio: `{training['negative_ratio']}`",
                f"- Channels: `{', '.join(str(value) for value in training['channels'])}`",
                f"- Hidden dim: `{training['hidden_dim']}`",
                f"- Dropout: `{training['dropout']}`",
            ]
        )

    if analysis_scope:
        lines.extend(
            [
                "",
                "## Evaluation Scope",
                "",
                f"- Rows analyzed: `{analysis_scope['rows_analyzed']:,}`",
                f"- Eligible test rows: `{analysis_scope['eligible_test_rows']:,}`",
                f"- Feature columns reported by analysis: `{len(analysis_scope['feature_columns'])}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Backtest Summary",
            "",
            f"- Trades: `{performance['trades']}`",
            f"- Active trading days: `{performance['trading_days']}`",
            f"- First trade date: `{performance['first_trade_date']}`",
            f"- Last trade date: `{performance['last_trade_date']}`",
            f"- Calendar span covered by active trades: `{performance['calendar_days_span']}` days",
            f"- Win rate: `{performance['win_rate']:.5f}`",
            f"- Loss rate: `{performance['loss_rate']:.5f}`",
            f"- Expectancy: `{performance['expectancy_r']:.6f}R` per trade",
            f"- Average R per trade: `{performance['average_r_per_trade']:.6f}R`",
            f"- Total R: `{performance['total_r']:.2f}R`",
            f"- Profit factor: `{performance['profit_factor']:.6f}`",
            f"- Average win: `{format_ratio(performance['avg_win_r'], 6)}`",
            f"- Average loss: `{format_ratio(performance['avg_loss_r'], 6)}`",
            f"- Realized payoff ratio: `{performance['payoff_ratio']:.6f}`" if performance["payoff_ratio"] is not None else "- Realized payoff ratio: `n/a`",
            f"- Average hold time: `{performance['average_hold_bars']:.6f}` bars",
            f"- Ending balance: `{format_currency(performance['ending_balance'])}`",
            f"- Return: `{performance['total_return_pct']:.4f}%`",
            f"- Max drawdown: `{performance['max_drawdown_pct']:.4f}%`",
            f"- Drawdown peak date: `{performance['peak_before_trough_date']}`",
            f"- Drawdown trough date: `{performance['drawdown_trough_date']}`",
            f"- Best trade: `{performance['best_trade']['session_date_utc']}` | `{performance['best_trade']['setup']}` | `{format_currency(performance['best_trade']['pnl_cash'])}` | `{format_ratio(performance['best_trade']['pnl_r'])}` | `{performance['best_trade']['exit_reason']}`",
            f"- Worst trade: `{performance['worst_trade']['session_date_utc']}` | `{performance['worst_trade']['setup']}` | `{format_currency(performance['worst_trade']['pnl_cash'])}` | `{format_ratio(performance['worst_trade']['pnl_r'])}` | `{performance['worst_trade']['exit_reason']}`",
        ]
    )

    lines.extend(
        [
            "",
            "## Distribution",
            "",
            f"- Median trade: `{distribution['median_trade_r']}`R",
            f"- Trade R std dev: `{distribution['trade_r_std']}`",
            f"- Mean daily return: `{distribution['daily_return_mean_pct']}`%",
            f"- Daily return std dev: `{distribution['daily_return_std_pct']}`%",
            f"- Daily Sharpe proxy: `{distribution['daily_sharpe_proxy']}`",
            f"- Daily Sortino proxy: `{distribution['daily_sortino_proxy']}`",
        ]
    )

    lines.extend(
        [
            "",
            "## Acceptance Metrics",
            "",
            f"- Pass probability 30 / 60 / 90: `{challenge_metrics.get('pass_probability_30')}` / `{challenge_metrics.get('pass_probability_60')}` / `{challenge_metrics.get('pass_probability_90')}`",
            f"- Median / avg days to pass: `{challenge_metrics.get('median_days_to_pass')}` / `{challenge_metrics.get('avg_days_to_pass')}`",
            f"- Profitable-day hit rate day 10 / 20: `{challenge_metrics.get('profitable_day_hit_rate_day_10')}` / `{challenge_metrics.get('profitable_day_hit_rate_day_20')}`",
            f"- Longest trade loss streak: `{challenge_metrics.get('longest_trade_loss_streak')}`",
            f"- Longest negative day streak: `{challenge_metrics.get('longest_negative_day_streak')}`",
            f"- Worst month return %: `{challenge_metrics.get('worst_month_return_pct')}`",
            f"- Loss cluster penalty: `{challenge_metrics.get('loss_cluster_penalty')}`",
            "",
            "## Prop-Firm Metrics",
            "",
            f"- Policy: `{challenge['policy_name']}`",
            f"- Profit target: `{challenge['profit_target_pct']:.2f}%`",
            f"- Minimum profitable days: `{challenge['min_profitable_days']}`",
            f"- Max total drawdown: `{challenge['max_total_drawdown_pct']:.2f}%`",
            f"- Max daily loss: `{challenge['max_daily_loss_pct']:.2f}%`",
            f"- Hard max loss per trade: `{challenge['max_loss_per_trade_pct']:.2f}%`",
            f"- Configured base risk per trade: `{challenge['configured_risk_per_trade_pct']:.2f}%`",
            f"- Actual test path passed: `{challenge['actual_path_passed']}`",
            f"- Days to pass on the recorded test path: `{challenge['actual_days_to_pass']}` active trading days",
            f"- Profitable days on the recorded test path: `{challenge['actual_profitable_days']}`",
            f"- Historical rolling-start pass rate: `{challenge['rolling_start']['pass_rate']:.6f}` ({challenge['rolling_start']['pass_count']}/{challenge['rolling_start']['start_count']})",
            f"- Fastest historical rolling-start pass: `{challenge['rolling_start']['min_days_to_pass']}` active trading days",
            f"- Average historical rolling-start pass: `{challenge['rolling_start']['avg_days_to_pass']}` active trading days",
            f"- Median historical rolling-start pass: `{challenge['rolling_start']['median_days_to_pass']}` active trading days",
            "- Bootstrap pass probabilities from active-day return resampling:",
        ]
    )

    for horizon, metrics in challenge["bootstrap"].items():
        lines.append(
            f"  - `{horizon}`-day horizon: pass probability `{metrics['pass_probability']:.6f}`, average pass day `{metrics['avg_days_to_pass']}`, median pass day `{metrics['median_days_to_pass']}`, min pass day `{metrics['min_days_to_pass']}`"
        )

    lines.extend(
        [
            "",
            "## Daily Consistency",
            "",
            f"- Profitable days: `{daily['profitable_days']}`",
            f"- Losing days: `{daily['losing_days']}`",
            f"- Positive day rate: `{daily['positive_day_rate']:.6f}`",
            f"- Average daily return: `{daily['average_day_return_pct']:.6f}%`",
            f"- Median daily return: `{daily['median_day_return_pct']:.6f}%`",
            f"- Best day: `{daily['best_day']['date']}` | `{format_currency(daily['best_day']['pnl_cash'])}` | `{format_ratio(daily['best_day']['pnl_r'])}` | `{format_pct(daily['best_day']['return_pct'], 4)}` | `{daily['best_day']['trades']}` trades",
            f"- Worst day: `{daily['worst_day']['date']}` | `{format_currency(daily['worst_day']['pnl_cash'])}` | `{format_ratio(daily['worst_day']['pnl_r'])}` | `{format_pct(daily['worst_day']['return_pct'], 4)}` | `{daily['worst_day']['trades']}` trades",
        ]
    )

    lines.extend(
        [
            "",
            "## Streaks",
            "",
            f"- Longest win streak: `{streaks['longest_trade_win_streak']}` trades",
            f"- Longest loss streak: `{streaks['longest_trade_loss_streak']}` trades",
            f"- Longest positive-day streak: `{streaks['longest_positive_day_streak']}` days",
            f"- Longest negative-day streak: `{streaks['longest_negative_day_streak']}` days",
        ]
    )

    lines.extend(["", "## Start Timing", ""])
    for row in start_timing[:10]:
        lines.append(
            f"- After `{row['prior_streak_type']}` streak `{int(row['prior_streak_length'])}`: `{int(row['starts'])}` starts, pass rate `{row['pass_rate']:.6f}`, average days to pass `{row['avg_days_to_pass']}`, median days to pass `{row['median_days_to_pass']}`"
        )

    lines.extend(
        [
            "",
            "## Operating Profile",
            "",
            f"- Average trades per day: `{operating['average_trades_per_day']:.6f}`",
            f"- Median trades per day: `{operating['median_trades_per_day']:.6f}`",
            f"- Days at max-trade cap: `{operating['days_at_trade_cap']}` / `{performance['trading_days']}`",
            f"- Capacity utilization on active days: `{operating['trade_cap_utilization_pct']:.4f}%`",
            f"- Skip counts: `cooldown={skip_counts.get('cooldown', 0)}`, `ineligible={skip_counts.get('ineligible', 0)}`, `session_end_buffer={skip_counts.get('session_end_buffer', 0)}`, `daily_trade_cap={skip_counts.get('daily_trade_cap', 0)}`, `allocator_low_utility={skip_counts.get('rejected_by_allocator_low_marginal_utility', 0)}`",
        ]
    )

    lines.extend(["", "## Breakdown By Setup", ""])
    for row in setup_breakdown:
        lines.append(
            f"- `{row['setup']}`: trades `{int(row['trades'])}`, win rate `{row['win_rate']:.6f}`, expectancy `{row['expectancy_r']:.6f}R`, total `{row['total_r']:.6f}R`, PnL `{format_currency(row['pnl_cash'])}`"
        )

    lines.extend(["", "## Breakdown By Market Session", ""])
    for row in session_breakdown:
        lines.append(
            f"- `{row['market_session']}`: trades `{int(row['trades'])}`, win rate `{row['win_rate']:.6f}`, expectancy `{row['expectancy_r']:.6f}R`, total `{row['total_r']:.6f}R`"
        )

    lines.extend(["", "## Breakdown By Session Phase", ""])
    for row in phase_breakdown:
        lines.append(
            f"- `{row['session_phase']}`: trades `{int(row['trades'])}`, win rate `{row['win_rate']:.6f}`, expectancy `{row['expectancy_r']:.6f}R`, total `{row['total_r']:.6f}R`"
        )

    lines.extend(["", "## Best Days", ""])
    for row in top_days:
        lines.append(
            f"- `{row['session_date_utc']}`: `{format_currency(row['day_pnl_cash'])}` | `{format_ratio(row['day_pnl_r'])}` | `{format_pct(row['day_return_pct'], 4)}` | `{int(row['trades'])}` trades"
        )

    lines.extend(["", "## Worst Days", ""])
    for row in bottom_days:
        lines.append(
            f"- `{row['session_date_utc']}`: `{format_currency(row['day_pnl_cash'])}` | `{format_ratio(row['day_pnl_r'])}` | `{format_pct(row['day_return_pct'], 4)}` | `{int(row['trades'])}` trades"
        )

    lines.extend(["", "## Sequence Diagnostics", ""])
    for label, rows in (
        ("After Loss Streaks", sequence["after_loss_streaks"]),
        ("After Win Streaks", sequence["after_win_streaks"]),
    ):
        lines.extend(["", f"### {label}", ""])
        for row in rows:
            next_avg_key = next(
                key for key in row.keys() if key.startswith("next_") and key.endswith("_trade_avg_r")
            )
            lines.append(
                f"- Prior `{row['prior_streak_type']}` streak `{int(row['prior_streak_length'])}`: `{int(row['samples'])}` samples, next-trade win probability `{row['next_trade_win_probability']:.6f}`, next-trade expectancy `{row['next_trade_expectancy_r']:.6f}R`, `{next_avg_key}` `{row[next_avg_key]:.6f}R`"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `days_to_pass` counts active trading days with at least one completed trade, not calendar days.",
            "- Prop-firm pass logic now requires both the profit target and the configured minimum profitable-day count.",
            "- Rolling-start pass rate is conservative because later start dates have less remaining sample history available to reach the target.",
            "- Bootstrap pass probabilities assume active-day returns are independently resampled from the recorded test distribution.",
            "- This report can be regenerated from the trade log and policy file, so it remains comparable after future model changes.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_training_snapshot(training_summary: Optional[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not training_summary:
        return None
    train_config = training_summary.get("train_config", {})
    model_reports = training_summary.get("model_reports", {})
    feature_count = None
    if model_reports:
        first_report = next(iter(model_reports.values()))
        feature_count = len(first_report.get("feature_columns", []))
    return {
        "lookback": train_config.get("lookback", 0),
        "train_fraction": train_config.get("train_fraction", 0.0),
        "val_fraction": train_config.get("val_fraction", 0.0),
        "epochs": train_config.get("epochs", 0),
        "batch_size": train_config.get("batch_size", 0),
        "negative_ratio": train_config.get("negative_ratio", train_config.get("train_negative_ratio", 0.0)),
        "channels": train_config.get("channels", []),
        "hidden_dim": train_config.get("hidden_dim", 0),
        "dropout": train_config.get("dropout", 0.0),
        "feature_count": feature_count or 0,
    }


def build_empty_report(
    artifact_dir: Path,
    artifact_name: str,
    trades_path: Path,
    policy_path: Path,
    summary_path: Path,
    training_summary_path: Path,
    analysis_report_path: Path,
    summary: Dict[str, object],
    policy: Dict[str, object],
    training_summary: Optional[Dict[str, object]],
    analysis_report: Optional[Dict[str, object]],
) -> Dict[str, object]:
    config = policy["backtest_config"]
    summary_metrics = summary["summary"]
    execution_meta = infer_execution_metadata(summary, policy)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "artifact_name": artifact_name,
            "artifact_dir": str(artifact_dir.resolve()),
            "trades_path": str(trades_path.resolve()),
            "policy_path": str(policy_path.resolve()),
            "summary_path": str(summary_path.resolve()),
            "training_summary_path": str(training_summary_path.resolve()),
            "analysis_report_path": str(analysis_report_path.resolve()),
            "dataset_path": summary.get("dataset"),
            "execution_mode": execution_meta["execution_mode"],
            "policy_selection": execution_meta["policy_selection"],
            "raw_source_summary": execution_meta["raw_source_summary"],
        },
        "training_snapshot": build_training_snapshot(training_summary),
        "analysis_scope": (
            {
                "rows_analyzed": analysis_report["analysis_scope"]["rows_analyzed"],
                "eligible_test_rows": analysis_report["analysis_scope"]["eligible_test_rows"],
                "feature_columns": analysis_report["analysis_scope"]["feature_columns"],
            }
            if analysis_report and "analysis_scope" in analysis_report
            else None
        ),
        "performance": {
            "trades": 0,
            "trading_days": 0,
            "first_trade_date": None,
            "last_trade_date": None,
            "calendar_days_span": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "expectancy_r": 0.0,
            "average_r_per_trade": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "avg_win_r": None,
            "avg_loss_r": None,
            "payoff_ratio": None,
            "average_hold_bars": 0.0,
            "ending_balance": float(config["starting_balance"]),
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "peak_before_trough_date": None,
            "drawdown_trough_date": None,
            "best_trade": {
                "session_date_utc": None,
                "setup": None,
                "pnl_cash": None,
                "pnl_r": None,
                "exit_reason": None,
            },
            "worst_trade": {
                "session_date_utc": None,
                "setup": None,
                "pnl_cash": None,
                "pnl_r": None,
                "exit_reason": None,
            },
        },
        "distribution": {
            "median_trade_r": None,
            "trade_r_std": None,
            "daily_return_mean_pct": 0.0,
            "daily_return_std_pct": None,
            "daily_sharpe_proxy": None,
            "daily_sortino_proxy": None,
        },
        "challenge": {
            "policy_name": str(config.get("policy_name", "prop_policy")),
            "profit_target_pct": round_or_none(float(config["profit_target_pct"]), 2),
            "min_profitable_days": int(config.get("min_profitable_days", 0)),
            "max_total_drawdown_pct": round_or_none(float(config["max_total_drawdown_pct"]), 2),
            "max_daily_loss_pct": round_or_none(float(config["max_daily_loss_pct"]), 2),
            "max_loss_per_trade_pct": round_or_none(float(config.get("max_loss_per_trade_pct", config.get("risk_per_trade_pct", 0.0))), 2),
            "configured_risk_per_trade_pct": round_or_none(float(config.get("risk_per_trade_pct", 0.0)), 2),
            "actual_path_passed": False,
            "actual_days_to_pass": None,
            "actual_profitable_days": 0,
            "rolling_start": {"pass_rate": 0.0, "pass_count": 0, "start_count": 0, "min_days_to_pass": None, "avg_days_to_pass": None, "median_days_to_pass": None, "pass_windows": []},
            "bootstrap": {str(h): {"pass_probability": 0.0, "avg_days_to_pass": None, "median_days_to_pass": None, "min_days_to_pass": None, "max_days_to_pass": None} for h in [30, 60, 66, 90, 120]},
        },
        "challenge_metrics": {
            "pass_probability_30": summary_metrics.get("pass_probability_30", 0.0),
            "pass_probability_60": summary_metrics.get("pass_probability_60", 0.0),
            "pass_probability_90": summary_metrics.get("pass_probability_90", 0.0),
            "median_days_to_pass": summary_metrics.get("median_days_to_pass"),
            "avg_days_to_pass": summary_metrics.get("avg_days_to_pass"),
            "profitable_day_hit_rate_day_10": summary_metrics.get("profitable_day_hit_rate_day_10", 0.0),
            "profitable_day_hit_rate_day_20": summary_metrics.get("profitable_day_hit_rate_day_20", 0.0),
            "longest_trade_loss_streak": summary_metrics.get("longest_trade_loss_streak", 0),
            "longest_negative_day_streak": summary_metrics.get("longest_negative_day_streak", 0),
            "worst_month_return_pct": summary_metrics.get("worst_month_return_pct", 0.0),
            "loss_cluster_penalty": summary_metrics.get("loss_cluster_penalty", 0.0),
        },
        "daily": {
            "profitable_days": 0,
            "losing_days": 0,
            "flat_days": 0,
            "positive_day_rate": 0.0,
            "average_day_return_pct": 0.0,
            "median_day_return_pct": 0.0,
            "best_day": {
                "date": None,
                "pnl_cash": None,
                "pnl_r": None,
                "return_pct": None,
                "trades": 0,
            },
            "worst_day": {
                "date": None,
                "pnl_cash": None,
                "pnl_r": None,
                "return_pct": None,
                "trades": 0,
            },
        },
        "streaks": {
            "longest_trade_win_streak": 0,
            "longest_trade_loss_streak": 0,
            "longest_positive_day_streak": 0,
            "longest_negative_day_streak": 0,
        },
        "start_timing": [],
        "operating_profile": {
            "average_trades_per_day": 0.0,
            "median_trades_per_day": 0.0,
            "days_at_trade_cap": 0,
            "trade_cap_utilization_pct": 0.0,
            "skip_counts": summary_metrics.get("skip_counts", {}),
        },
        "by_setup": [],
        "by_market_session": [],
        "by_session_phase": [],
        "top_days": [],
        "bottom_days": [],
        "sequence": {
            "after_loss_streaks": [],
            "after_win_streaks": [],
        },
    }


def write_empty_markdown(report: Dict[str, object], output_path: Path) -> None:
    baseline = report["baseline"]
    performance = report["performance"]
    challenge = report["challenge"]
    operating = report["operating_profile"]
    lines = [
        "# Current Baseline Report",
        "",
        f"Generated at `{report['generated_at_utc']}` from `{baseline['artifact_name']}`.",
        "",
        "## Baseline Snapshot",
        "",
        f"- Artifact: `{baseline['artifact_dir']}`",
        f"- Trade log: `{baseline['trades_path']}`",
        f"- Manager policy: `{baseline['policy_path']}`",
        f"- Dataset: `{baseline['dataset_path']}`",
        "",
        "## Backtest Summary",
        "",
        f"- Trades: `{performance['trades']}`",
        f"- Active trading days: `{performance['trading_days']}`",
        f"- Ending balance: `{format_currency(performance['ending_balance'])}`",
        f"- Return: `{performance['total_return_pct']:.4f}%`",
        f"- Max drawdown: `{performance['max_drawdown_pct']:.4f}%`",
        "",
        "## Challenge Summary",
        "",
        f"- Policy: `{challenge['policy_name']}`",
        f"- Passed: `{challenge['actual_path_passed']}`",
        f"- Days to pass: `{challenge['actual_days_to_pass']}`",
        f"- Profitable days: `{challenge['actual_profitable_days']}`",
        "",
        "## Operating Notes",
        "",
        "- No trades were accepted on the recorded replay path for this artifact.",
        f"- Skip counts: `{operating['skip_counts']}`",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a reproducible baseline report from a backtest trade log."
    )
    parser.add_argument(
        "--artifact-dir",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="Artifact directory containing the baseline outputs.",
    )
    parser.add_argument(
        "--artifact-name",
        default="specialist_tcns/us100_session_refined",
        help="Human-readable name for the baseline artifact.",
    )
    parser.add_argument(
        "--trades-path",
        help="Path to the backtest trade log. Defaults to <artifact-dir>/backtest_trades.csv.gz.",
    )
    parser.add_argument(
        "--policy-path",
        help="Path to the manager policy JSON. Defaults to <artifact-dir>/manager_policy.json.",
    )
    parser.add_argument(
        "--summary-path",
        help="Path to the backtest summary JSON. Defaults to <artifact-dir>/backtest_summary.json.",
    )
    parser.add_argument(
        "--training-summary-path",
        help="Path to the training summary JSON. Defaults to <artifact-dir>/training_summary.json.",
    )
    parser.add_argument(
        "--analysis-report-path",
        help="Path to the analysis report JSON. Defaults to <artifact-dir>/analysis_report.json.",
    )
    parser.add_argument(
        "--output-json",
        help="Output path for the machine-readable report. Defaults to <artifact-dir>/baseline_report.json.",
    )
    parser.add_argument(
        "--output-md",
        default=str(DEFAULT_DOC_PATH),
        help="Output path for the markdown report.",
    )
    parser.add_argument(
        "--bootstrap-simulations",
        type=int,
        default=2000,
        help="Number of bootstrap simulations per horizon.",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=7,
        help="Random seed for bootstrap pass probability estimates.",
    )
    parser.add_argument(
        "--bootstrap-horizons",
        type=int,
        nargs="+",
        default=[30, 60, 66, 90, 120],
        help="Active-trading-day horizons for bootstrap pass probabilities.",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    trades_path = (
        Path(args.trades_path)
        if args.trades_path
        else artifact_dir / "backtest_trades.csv.gz"
    )
    policy_path = (
        Path(args.policy_path)
        if args.policy_path
        else artifact_dir / "manager_policy.json"
    )
    summary_path = (
        Path(args.summary_path)
        if args.summary_path
        else artifact_dir / "backtest_summary.json"
    )
    training_summary_path = (
        Path(args.training_summary_path)
        if args.training_summary_path
        else artifact_dir / "training_summary.json"
    )
    analysis_report_path = (
        Path(args.analysis_report_path)
        if args.analysis_report_path
        else artifact_dir / "analysis_report.json"
    )
    output_json = (
        Path(args.output_json)
        if args.output_json
        else artifact_dir / "baseline_report.json"
    )
    output_md = Path(args.output_md)

    trades = pd.read_csv(trades_path, compression="gzip")

    policy = load_json(policy_path)
    summary = load_json(summary_path)
    validate_canonical_summary(summary, policy, artifact_dir)
    training_summary = (
        load_json(training_summary_path) if training_summary_path.exists() else None
    )
    analysis_report = (
        load_json(analysis_report_path) if analysis_report_path.exists() else None
    )

    if trades.empty:
        report = build_empty_report(
            artifact_dir=artifact_dir,
            artifact_name=args.artifact_name,
            trades_path=trades_path,
            policy_path=policy_path,
            summary_path=summary_path,
            training_summary_path=training_summary_path,
            analysis_report_path=analysis_report_path,
            summary=summary,
            policy=policy,
            training_summary=training_summary,
            analysis_report=analysis_report,
        )
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        write_empty_markdown(report, output_md)
        print(f"Wrote {output_json}")
        print(f"Wrote {output_md}")
        return 0

    trades["entry_timestamp"] = pd.to_datetime(trades["entry_timestamp"], utc=True)
    trades["exit_timestamp"] = pd.to_datetime(trades["exit_timestamp"], utc=True)
    trades["session_date_utc"] = pd.to_datetime(trades["session_date_utc"]).dt.date
    trades = trades.sort_values(
        ["entry_timestamp", "exit_timestamp", "entry_index"]
    ).reset_index(drop=True)

    config = policy["backtest_config"]
    summary_metrics = summary["summary"]
    execution_meta = infer_execution_metadata(summary, policy)
    starting_balance = float(config["starting_balance"])
    policy_name = str(config.get("policy_name", "legacy_prop_policy"))
    min_profitable_days = int(config.get("min_profitable_days", 0))
    max_loss_per_trade_pct = float(
        config.get("max_loss_per_trade_pct", config.get("risk_per_trade_pct", 0.0))
    )
    configured_risk_per_trade_pct = float(config.get("risk_per_trade_pct", 0.0))

    wins = trades.loc[trades["pnl_r"] > 0, "pnl_r"]
    losses = trades.loc[trades["pnl_r"] < 0, "pnl_r"]
    daily = build_daily_frame(trades)
    daily_returns_pct = build_daily_returns_pct(daily, starting_balance)
    drawdown = compute_drawdown_timeline(daily, starting_balance)
    trade_extremes = best_and_worst_trade(trades)
    trade_streaks = build_trade_streaks(trades)

    actual_evaluation = evaluate_propfirm_path(
        daily_returns_pct=daily_returns_pct,
        starting_balance=starting_balance,
        profit_target_pct=float(config["profit_target_pct"]),
        max_total_drawdown_pct=float(config["max_total_drawdown_pct"]),
        min_profitable_days=min_profitable_days,
    )

    rolling_start = rolling_start_pass_metrics(
        daily_returns_pct=daily_returns_pct,
        start_dates=[str(value) for value in daily["session_date_utc"]],
        starting_balance=starting_balance,
        profit_target_pct=float(config["profit_target_pct"]),
        max_total_drawdown_pct=float(config["max_total_drawdown_pct"]),
        min_profitable_days=min_profitable_days,
    )
    bootstrap = bootstrap_pass_metrics(
        daily_returns_pct=daily_returns_pct,
        starting_balance=starting_balance,
        profit_target_pct=float(config["profit_target_pct"]),
        max_total_drawdown_pct=float(config["max_total_drawdown_pct"]),
        min_profitable_days=min_profitable_days,
        horizons=args.bootstrap_horizons,
        simulations=args.bootstrap_simulations,
        seed=args.bootstrap_seed,
    )

    best_day_row = daily.loc[daily["day_pnl_cash"].idxmax()]
    worst_day_row = daily.loc[daily["day_pnl_cash"].idxmin()]
    days_at_trade_cap = int((daily["trades"] >= int(config["max_trades_per_day"])).sum())
    max_trade_capacity = len(daily) * int(config["max_trades_per_day"])
    trade_r_values = trades["pnl_r"].tolist()
    daily_return_std = safe_std(daily_returns_pct)
    downside_daily_returns = [value for value in daily_returns_pct if value < 0.0]
    downside_std = safe_std(downside_daily_returns) if downside_daily_returns else None
    start_timing = build_day_start_state_table(
        trades=trades,
        daily_returns_pct=daily_returns_pct,
        daily_dates=[str(value) for value in daily["session_date_utc"]],
        starting_balance=starting_balance,
        profit_target_pct=float(config["profit_target_pct"]),
        max_total_drawdown_pct=float(config["max_total_drawdown_pct"]),
        min_profitable_days=min_profitable_days,
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "artifact_name": args.artifact_name,
            "artifact_dir": str(artifact_dir.resolve()),
            "trades_path": str(trades_path.resolve()),
            "policy_path": str(policy_path.resolve()),
            "summary_path": str(summary_path.resolve()),
            "training_summary_path": str(training_summary_path.resolve()),
            "analysis_report_path": str(analysis_report_path.resolve()),
            "dataset_path": summary.get("dataset"),
            "execution_mode": execution_meta["execution_mode"],
            "policy_selection": execution_meta["policy_selection"],
            "raw_source_summary": execution_meta["raw_source_summary"],
        },
        "training_snapshot": build_training_snapshot(training_summary),
        "analysis_scope": (
            {
                "rows_analyzed": analysis_report["analysis_scope"]["rows_analyzed"],
                "eligible_test_rows": analysis_report["analysis_scope"]["eligible_test_rows"],
                "feature_columns": analysis_report["analysis_scope"]["feature_columns"],
            }
            if analysis_report and "analysis_scope" in analysis_report
            else None
        ),
        "performance": {
            "trades": int(summary_metrics["trades"]),
            "trading_days": int(summary_metrics["trading_days"]),
            "first_trade_date": str(daily["session_date_utc"].iloc[0]),
            "last_trade_date": str(daily["session_date_utc"].iloc[-1]),
            "calendar_days_span": int(
                (daily["session_date_utc"].iloc[-1] - daily["session_date_utc"].iloc[0]).days
                + 1
            ),
            "win_rate": round_or_none(float(summary_metrics["win_rate"])),
            "loss_rate": round_or_none(float((trades["pnl_r"] < 0).mean())),
            "expectancy_r": round_or_none(float(summary_metrics["expectancy_r"])),
            "average_r_per_trade": round_or_none(float(np.mean(trade_r_values))),
            "total_r": round_or_none(float(summary_metrics["total_r"])),
            "profit_factor": round_or_none(float(summary_metrics["profit_factor"])),
            "avg_win_r": round_or_none(float(wins.mean())) if len(wins) else None,
            "avg_loss_r": round_or_none(float(losses.mean())) if len(losses) else None,
            "payoff_ratio": (
                round_or_none(abs(float(wins.mean()) / float(losses.mean())))
                if len(wins) and len(losses) and float(losses.mean()) != 0.0
                else None
            ),
            "average_hold_bars": round_or_none(
                float(summary_metrics["average_hold_bars"])
            ),
            "ending_balance": round_or_none(
                float(summary_metrics["ending_balance"]), 2
            ),
            "total_return_pct": round_or_none(
                float(summary_metrics["total_return_pct"]), 4
            ),
            "max_drawdown_pct": round_or_none(
                float(summary_metrics["max_drawdown_pct"]), 4
            ),
            "peak_before_trough_date": drawdown["peak_before_trough_date"],
            "drawdown_trough_date": drawdown["drawdown_trough_date"],
            "best_trade": trade_extremes["best_trade"],
            "worst_trade": trade_extremes["worst_trade"],
        },
        "distribution": {
            "median_trade_r": round_or_none(float(np.median(trade_r_values))),
            "trade_r_std": round_or_none(safe_std(trade_r_values)),
            "daily_return_mean_pct": round_or_none(float(np.mean(daily_returns_pct))),
            "daily_return_std_pct": round_or_none(daily_return_std),
            "daily_sharpe_proxy": (
                round_or_none(float(np.mean(daily_returns_pct)) / daily_return_std, 4)
                if daily_return_std not in (None, 0.0)
                else None
            ),
            "daily_sortino_proxy": (
                round_or_none(float(np.mean(daily_returns_pct)) / downside_std, 4)
                if downside_std not in (None, 0.0)
                else None
            ),
        },
        "challenge": {
            "policy_name": policy_name,
            "profit_target_pct": round_or_none(float(config["profit_target_pct"]), 2),
            "min_profitable_days": min_profitable_days,
            "max_total_drawdown_pct": round_or_none(
                float(config["max_total_drawdown_pct"]), 2
            ),
            "max_daily_loss_pct": round_or_none(
                float(config["max_daily_loss_pct"]), 2
            ),
            "max_loss_per_trade_pct": round_or_none(max_loss_per_trade_pct, 2),
            "configured_risk_per_trade_pct": round_or_none(
                configured_risk_per_trade_pct,
                2,
            ),
            "actual_path_passed": bool(actual_evaluation["passed"]),
            "actual_days_to_pass": actual_evaluation["days_to_pass"],
            "actual_profitable_days": int(actual_evaluation["profitable_days"]),
            "rolling_start": rolling_start,
            "bootstrap": bootstrap,
        },
        "challenge_metrics": {
            "pass_probability_30": summary_metrics.get("pass_probability_30", bootstrap.get("30", {}).get("pass_probability", 0.0)),
            "pass_probability_60": summary_metrics.get("pass_probability_60", bootstrap.get("60", {}).get("pass_probability", 0.0)),
            "pass_probability_90": summary_metrics.get("pass_probability_90", bootstrap.get("90", {}).get("pass_probability", 0.0)),
            "median_days_to_pass": summary_metrics.get("median_days_to_pass", rolling_start.get("median_days_to_pass")),
            "avg_days_to_pass": summary_metrics.get("avg_days_to_pass", rolling_start.get("avg_days_to_pass")),
            "profitable_day_hit_rate_day_10": summary_metrics.get("profitable_day_hit_rate_day_10", 0.0),
            "profitable_day_hit_rate_day_20": summary_metrics.get("profitable_day_hit_rate_day_20", 0.0),
            "longest_trade_loss_streak": summary_metrics.get("longest_trade_loss_streak", compute_longest_streak(trades["pnl_r"].tolist(), lambda value: value < 0)),
            "longest_negative_day_streak": summary_metrics.get("longest_negative_day_streak", compute_longest_streak(daily["day_pnl_cash"].tolist(), lambda value: value < 0)),
            "worst_month_return_pct": summary_metrics.get("worst_month_return_pct", round_or_none(float(daily.groupby(daily["session_date_utc"].astype(str).str.slice(0, 7))["day_return_pct"].sum().min()), 6)),
            "loss_cluster_penalty": summary_metrics.get("loss_cluster_penalty", round_or_none(float((daily["day_pnl_cash"] < 0).mean() * abs(daily.loc[daily["day_pnl_cash"] < 0, "day_return_pct"].mean())) + 0.10 * compute_longest_streak(daily["day_pnl_cash"].tolist(), lambda value: value < 0), 6)),
        },
        "daily": {
            "profitable_days": int((daily["day_pnl_cash"] > 0).sum()),
            "losing_days": int((daily["day_pnl_cash"] < 0).sum()),
            "flat_days": int((daily["day_pnl_cash"] == 0).sum()),
            "positive_day_rate": round_or_none(
                float((daily["day_pnl_cash"] > 0).mean())
            ),
            "average_day_return_pct": round_or_none(float(np.mean(daily_returns_pct))),
            "median_day_return_pct": round_or_none(float(np.median(daily_returns_pct))),
            "best_day": {
                "date": str(best_day_row["session_date_utc"]),
                "pnl_cash": round_or_none(float(best_day_row["day_pnl_cash"]), 2),
                "pnl_r": round_or_none(float(best_day_row["day_pnl_r"])),
                "return_pct": round_or_none(float(best_day_row["day_return_pct"]), 4),
                "trades": int(best_day_row["trades"]),
                "win_rate": round_or_none(float(best_day_row["win_rate"])),
            },
            "worst_day": {
                "date": str(worst_day_row["session_date_utc"]),
                "pnl_cash": round_or_none(float(worst_day_row["day_pnl_cash"]), 2),
                "pnl_r": round_or_none(float(worst_day_row["day_pnl_r"])),
                "return_pct": round_or_none(float(worst_day_row["day_return_pct"]), 4),
                "trades": int(worst_day_row["trades"]),
                "win_rate": round_or_none(float(worst_day_row["win_rate"])),
            },
        },
        "streaks": {
            "longest_trade_win_streak": compute_longest_streak(
                trades["pnl_r"].tolist(),
                lambda value: value > 0,
            ),
            "longest_trade_loss_streak": compute_longest_streak(
                trades["pnl_r"].tolist(),
                lambda value: value < 0,
            ),
            "longest_positive_day_streak": compute_longest_streak(
                daily["day_pnl_cash"].tolist(),
                lambda value: value > 0,
            ),
            "longest_negative_day_streak": compute_longest_streak(
                daily["day_pnl_cash"].tolist(),
                lambda value: value < 0,
            ),
        },
        "start_timing": start_timing,
        "operating_profile": {
            "average_trades_per_day": round_or_none(float(daily["trades"].mean())),
            "median_trades_per_day": round_or_none(float(daily["trades"].median())),
            "days_at_trade_cap": days_at_trade_cap,
            "trade_cap_utilization_pct": round_or_none(
                safe_div(float(len(trades)), float(max_trade_capacity)) * 100.0,
                4,
            ),
            "skip_counts": summary_metrics["skip_counts"],
        },
        "by_setup": summarize_group(trades, "setup"),
        "by_market_session": summarize_group(trades, "market_session"),
        "by_session_phase": summarize_group(trades, "session_phase"),
        "top_days": serialize_days(daily, limit=10, ascending=False),
        "bottom_days": serialize_days(daily, limit=10, ascending=True),
        "sequence": {
            "after_loss_streaks": build_streak_condition_table(
                trades=trades,
                streaks=trade_streaks,
                sign=-1,
            ),
            "after_win_streaks": build_streak_condition_table(
                trades=trades,
                streaks=trade_streaks,
                sign=1,
            ),
        },
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, output_md)

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
