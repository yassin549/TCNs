from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from frontier_account_state import AccountStateConfig, AccountStateTracker
from frontier_allocator import AllocationConfig, allocate_day, build_policy_payload, determine_kill_switch_state
from prop_firm_rules import evaluate_propfirm_path, fundedhive_backtest_defaults


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(value):
        return default
    return float(value)


def _account_stage(account_state: Dict[str, object], account_config: AccountStateConfig) -> str:
    stage = str(account_state.get("account_stage", getattr(account_config, "initial_account_stage", "challenge")))
    return "funded" if stage == "funded" else "challenge"


def _stage_risk_pct(candidate: Dict[str, object], account_state: Dict[str, object], account_config: AccountStateConfig, allocation_config: AllocationConfig) -> float:
    stage = _account_stage(account_state, account_config)
    drawdown_pct = float(account_state.get("account_drawdown_pct", 0.0))
    distance_to_target = float(account_state.get("account_distance_to_target_pct", 0.0))
    daily_budget_remaining = float(account_state.get("day_loss_budget_remaining_pct", account_config.max_daily_loss_pct))
    total_budget_remaining = float(account_state.get("total_drawdown_budget_remaining_pct", account_config.max_total_drawdown_pct))
    if stage == "challenge":
        risk_pct = allocation_config.challenge_base_risk_pct
        if (
            distance_to_target >= 6.0
            and drawdown_pct <= 1.5
            and daily_budget_remaining >= 3.0
            and total_budget_remaining >= 6.0
        ):
            risk_pct = allocation_config.challenge_max_risk_pct
        elif distance_to_target <= 2.0 and float(account_state.get("account_profitable_days_remaining", 0.0)) <= 0.0:
            risk_pct = allocation_config.challenge_near_target_risk_pct
        elif total_budget_remaining <= 2.0 or daily_budget_remaining <= 1.0:
            risk_pct = min(risk_pct, allocation_config.challenge_near_target_risk_pct)
        return float(risk_pct)

    risk_pct = allocation_config.funded_base_risk_pct
    if float(candidate.get("predicted_funded_expected_return_20d", 0.0)) >= 0.20 and drawdown_pct <= 1.5:
        risk_pct = allocation_config.funded_max_risk_pct
    if drawdown_pct >= allocation_config.drawdown_soft_pct or total_budget_remaining <= 2.0:
        risk_pct = allocation_config.funded_defensive_risk_pct
    return float(risk_pct)


def load_candidates(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, compression="gzip" if str(path).endswith(".gz") else None)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["session_date_utc"] = pd.to_datetime(frame["session_date_utc"]).dt.date
    return frame.sort_values(["timestamp"]).reset_index(drop=True)


def _daily_returns_from_cash(day_pnl_cash: List[float], starting_balance: float) -> List[float]:
    balance = float(starting_balance)
    daily_returns = []
    for pnl_cash in day_pnl_cash:
        if balance <= 0.0:
            daily_returns.append(0.0)
            balance += pnl_cash
            continue
        daily_returns.append(float(pnl_cash) / balance * 100.0)
        balance += pnl_cash
    return daily_returns


def _rolling_start_metrics(daily_returns_pct: List[float], config: AccountStateConfig) -> Dict[str, object]:
    evaluations = [
        evaluate_propfirm_path(
            daily_returns_pct=daily_returns_pct[start_idx:],
            starting_balance=config.starting_balance,
            profit_target_pct=config.profit_target_pct,
            max_total_drawdown_pct=config.max_total_drawdown_pct,
            min_profitable_days=config.min_profitable_days,
        )
        for start_idx in range(len(daily_returns_pct))
    ]
    pass_flags = [float(item["passed"]) for item in evaluations]
    pass_days = [float(item["days_to_pass"]) for item in evaluations if item["days_to_pass"] is not None]
    return {
        "pass_rate": round(float(np.mean(pass_flags)) if pass_flags else 0.0, 6),
        "avg_days_to_pass": round(float(np.mean(pass_days)), 6) if pass_days else None,
        "median_days_to_pass": round(float(np.median(pass_days)), 6) if pass_days else None,
    }


