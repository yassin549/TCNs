import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


STARTING_BALANCE_DEFAULT = 100000.0


def load_trades(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["entry_timestamp"] = pd.to_datetime(frame["entry_timestamp"], utc=True)
    frame["exit_timestamp"] = pd.to_datetime(frame["exit_timestamp"], utc=True)
    frame["session_date"] = pd.to_datetime(frame["session_date_utc"]).dt.date
    frame["month"] = frame["entry_timestamp"].dt.to_period("M").astype(str)
    return frame.sort_values(["entry_timestamp", "exit_timestamp"]).reset_index(drop=True)


def longest_streak(mask: List[bool], dates: pd.Series, entries: pd.Series) -> Dict[str, object]:
    best_len = 0
    best_start = None
    best_end = None
    current_len = 0
    current_start = None
    for index, flag in enumerate(mask):
        if flag:
            if current_len == 0:
                current_start = index
            current_len += 1
            if current_len > best_len:
                best_len = current_len
                best_start = current_start
                best_end = index
        else:
            current_len = 0
            current_start = None
    if best_len == 0 or best_start is None or best_end is None:
        return {"length": 0}
    return {
        "length": int(best_len),
        "start_entry": str(entries.iloc[best_start]),
        "end_entry": str(entries.iloc[best_end]),
        "start_date": str(dates.iloc[best_start]),
        "end_date": str(dates.iloc[best_end]),
    }


def profit_factor(series: pd.Series) -> float:
    gross_loss = abs(float(series.loc[series < 0.0].sum()))
    if gross_loss == 0.0:
        return float("nan")
    return float(series.loc[series > 0.0].sum()) / gross_loss


def aggregate_groups(frame: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
    grouped = (
        frame.groupby(group_cols, dropna=False)
        .agg(
            trades=("pnl_r", "size"),
            wins=("pnl_r", lambda values: int((values > 0.0).sum())),
            losses=("pnl_r", lambda values: int((values < 0.0).sum())),
            win_rate=("pnl_r", lambda values: float((values > 0.0).mean())),
            expectancy_r=("pnl_r", "mean"),
            total_r=("pnl_r", "sum"),
            avg_probability=("probability", "mean"),
            avg_hold_bars=("bars_held", "mean"),
            total_pnl_cash=("pnl_cash", "sum"),
            profit_factor=("pnl_r", profit_factor),
        )
        .reset_index()
    )
    return grouped


def build_daily_frame(frame: pd.DataFrame, starting_balance: float) -> pd.DataFrame:
    daily = (
        frame.groupby("session_date", dropna=False)
        .agg(
            pnl_r=("pnl_r", "sum"),
            pnl_cash=("pnl_cash", "sum"),
            trades=("pnl_r", "size"),
            win_rate=("pnl_r", lambda values: float((values > 0.0).mean())),
        )
        .reset_index()
        .sort_values("session_date")
        .reset_index(drop=True)
    )
    daily["equity"] = starting_balance + daily["pnl_cash"].cumsum()
    daily["equity_peak"] = daily["equity"].cummax()
    daily["drawdown_pct"] = (daily["equity"] / daily["equity_peak"] - 1.0) * 100.0
    return daily


def compute_probability_buckets(frame: pd.DataFrame) -> List[Dict[str, object]]:
    ranked = frame[["probability", "pnl_r"]].copy()
    ranked["bucket"] = pd.qcut(ranked["probability"], 10, labels=False, duplicates="drop")
    output = (
        ranked.groupby("bucket")
        .agg(
            trades=("pnl_r", "size"),
            min_probability=("probability", "min"),
            max_probability=("probability", "max"),
            avg_probability=("probability", "mean"),
            win_rate=("pnl_r", lambda values: float((values > 0.0).mean())),
            expectancy_r=("pnl_r", "mean"),
            total_r=("pnl_r", "sum"),
        )
        .reset_index()
        .sort_values("bucket")
    )
    output["bucket"] = output["bucket"] + 1
    return output.to_dict("records")


def compute_context_probability_buckets(frame: pd.DataFrame) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for keys, group in frame.groupby(["setup", "market_session", "session_phase"], dropna=False):
        if len(group) < 10:
            continue
        ranked = group[["probability", "pnl_r", "pnl_cash", "session_date"]].copy()
        ranked["bucket"] = pd.qcut(ranked["probability"], 5, labels=False, duplicates="drop")
        ranked = ranked.dropna(subset=["bucket"])
        if ranked.empty:
            continue
        bucket_daily = (
            ranked.groupby(["bucket", "session_date"], dropna=False)
            .agg(day_pnl_r=("pnl_r", "sum"), day_pnl_cash=("pnl_cash", "sum"))
            .reset_index()
        )
        bucket_summary = (
            ranked.groupby("bucket", dropna=False)
            .agg(
                trades=("pnl_r", "size"),
                win_rate=("pnl_r", lambda values: float((values > 0.0).mean())),
                expectancy_r=("pnl_r", "mean"),
                total_r=("pnl_r", "sum"),
                min_probability=("probability", "min"),
                max_probability=("probability", "max"),
            )
            .reset_index()
            .sort_values("bucket")
        )
        for row in bucket_summary.to_dict("records"):
            bucket = row["bucket"]
            bucket_days = bucket_daily.loc[bucket_daily["bucket"] == bucket, "day_pnl_r"].astype(float).tolist()
            negative_days = [value for value in bucket_days if value < 0.0]
            negative_rate = len(negative_days) / len(bucket_days) if bucket_days else 0.0
            avg_negative = abs(float(np.mean(negative_days))) if negative_days else 0.0
            rows.append(
                {
                    "setup": keys[0],
                    "market_session": keys[1],
                    "session_phase": keys[2],
                    "bucket_rank": int(row["bucket"]) + 1,
                    "trades": int(row["trades"]),
                    "win_rate": float(row["win_rate"]),
                    "expectancy_r": float(row["expectancy_r"]),
                    "total_r": float(row["total_r"]),
                    "pass_utility_contribution": float(row["total_r"]),
                    "drawdown_contribution": float(abs(sum(value for value in bucket_days if value < 0.0))),
                    "loss_cluster_penalty": negative_rate * avg_negative,
                    "min_probability": float(row["min_probability"]),
                    "max_probability": float(row["max_probability"]),
                }
            )
    return rows


def compute_after_streak_expectancy(frame: pd.DataFrame, max_streak: int = 5) -> List[Dict[str, object]]:
    pnl = frame["pnl_r"].tolist()
    rows: List[Dict[str, object]] = []
    for streak_type in ["win", "loss"]:
        for streak_len in range(1, max_streak + 1):
            next_values: List[float] = []
            current_streak = 0
            for index, value in enumerate(pnl[:-1]):
                matches = value > 0.0 if streak_type == "win" else value < 0.0
                current_streak = current_streak + 1 if matches else 0
                if current_streak == streak_len:
                    next_values.append(float(pnl[index + 1]))
            if next_values:
                rows.append(
                    {
                        "streak_type": streak_type,
                        "streak_len": streak_len,
                        "samples": len(next_values),
                        "next_expectancy_r": float(np.mean(next_values)),
                        "next_win_rate": float(np.mean(np.array(next_values) > 0.0)),
                    }
                )
    return rows


def build_report(frame: pd.DataFrame, starting_balance: float) -> Dict[str, object]:
    daily = build_daily_frame(frame, starting_balance)
    by_setup = aggregate_groups(frame, ["setup"]).sort_values("expectancy_r", ascending=False)
    by_session = aggregate_groups(frame, ["market_session"]).sort_values("expectancy_r", ascending=False)
    by_phase = aggregate_groups(frame, ["session_phase"]).sort_values("expectancy_r", ascending=False)
    by_context = aggregate_groups(frame, ["setup", "market_session", "session_phase"])
    by_context_best = by_context.sort_values(
        ["expectancy_r", "total_r", "trades"], ascending=[False, False, False]
    ).head(10)
    by_context_worst = by_context.sort_values(
        ["expectancy_r", "total_r", "trades"], ascending=[True, True, False]
    ).head(10)
    by_exit = (
        frame.groupby("exit_reason", dropna=False)
        .agg(
            trades=("pnl_r", "size"),
            win_rate=("pnl_r", lambda values: float((values > 0.0).mean())),
            expectancy_r=("pnl_r", "mean"),
            total_r=("pnl_r", "sum"),
        )
        .reset_index()
        .sort_values("trades", ascending=False)
    )
    monthly = (
        frame.groupby("month", dropna=False)
        .agg(
            trades=("pnl_r", "size"),
            win_rate=("pnl_r", lambda values: float((values > 0.0).mean())),
            expectancy_r=("pnl_r", "mean"),
            total_r=("pnl_r", "sum"),
            total_pnl_cash=("pnl_cash", "sum"),
        )
        .reset_index()
        .sort_values("month")
    )
    summary = {
        "trades": int(len(frame)),
        "trading_days": int(frame["session_date"].nunique()),
        "win_rate": float((frame["pnl_r"] > 0.0).mean()),
        "loss_rate": float((frame["pnl_r"] < 0.0).mean()),
        "expectancy_r": float(frame["pnl_r"].mean()),
        "total_r": float(frame["pnl_r"].sum()),
        "profit_factor": profit_factor(frame["pnl_r"]),
        "average_hold_bars": float(frame["bars_held"].mean()),
        "average_risk_cash": float(frame["risk_cash"].mean()),
        "ending_balance": float(frame["balance_after"].iloc[-1]),
        "total_return_pct": float((frame["balance_after"].iloc[-1] / starting_balance - 1.0) * 100.0),
        "max_drawdown_pct": float(abs(daily["drawdown_pct"].min())),
        "first_trade_timestamp": str(frame["entry_timestamp"].iloc[0]),
        "last_trade_timestamp": str(frame["entry_timestamp"].iloc[-1]),
    }
    streaks = {
        "longest_trade_win_streak": longest_streak(
            (frame["pnl_r"] > 0.0).tolist(), frame["session_date"], frame["entry_timestamp"]
        ),
        "longest_trade_loss_streak": longest_streak(
            (frame["pnl_r"] < 0.0).tolist(), frame["session_date"], frame["entry_timestamp"]
        ),
        "longest_positive_day_streak": longest_streak(
            (daily["pnl_r"] > 0.0).tolist(), daily["session_date"], daily["session_date"]
        ),
        "longest_negative_day_streak": longest_streak(
            (daily["pnl_r"] < 0.0).tolist(), daily["session_date"], daily["session_date"]
        ),
    }
    return {
        "summary": summary,
        "streaks": streaks,
        "by_setup": by_setup.to_dict("records"),
        "by_session": by_session.to_dict("records"),
        "by_phase": by_phase.to_dict("records"),
        "best_contexts": by_context_best.to_dict("records"),
        "worst_contexts": by_context_worst.to_dict("records"),
        "by_exit_reason": by_exit.to_dict("records"),
        "best_days": daily.sort_values(["pnl_r", "pnl_cash"], ascending=False).head(10).to_dict("records"),
        "worst_days": daily.sort_values(["pnl_r", "pnl_cash"], ascending=True).head(10).to_dict("records"),
        "monthly": monthly.to_dict("records"),
        "probability_buckets": compute_probability_buckets(frame),
        "context_probability_buckets": compute_context_probability_buckets(frame),
        "after_streak_expectancy": compute_after_streak_expectancy(frame),
    }


def _render_group_lines(title: str, rows: List[Dict[str, object]], key_columns: List[str]) -> List[str]:
    lines = [f"## {title}", ""]
    for row in rows:
        label = " / ".join(str(row[key]) for key in key_columns)
        lines.append(
            f"- `{label}`: trades `{row['trades']}`, win rate `{row['win_rate']:.4f}`, "
            f"expectancy `{row['expectancy_r']:.6f}R`, total `{row['total_r']:.6f}R`, "
            f"profit factor `{row['profit_factor']:.6f}`"
        )
    lines.append("")
    return lines


def write_markdown(report: Dict[str, object], output_path: Path) -> None:
    summary = report["summary"]
    streaks = report["streaks"]
    lines = [
        "# Backtest Diagnostics",
        "",
        f"- Trades: `{summary['trades']}`",
        f"- Trading days: `{summary['trading_days']}`",
        f"- Win rate: `{summary['win_rate']:.6f}`",
        f"- Expectancy: `{summary['expectancy_r']:.6f}R`",
        f"- Total R: `{summary['total_r']:.6f}`",
        f"- Profit factor: `{summary['profit_factor']:.6f}`",
        f"- Ending balance: `{summary['ending_balance']:.2f}`",
        f"- Return: `{summary['total_return_pct']:.4f}%`",
        f"- Max drawdown: `{summary['max_drawdown_pct']:.4f}%`",
        "",
        "## Streaks",
        "",
        f"- Longest trade win streak: `{streaks['longest_trade_win_streak']['length']}`",
        f"- Longest trade loss streak: `{streaks['longest_trade_loss_streak']['length']}`",
        f"- Longest positive day streak: `{streaks['longest_positive_day_streak']['length']}`",
        f"- Longest negative day streak: `{streaks['longest_negative_day_streak']['length']}`",
        "",
    ]
    lines.extend(_render_group_lines("By Setup", report["by_setup"], ["setup"]))
    lines.extend(_render_group_lines("By Market Session", report["by_session"], ["market_session"]))
    lines.extend(_render_group_lines("By Session Phase", report["by_phase"], ["session_phase"]))
    lines.extend(_render_group_lines("Best Contexts", report["best_contexts"], ["setup", "market_session", "session_phase"]))
    lines.extend(_render_group_lines("Worst Contexts", report["worst_contexts"], ["setup", "market_session", "session_phase"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize detailed backtest diagnostics from a trade log.")
    parser.add_argument("--trades", required=True, help="Path to the backtest trades CSV or CSV.GZ.")
    parser.add_argument("--json-output", required=True, help="Path to write the diagnostics JSON.")
    parser.add_argument("--markdown-output", help="Optional path to write a markdown summary.")
    parser.add_argument(
        "--starting-balance",
        type=float,
        default=STARTING_BALANCE_DEFAULT,
        help="Starting account balance used for return and drawdown calculations.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    trades = load_trades(Path(args.trades))
    report = build_report(trades, starting_balance=float(args.starting_balance))
    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if args.markdown_output:
        write_markdown(report, Path(args.markdown_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