def _bootstrap_metrics(daily_returns_pct: List[float], config: AccountStateConfig, horizons: List[int], simulations: int, seed: int) -> Dict[str, Dict[str, Optional[float]]]:
    if not daily_returns_pct:
        return {str(h): {"pass_probability": 0.0, "median_days_to_pass": None} for h in horizons}
    rng = np.random.default_rng(seed)
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for horizon in horizons:
        pass_days: List[int] = []
        for _ in range(simulations):
            sampled = []
            for day in range(1, horizon + 1):
                sampled.append(float(rng.choice(daily_returns_pct)))
                evaluation = evaluate_propfirm_path(
                    daily_returns_pct=sampled,
                    starting_balance=config.starting_balance,
                    profit_target_pct=config.profit_target_pct,
                    max_total_drawdown_pct=config.max_total_drawdown_pct,
                    min_profitable_days=config.min_profitable_days,
                )
                if evaluation["passed"]:
                    pass_days.append(day)
                    break
                if evaluation["breached_total_drawdown"]:
                    break
        out[str(horizon)] = {
            "pass_probability": round(len(pass_days) / simulations, 6),
            "median_days_to_pass": int(np.median(pass_days)) if pass_days else None,
        }
    return out


def _longest_negative_streak(values: List[float]) -> int:
    best = 0
    current = 0
    for value in values:
        if value < 0.0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _profitable_days_within_horizon(daily_returns_pct: List[float], horizon: int) -> int:
    return int(sum(1 for value in daily_returns_pct[:horizon] if value > 0.0))


def _build_challenge_metrics(
    daily_returns_pct: List[float],
    daily_dates: List[object],
    config: AccountStateConfig,
    bootstrap_simulations: int,
    bootstrap_seed: int,
) -> Dict[str, object]:
    rolling = _rolling_start_metrics(daily_returns_pct, config)
    bootstrap = _bootstrap_metrics(
        daily_returns_pct,
        config,
        horizons=[30, 60, 90],
        simulations=bootstrap_simulations,
        seed=bootstrap_seed,
    )
    if not daily_returns_pct:
        return {
            "pass_probability_30": 0.0,
            "pass_probability_60": 0.0,
            "pass_probability_90": 0.0,
            "median_days_to_pass": None,
            "avg_days_to_pass": None,
            "profitable_day_hit_rate_day_10": 0.0,
            "profitable_day_hit_rate_day_20": 0.0,
            "longest_negative_day_streak": 0,
            "loss_cluster_penalty": 0.0,
            "worst_month_return_pct": 0.0,
            "rolling_start": rolling,
            "bootstrap": bootstrap,
        }
    profitable_day_hit_10 = []
    profitable_day_hit_20 = []
    for start_index in range(len(daily_returns_pct)):
        trailing = daily_returns_pct[start_index:]
        profitable_day_hit_10.append(float(_profitable_days_within_horizon(trailing, 10) >= config.min_profitable_days))
        profitable_day_hit_20.append(float(_profitable_days_within_horizon(trailing, 20) >= config.min_profitable_days))
    month_returns: Dict[str, float] = defaultdict(float)
    for trade_day, day_return in zip(daily_dates, daily_returns_pct):
        month_returns[str(trade_day)[:7]] += float(day_return)
    negative_days = [value for value in daily_returns_pct if value < 0.0]
    negative_day_rate = len(negative_days) / len(daily_returns_pct)
    avg_negative = abs(float(np.mean(negative_days))) if negative_days else 0.0
    loss_cluster_penalty = negative_day_rate * avg_negative + 0.10 * _longest_negative_streak(daily_returns_pct)
    return {
        "pass_probability_30": round(float(bootstrap["30"]["pass_probability"]), 6),
        "pass_probability_60": round(float(bootstrap["60"]["pass_probability"]), 6),
        "pass_probability_90": round(float(bootstrap["90"]["pass_probability"]), 6),
        "median_days_to_pass": rolling["median_days_to_pass"],
        "avg_days_to_pass": rolling["avg_days_to_pass"],
        "profitable_day_hit_rate_day_10": round(float(np.mean(profitable_day_hit_10)), 6),
        "profitable_day_hit_rate_day_20": round(float(np.mean(profitable_day_hit_20)), 6),
        "longest_negative_day_streak": int(_longest_negative_streak(daily_returns_pct)),
        "loss_cluster_penalty": round(float(loss_cluster_penalty), 6),
        "worst_month_return_pct": round(float(min(month_returns.values())) if month_returns else 0.0, 6),
        "rolling_start": rolling,
        "bootstrap": bootstrap,
    }


def replay_candidates(
    candidates: pd.DataFrame,
    account_config: AccountStateConfig,
    allocation_config: AllocationConfig,
) -> Tuple[List[Dict[str, object]], Dict[str, int], Dict[str, object]]:
    tracker = AccountStateTracker(account_config)
    trade_rows: List[Dict[str, object]] = []
    skip_counts = defaultdict(int)
    accepted_setups = defaultdict(int)
    kill_switch_day_counts = defaultdict(int)
    grouped = candidates.groupby("session_date_utc", sort=True)
    for session_date, day_frame in grouped:
        day_candidates = []
        start_state = tracker.observe_day(session_date)
        kill_switch_day_counts[determine_kill_switch_state(start_state, allocation_config)] += 1
        if float(start_state.get("account_drawdown_pct", 0.0)) >= allocation_config.drawdown_hard_pct:
            skip_counts["total_drawdown_lock"] += int(len(day_frame))
            continue
        for row in day_frame.to_dict("records"):
            row["state_account_drawdown_pct"] = start_state["account_drawdown_pct"]
            row["state_account_distance_to_target_pct"] = start_state["account_distance_to_target_pct"]
            row["state_account_profitable_days_remaining"] = start_state["account_profitable_days_remaining"]
            row["state_kill_switch_state"] = determine_kill_switch_state(start_state, allocation_config)
            day_candidates.append(row)
        accepted, rejected = allocate_day(day_candidates, start_state, allocation_config)
        for rejected_row in rejected:
            skip_counts[str(rejected_row["allocator_decision"])] += 1
        for accepted_row in accepted:
            balance_before = tracker.state.balance
            risk_pct = _stage_risk_pct(accepted_row, start_state, account_config, allocation_config)
            risk_cash = balance_before * (risk_pct / 100.0)
            pnl_r = _safe_float(accepted_row.get("trade_realized_pnl_r"))
            pnl_cash = risk_cash * pnl_r
            state_after = tracker.apply_trade(session_date, pnl_cash=pnl_cash, pnl_r=pnl_r)
            accepted_setups[str(accepted_row["chosen_setup"])] += 1
            trade_rows.append(
                {
                    "setup": accepted_row["chosen_setup"],
                    "account_stage": _account_stage(start_state, account_config),
                    "probability": accepted_row["probability"],
                    "predicted_frontier_score": accepted_row["predicted_frontier_score"],
                    "predicted_trade_utility": accepted_row["predicted_trade_utility"],
                    "predicted_challenge_pass_prob_5d": accepted_row.get("predicted_challenge_pass_prob_5d", 0.0),
                    "predicted_challenge_pass_prob_10d": accepted_row.get("predicted_challenge_pass_prob_10d", 0.0),
                    "predicted_challenge_pass_prob_20d": accepted_row.get("predicted_challenge_pass_prob_20d", 0.0),
                    "predicted_challenge_fail_prob_5d": accepted_row.get("predicted_challenge_fail_prob_5d", 0.0),
                    "predicted_challenge_fail_prob_10d": accepted_row.get("predicted_challenge_fail_prob_10d", 0.0),
                    "predicted_challenge_expected_days_to_resolution": accepted_row.get("predicted_challenge_expected_days_to_resolution", 0.0),
                    "predicted_challenge_distance_to_target_delta": accepted_row.get("predicted_challenge_distance_to_target_delta", 0.0),
                    "predicted_challenge_daily_loss_budget_consumption": accepted_row.get("predicted_challenge_daily_loss_budget_consumption", 0.0),
                    "predicted_challenge_total_drawdown_budget_consumption": accepted_row.get("predicted_challenge_total_drawdown_budget_consumption", 0.0),
                    "predicted_funded_expected_return_5d": accepted_row.get("predicted_funded_expected_return_5d", 0.0),
                    "predicted_funded_expected_return_20d": accepted_row.get("predicted_funded_expected_return_20d", 0.0),
                    "predicted_funded_breach_risk_5d": accepted_row.get("predicted_funded_breach_risk_5d", 0.0),
                    "predicted_funded_breach_risk_20d": accepted_row.get("predicted_funded_breach_risk_20d", 0.0),
                    "predicted_funded_expected_drawdown": accepted_row.get("predicted_funded_expected_drawdown", 0.0),
                    "predicted_funded_expected_payout_growth": accepted_row.get("predicted_funded_expected_payout_growth", 0.0),
                    "session_date_utc": session_date,
                    "market_session": accepted_row["market_session"],
                    "session_phase": accepted_row["session_phase"],
                    "entry_timestamp": accepted_row["timestamp"],
                    "exit_timestamp": accepted_row["timestamp"],
                    "entry_index": int(accepted_row["bar_index_in_segment"]),
                    "exit_index": int(accepted_row["bar_index_in_segment"]) + 1,
                    "entry_price": float(accepted_row["close"]),
                    "exit_price": float(accepted_row["close"]),
                    "exit_reason": "utility_label",
                    "bars_held": 1,
                    "allocator_rank_within_day": int(accepted_row.get("allocator_rank_within_day", 0)),
                    "allocator_score": _safe_float(accepted_row.get("allocator_score")),
                    "balance_before": round(balance_before, 2),
                    "balance_after": round(state_after["account_balance"], 2),
                    "risk_pct": round(risk_pct, 4),
                    "risk_cash": round(risk_cash, 2),
                    "pnl_r": round(pnl_r, 6),
                    "pnl_cash": round(pnl_cash, 2),
                    "account_drawdown_pct_before_trade": round(float(start_state["account_drawdown_pct"]), 6),
                    "account_distance_to_target_pct_before_trade": round(float(start_state["account_distance_to_target_pct"]), 6),
                    "account_profitable_days_remaining_before_trade": int(start_state["account_profitable_days_remaining"]),
                    "kill_switch_state": str(accepted_row.get("kill_switch_state", "normal")),
                }
            )
    replay_meta = {
        "account_state_summary": tracker.finalize(),
        "accepted_setup_counts": dict(accepted_setups),
        "kill_switch_day_counts": dict(kill_switch_day_counts),
    }
    return trade_rows, dict(skip_counts), replay_meta


def build_backtest_summary(trades: pd.DataFrame, skip_counts: Dict[str, int], config: AccountStateConfig, policy_input: str, dataset: Optional[str], artifacts_dir: Optional[str], split: str) -> Dict[str, object]:
    if trades.empty:
        summary = {
            "trades": 0,
            "trading_days": 0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "average_hold_bars": 0.0,
            "ending_balance": round(config.starting_balance, 2),
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "reached_profit_target": False,
            "days_to_target": None,
            "breached_total_drawdown": False,
            "skip_counts": skip_counts,
            "pass_probability_30": 0.0,
            "pass_probability_60": 0.0,
            "pass_probability_90": 0.0,
            "median_days_to_pass": None,
            "avg_days_to_pass": None,
            "profitable_day_hit_rate_day_10": 0.0,
            "profitable_day_hit_rate_day_20": 0.0,
            "longest_trade_loss_streak": 0,
            "longest_negative_day_streak": 0,
            "worst_month_return_pct": 0.0,
            "loss_cluster_penalty": 0.0,
        }
        return {
            "dataset": dataset,
            "artifacts_dir": artifacts_dir,
            "policy_input": policy_input,
            "split": split,
            "execution_mode": "frontier_managed",
            "policy_selection": "frontier_daily_allocator",
            "raw_source_summary": None,
            "summary": summary,
        }

    trades = trades.sort_values(["entry_timestamp", "entry_index"]).reset_index(drop=True)
    equity = trades["balance_after"].astype(float)
    running_peak = equity.cummax()
    drawdown_pct = ((running_peak - equity) / running_peak.replace(0, np.nan) * 100.0).fillna(0.0)
    daily = (
        trades.groupby("session_date_utc", as_index=False)
        .agg(day_pnl_cash=("pnl_cash", "sum"))
        .sort_values("session_date_utc")
        .reset_index(drop=True)
    )
    daily_returns_pct = _daily_returns_from_cash(daily["day_pnl_cash"].astype(float).tolist(), config.starting_balance)
    evaluation = evaluate_propfirm_path(
        daily_returns_pct=daily_returns_pct,
        starting_balance=config.starting_balance,
        profit_target_pct=config.profit_target_pct,
        max_total_drawdown_pct=config.max_total_drawdown_pct,
        min_profitable_days=config.min_profitable_days,
    )
    losing_r = float(abs(trades.loc[trades["pnl_r"] < 0, "pnl_r"].sum()))
    challenge_metrics = _build_challenge_metrics(
        daily_returns_pct=daily_returns_pct,
        daily_dates=daily["session_date_utc"].tolist(),
        config=config,
        bootstrap_simulations=500,
        bootstrap_seed=7,
    )
    summary = {
        "trades": int(len(trades)),
        "trading_days": int(trades["session_date_utc"].nunique()),
        "win_rate": round(float((trades["pnl_r"] > 0).mean()), 6),
        "expectancy_r": round(float(trades["pnl_r"].mean()), 6),
        "total_r": round(float(trades["pnl_r"].sum()), 6),
        "profit_factor": round(float(trades.loc[trades["pnl_r"] > 0, "pnl_r"].sum() / losing_r), 6) if losing_r > 0 else 0.0,
        "average_hold_bars": round(float(trades["bars_held"].mean()), 6),
        "ending_balance": round(float(equity.iloc[-1]), 2),
        "total_return_pct": round((float(equity.iloc[-1]) / config.starting_balance - 1.0) * 100.0, 4),
        "max_drawdown_pct": round(float(drawdown_pct.max()), 4),
        "reached_profit_target": bool(evaluation["passed"]),
        "days_to_target": evaluation["days_to_pass"],
        "breached_total_drawdown": bool(evaluation["breached_total_drawdown"]),
        "skip_counts": skip_counts,
        "pass_probability_30": challenge_metrics["pass_probability_30"],
        "pass_probability_60": challenge_metrics["pass_probability_60"],
        "pass_probability_90": challenge_metrics["pass_probability_90"],
        "median_days_to_pass": challenge_metrics["median_days_to_pass"],
        "avg_days_to_pass": challenge_metrics["avg_days_to_pass"],
        "profitable_day_hit_rate_day_10": challenge_metrics["profitable_day_hit_rate_day_10"],
        "profitable_day_hit_rate_day_20": challenge_metrics["profitable_day_hit_rate_day_20"],
        "longest_trade_loss_streak": int(_longest_negative_streak(trades["pnl_r"].astype(float).tolist())),
        "longest_negative_day_streak": challenge_metrics["longest_negative_day_streak"],
        "worst_month_return_pct": challenge_metrics["worst_month_return_pct"],
        "loss_cluster_penalty": challenge_metrics["loss_cluster_penalty"],
    }
    return {
        "dataset": dataset,
        "artifacts_dir": artifacts_dir,
        "policy_input": policy_input,
        "split": split,
        "execution_mode": "frontier_managed",
        "policy_selection": "frontier_daily_allocator",
        "raw_source_summary": None,
        "summary": summary,
    }


def save_trades(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "setup",
        "account_stage",
        "probability",
        "predicted_frontier_score",
        "predicted_trade_utility",
        "predicted_challenge_pass_prob_5d",
        "predicted_challenge_pass_prob_10d",
        "predicted_challenge_pass_prob_20d",
        "predicted_challenge_fail_prob_5d",
        "predicted_challenge_fail_prob_10d",
        "predicted_challenge_expected_days_to_resolution",
        "predicted_challenge_distance_to_target_delta",
        "predicted_challenge_daily_loss_budget_consumption",
        "predicted_challenge_total_drawdown_budget_consumption",
        "predicted_funded_expected_return_5d",
        "predicted_funded_expected_return_20d",
        "predicted_funded_breach_risk_5d",
        "predicted_funded_breach_risk_20d",
        "predicted_funded_expected_drawdown",
        "predicted_funded_expected_payout_growth",
        "session_date_utc",
        "market_session",
        "session_phase",
        "entry_timestamp",
        "exit_timestamp",
        "entry_index",
        "exit_index",
        "entry_price",
        "exit_price",
        "exit_reason",
        "bars_held",
        "allocator_rank_within_day",
        "allocator_score",
        "balance_before",
        "balance_after",
        "risk_pct",
        "risk_cash",
        "pnl_r",
        "pnl_cash",
        "account_drawdown_pct_before_trade",
        "account_distance_to_target_pct_before_trade",
        "account_profitable_days_remaining_before_trade",
        "kill_switch_state",
    ]
    with gzip.open(path, "wt", newline="") as handle:
        pd.DataFrame(rows, columns=columns).to_csv(handle, index=False)


def run_replay(args: argparse.Namespace) -> int:
    candidates_path = Path(args.candidates).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(candidates_path)
    fundedhive = fundedhive_backtest_defaults()
    account_config = AccountStateConfig(
        starting_balance=float(args.starting_balance),
        profit_target_pct=float(fundedhive["profit_target_pct"]),
        min_profitable_days=int(fundedhive["min_profitable_days"]),
        max_daily_loss_pct=float(fundedhive["max_daily_loss_pct"]),
        max_total_drawdown_pct=float(fundedhive["max_total_drawdown_pct"]),
        max_trades_per_day=int(args.max_trades_per_day),
        risk_per_trade_pct=float(args.risk_per_trade_pct),
        initial_account_stage=str(args.account_stage),
    )
    allocation_config = AllocationConfig(
        min_trade_score=float(args.min_trade_score),
        max_trades_per_day=int(args.max_trades_per_day),
        allow_continuation=bool(args.allow_continuation),
    )
    trade_rows, skip_counts, replay_meta = replay_candidates(candidates, account_config, allocation_config)
    trades_frame = pd.DataFrame(trade_rows)
    policy_payload = build_policy_payload(allocation_config)
    policy_payload["backtest_config"] = {
        **fundedhive,
        "starting_balance": account_config.starting_balance,
        "max_trades_per_day": account_config.max_trades_per_day,
        "risk_per_trade_pct": account_config.risk_per_trade_pct,
    }
    policy_payload["replay_mode"] = "full_integrated_replay"
    policy_payload["candidate_input"] = str(candidates_path)
    policy_payload["continuation_reenabled"] = bool(args.allow_continuation)
    policy_payload["initial_account_stage"] = str(args.account_stage)

    policy_path = artifacts_dir / "manager_policy.json"
    policy_path.write_text(json.dumps(policy_payload, indent=2), encoding="utf-8")
    trades_output = artifacts_dir / "backtest_trades.csv.gz"
    save_trades(trades_output, trade_rows)
    summary_payload = build_backtest_summary(
        trades=trades_frame,
        skip_counts=skip_counts,
        config=account_config,
        policy_input=str(policy_path.resolve()),
        dataset=args.dataset,
        artifacts_dir=str(artifacts_dir),
        split=args.split,
    )
    (artifacts_dir / "backtest_summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    daily_by_date = trades_frame.groupby("session_date_utc")["pnl_cash"].sum() if not trades_frame.empty else pd.Series(dtype=float)
    daily_returns_pct = _daily_returns_from_cash(
        daily_by_date.astype(float).tolist(),
        account_config.starting_balance,
    )
    challenge_metrics = _build_challenge_metrics(
        daily_returns_pct=daily_returns_pct,
        daily_dates=list(daily_by_date.index),
        config=account_config,
        bootstrap_simulations=int(args.bootstrap_simulations),
        bootstrap_seed=int(args.bootstrap_seed),
    )
    replay_report = {
        "candidates": str(candidates_path),
        "dataset": args.dataset,
        "split": args.split,
        "account_config": asdict(account_config),
        "allocation_config": asdict(allocation_config),
        "summary": summary_payload["summary"],
        "challenge_metrics": challenge_metrics,
        "rolling_start": challenge_metrics["rolling_start"],
        "bootstrap": challenge_metrics["bootstrap"],
        "meta": replay_meta,
    }
    (artifacts_dir / "replay_report.json").write_text(json.dumps(replay_report, indent=2), encoding="utf-8")
    print(trades_output)
    print(artifacts_dir / "backtest_summary.json")
    print(artifacts_dir / "manager_policy.json")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay frontier utility candidates through the integrated allocator.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay = subparsers.add_parser("replay", help="Run full integrated replay on scored candidates.")
    replay.add_argument("--candidates", required=True)
    replay.add_argument("--artifacts-dir", required=True)
    replay.add_argument("--dataset")
    replay.add_argument("--split", default="test")
    replay.add_argument("--starting-balance", type=float, default=100000.0)
    replay.add_argument("--max-trades-per-day", type=int, default=3)
    replay.add_argument("--risk-per-trade-pct", type=float, default=0.25)
    replay.add_argument("--account-stage", choices=["challenge", "funded"], default="challenge")
    replay.add_argument("--min-trade-score", type=float, default=0.0)
    replay.add_argument("--allow-continuation", action="store_true")
    replay.add_argument("--bootstrap-simulations", type=int, default=500)
    replay.add_argument("--bootstrap-seed", type=int, default=7)
    replay.set_defaults(func=run_replay)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
