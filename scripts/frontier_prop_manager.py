import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from prop_firm_rules import evaluate_propfirm_path, fundedhive_backtest_defaults


DEFAULT_DISABLED_SETUPS = {"long_continuation", "short_continuation"}


@dataclass(frozen=True)
class PolicyBuildConfig:
    min_context_trades: int = 40
    min_context_expectancy_r: float = 0.05
    min_context_profit_factor: float = 1.10
    max_contexts_per_setup: int = 4
    disable_below_setup_expectancy_r: float = 0.03
    threshold_loosen_bps: float = 0.010
    threshold_tighten_bps: float = 0.020
    low_edge_risk_pct: float = 0.20
    normal_edge_risk_pct: float = 0.25
    strong_edge_risk_pct: float = 0.45
    low_edge_surplus: float = 0.000
    strong_edge_surplus: float = 0.015
    drawdown_soft_pct: float = 2.5
    drawdown_hard_pct: float = 5.0
    max_daily_trades: int = 3
    post_win_1_threshold_bump: float = 0.004
    post_win_2_threshold_bump: float = 0.008
    soft_drawdown_threshold_bump: float = 0.006
    recovery_after_loss_streak: int = 3
    recovery_mode_max_trades: int = 2
    weak_bucket_min_trades: int = 8
    weak_bucket_risk_pct: float = 0.15
    fragile_continuation_bucket_risk_pct: float = 0.10
    fragile_continuation_min_probability_surplus: float = 0.004
    weak_month_soft_floor_pct: float = -0.75
    weak_month_hard_floor_pct: float = -1.50


def _read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    return float(value)


def _round_or_none(value: Optional[float], digits: int = 6) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), digits)


def _daily_returns_from_cash(day_pnl_cash: Iterable[float], starting_balance: float) -> List[float]:
    balance = float(starting_balance)
    returns_pct: List[float] = []
    for pnl_cash in day_pnl_cash:
        pnl_cash = float(pnl_cash)
        if balance <= 0.0:
            returns_pct.append(0.0)
            balance += pnl_cash
            continue
        returns_pct.append(pnl_cash / balance * 100.0)
        balance += pnl_cash
    return returns_pct


def _profitable_days_within_horizon(daily_returns_pct: List[float], horizon: int) -> int:
    return int(sum(1 for value in daily_returns_pct[:horizon] if value > 0.0))


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


def _bootstrap_pass_probability(
    daily_returns_pct: List[float],
    starting_balance: float,
    profit_target_pct: float,
    max_total_drawdown_pct: float,
    min_profitable_days: int,
    horizon: int,
    simulations: int = 500,
    seed: int = 7,
) -> float:
    if not daily_returns_pct:
        return 0.0
    rng = np.random.default_rng(seed + horizon)
    passed = 0
    for _ in range(simulations):
        sampled: List[float] = []
        for _day in range(horizon):
            sampled.append(float(rng.choice(daily_returns_pct)))
            evaluation = evaluate_propfirm_path(
                daily_returns_pct=sampled,
                starting_balance=starting_balance,
                profit_target_pct=profit_target_pct,
                max_total_drawdown_pct=max_total_drawdown_pct,
                min_profitable_days=min_profitable_days,
            )
            if evaluation["passed"]:
                passed += 1
                break
            if evaluation["breached_total_drawdown"]:
                break
    return round(passed / simulations, 6)


def _build_challenge_metric_block(
    trades: pd.DataFrame,
    starting_balance: float,
    policy_config: Dict[str, object],
) -> Dict[str, object]:
    if trades.empty:
        return {
            "pass_probability_30": 0.0,
            "pass_probability_60": 0.0,
            "pass_probability_90": 0.0,
            "median_days_to_pass": None,
            "avg_days_to_pass": None,
            "profitable_day_hit_rate_day_10": 0.0,
            "profitable_day_hit_rate_day_20": 0.0,
            "longest_negative_day_streak": 0,
            "worst_month_return_pct": 0.0,
            "loss_cluster_penalty": 0.0,
        }
    daily = (
        trades.groupby("session_date_utc", as_index=False)
        .agg(day_pnl_cash=("pnl_cash", "sum"))
        .sort_values("session_date_utc")
        .reset_index(drop=True)
    )
    daily_returns_pct = _daily_returns_from_cash(daily["day_pnl_cash"].astype(float).tolist(), starting_balance)
    profit_target_pct = _safe_float(policy_config.get("profit_target_pct"), 10.0)
    max_total_drawdown_pct = _safe_float(policy_config.get("max_total_drawdown_pct"), 10.0)
    min_profitable_days = int(_safe_float(policy_config.get("min_profitable_days"), 3))
    pass_days = []
    hit_10 = []
    hit_20 = []
    for start_index in range(len(daily_returns_pct)):
        trailing = daily_returns_pct[start_index:]
        evaluation = evaluate_propfirm_path(
            daily_returns_pct=trailing,
            starting_balance=starting_balance,
            profit_target_pct=profit_target_pct,
            max_total_drawdown_pct=max_total_drawdown_pct,
            min_profitable_days=min_profitable_days,
        )
        if evaluation["days_to_pass"] is not None:
            pass_days.append(float(evaluation["days_to_pass"]))
        hit_10.append(float(_profitable_days_within_horizon(trailing, 10) >= min_profitable_days))
        hit_20.append(float(_profitable_days_within_horizon(trailing, 20) >= min_profitable_days))
    negative_days = [value for value in daily_returns_pct if value < 0.0]
    negative_day_rate = len(negative_days) / len(daily_returns_pct) if daily_returns_pct else 0.0
    avg_negative = abs(float(np.mean(negative_days))) if negative_days else 0.0
    month_returns = (
        pd.DataFrame({"session_date_utc": daily["session_date_utc"], "day_return_pct": daily_returns_pct})
        .assign(month=lambda frame: frame["session_date_utc"].astype(str).str.slice(0, 7))
        .groupby("month", dropna=False)["day_return_pct"]
        .sum()
    )
    return {
        "pass_probability_30": _bootstrap_pass_probability(daily_returns_pct, starting_balance, profit_target_pct, max_total_drawdown_pct, min_profitable_days, 30),
        "pass_probability_60": _bootstrap_pass_probability(daily_returns_pct, starting_balance, profit_target_pct, max_total_drawdown_pct, min_profitable_days, 60),
        "pass_probability_90": _bootstrap_pass_probability(daily_returns_pct, starting_balance, profit_target_pct, max_total_drawdown_pct, min_profitable_days, 90),
        "median_days_to_pass": _round_or_none(float(np.median(pass_days)) if pass_days else np.nan),
        "avg_days_to_pass": _round_or_none(float(np.mean(pass_days)) if pass_days else np.nan),
        "profitable_day_hit_rate_day_10": round(float(np.mean(hit_10)) if hit_10 else 0.0, 6),
        "profitable_day_hit_rate_day_20": round(float(np.mean(hit_20)) if hit_20 else 0.0, 6),
        "longest_negative_day_streak": int(_longest_negative_streak(daily_returns_pct)),
        "worst_month_return_pct": round(float(month_returns.min()) if len(month_returns) else 0.0, 6),
        "loss_cluster_penalty": round(negative_day_rate * avg_negative + 0.10 * _longest_negative_streak(daily_returns_pct), 6),
    }


def _build_bucket_rule_for_slice(
    trades: pd.DataFrame,
    setup: str,
    market_session: str,
    session_phase: str,
    config: PolicyBuildConfig,
    min_probability_surplus: float,
    weak_bucket_risk_pct: float,
) -> Dict[str, object]:
    slice_frame = trades[
        (trades["setup"] == setup)
        & (trades["market_session"] == market_session)
        & (trades["session_phase"] == session_phase)
    ].copy()
    if len(slice_frame) < config.weak_bucket_min_trades * 2 or "probability" not in slice_frame.columns:
        return {}
    slice_frame["bucket"] = pd.qcut(slice_frame["probability"], 5, labels=False, duplicates="drop")
    if slice_frame["bucket"].isna().all():
        return {}
    bucket_stats = (
        slice_frame.dropna(subset=["bucket"])
        .groupby("bucket", dropna=False)
        .agg(
            trades=("pnl_r", "size"),
            expectancy_r=("pnl_r", "mean"),
            total_r=("pnl_r", "sum"),
            min_probability=("probability", "min"),
            max_probability=("probability", "max"),
        )
        .reset_index()
        .sort_values("bucket")
    )
    if bucket_stats.empty:
        return {}
    bucket_stats["bucket_rank"] = np.arange(1, len(bucket_stats) + 1)
    blacklist = bucket_stats[
        (bucket_stats["trades"] >= config.weak_bucket_min_trades)
        & ((bucket_stats["expectancy_r"] <= 0.0) | (bucket_stats["total_r"] <= 0.0))
    ]
    if blacklist.empty:
        return {}
    survivors = bucket_stats.loc[~bucket_stats["bucket_rank"].isin(blacklist["bucket_rank"])]
    bucket_rank_floor = int(survivors["bucket_rank"].min()) if not survivors.empty else int(bucket_stats["bucket_rank"].max() + 1)
    return {
        "bucket_rank_floor": bucket_rank_floor,
        "min_probability_surplus": min_probability_surplus,
        "risk_pct_by_bucket": {
            str(int(row["bucket_rank"])): round(
                weak_bucket_risk_pct if int(row["bucket_rank"]) < bucket_rank_floor else config.normal_edge_risk_pct,
                4,
            )
            for _, row in bucket_stats.iterrows()
        },
        "blacklisted_bucket_ranks": [int(value) for value in blacklist["bucket_rank"].tolist()],
        "bucket_ranges": [
            {
                "bucket_rank": int(row["bucket_rank"]),
                "min_probability": round(float(row["min_probability"]), 6),
                "max_probability": round(float(row["max_probability"]), 6),
                "trades": int(row["trades"]),
                "expectancy_r": round(float(row["expectancy_r"]), 6),
                "total_r": round(float(row["total_r"]), 6),
            }
            for _, row in bucket_stats.iterrows()
        ],
    }


def _targeted_bucket_rules(trades: pd.DataFrame, config: PolicyBuildConfig) -> Dict[str, object]:
    if trades.empty:
        return {}
    rules: Dict[str, object] = {}
    slice_specs = [
        {
            "setup": "short_reversal",
            "market_session": "asia",
            "session_phase": "build_20_40",
            "min_probability_surplus": 0.002,
            "weak_bucket_risk_pct": config.weak_bucket_risk_pct,
        },
        {
            "setup": "long_continuation",
            "market_session": "asia",
            "session_phase": "opening_0_20",
            "min_probability_surplus": config.fragile_continuation_min_probability_surplus,
            "weak_bucket_risk_pct": config.fragile_continuation_bucket_risk_pct,
        },
    ]
    for spec in slice_specs:
        slice_key = f"{spec['setup']}|{spec['market_session']}|{spec['session_phase']}"
        rule = _build_bucket_rule_for_slice(
            trades=trades,
            setup=spec["setup"],
            market_session=spec["market_session"],
            session_phase=spec["session_phase"],
            config=config,
            min_probability_surplus=float(spec["min_probability_surplus"]),
            weak_bucket_risk_pct=float(spec["weak_bucket_risk_pct"]),
        )
        if rule:
            rules[slice_key] = rule
    return rules


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


def load_trade_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["entry_timestamp"] = pd.to_datetime(frame["entry_timestamp"], utc=True)
    frame["exit_timestamp"] = pd.to_datetime(frame["exit_timestamp"], utc=True)
    frame["session_date_utc"] = pd.to_datetime(frame["session_date_utc"], utc=False).dt.date
    return frame.sort_values(["entry_timestamp", "exit_timestamp"]).reset_index(drop=True)


def compute_context_path_stats(
    trades: pd.DataFrame,
    policy_config: Dict[str, object],
    starting_balance: float,
) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(
            columns=[
                "setup",
                "market_session",
                "session_phase",
                "positive_day_rate",
                "avg_day_r",
                "avg_day_return_pct",
                "loss_cluster_penalty",
                "rolling_start_pass_rate",
                "avg_days_to_pass",
                "median_days_to_pass",
                "profitable_day_hit_rate_day_10",
                "profitable_day_hit_rate_day_20",
                "avg_profitable_days_day_10",
                "avg_profitable_days_day_20",
                "days_traded",
            ]
        )

    day_summary = (
        trades.groupby(["setup", "market_session", "session_phase", "session_date_utc"], dropna=False)
        .agg(
            day_pnl_r=("pnl_r", "sum"),
            day_pnl_cash=("pnl_cash", "sum"),
            trades=("pnl_r", "size"),
        )
        .reset_index()
        .sort_values(["setup", "market_session", "session_phase", "session_date_utc"])
    )
    min_profitable_days = int(policy_config.get("min_profitable_days", 0))
    profit_target_pct = _safe_float(policy_config.get("profit_target_pct"), 10.0)
    max_total_drawdown_pct = _safe_float(policy_config.get("max_total_drawdown_pct"), 10.0)

    rows: List[Dict[str, object]] = []
    for keys, group in day_summary.groupby(["setup", "market_session", "session_phase"], dropna=False):
        group = group.sort_values("session_date_utc").reset_index(drop=True)
        daily_r = group["day_pnl_r"].astype(float).tolist()
        daily_cash = group["day_pnl_cash"].astype(float).tolist()
        daily_returns_pct = _daily_returns_from_cash(daily_cash, starting_balance)
        positive_day_rate = float(np.mean([value > 0.0 for value in daily_r])) if daily_r else 0.0
        negative_day_rate = float(np.mean([value < 0.0 for value in daily_r])) if daily_r else 0.0
        avg_day_r = float(np.mean(daily_r)) if daily_r else 0.0
        avg_day_return_pct = float(np.mean(daily_returns_pct)) if daily_returns_pct else 0.0

        pass_flags: List[float] = []
        pass_days: List[float] = []
        profit_day_hit_10: List[float] = []
        profit_day_hit_20: List[float] = []
        profitable_days_10: List[float] = []
        profitable_days_20: List[float] = []
        for start_index in range(len(daily_returns_pct)):
            trailing = daily_returns_pct[start_index:]
            evaluation = evaluate_propfirm_path(
                daily_returns_pct=trailing,
                starting_balance=starting_balance,
                profit_target_pct=profit_target_pct,
                max_total_drawdown_pct=max_total_drawdown_pct,
                min_profitable_days=min_profitable_days,
            )
            pass_flags.append(float(bool(evaluation["passed"])))
            if evaluation["days_to_pass"] is not None:
                pass_days.append(float(evaluation["days_to_pass"]))
            profitable_days_10.append(float(_profitable_days_within_horizon(trailing, 10)))
            profitable_days_20.append(float(_profitable_days_within_horizon(trailing, 20)))
            profit_day_hit_10.append(float(_profitable_days_within_horizon(trailing, 10) >= min_profitable_days))
            profit_day_hit_20.append(float(_profitable_days_within_horizon(trailing, 20) >= min_profitable_days))

        loss_cluster_penalty = (
            negative_day_rate * max(-avg_day_r, 0.0) + 0.10 * float(_longest_negative_streak(daily_r))
        )
        rows.append(
            {
                "setup": keys[0],
                "market_session": keys[1],
                "session_phase": keys[2],
                "positive_day_rate": positive_day_rate,
                "negative_day_rate": negative_day_rate,
                "avg_day_r": avg_day_r,
                "avg_day_return_pct": avg_day_return_pct,
                "loss_cluster_penalty": loss_cluster_penalty,
                "rolling_start_pass_rate": float(np.mean(pass_flags)) if pass_flags else 0.0,
                "avg_days_to_pass": float(np.mean(pass_days)) if pass_days else np.nan,
                "median_days_to_pass": float(np.median(pass_days)) if pass_days else np.nan,
                "profitable_day_hit_rate_day_10": float(np.mean(profit_day_hit_10)) if profit_day_hit_10 else 0.0,
                "profitable_day_hit_rate_day_20": float(np.mean(profit_day_hit_20)) if profit_day_hit_20 else 0.0,
                "avg_profitable_days_day_10": float(np.mean(profitable_days_10)) if profitable_days_10 else 0.0,
                "avg_profitable_days_day_20": float(np.mean(profitable_days_20)) if profitable_days_20 else 0.0,
                "days_traded": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def build_context_frame(
    analysis_report: Dict[str, object],
    baseline_report: Dict[str, object],
    config: PolicyBuildConfig,
) -> pd.DataFrame:
    validation_backtests = analysis_report.get("validation_context_backtests", {})
    base_thresholds = {
        setup: _safe_float(payload.get("threshold"))
        for setup, payload in analysis_report.get("setup_signal_summary", {}).items()
    }
    by_setup = pd.DataFrame(baseline_report.get("by_setup", []))
    setup_stats = by_setup.set_index("setup").to_dict("index") if not by_setup.empty else {}

    rows: List[Dict[str, object]] = []
    for setup, contexts in validation_backtests.items():
        base_threshold = _safe_float(base_thresholds.get(setup))
        setup_expectancy = _safe_float(setup_stats.get(setup, {}).get("expectancy_r"))
        for context in contexts:
            trades = int(_safe_float(context.get("trades")))
            expectancy_r = _safe_float(context.get("expectancy_r"), np.nan)
            profit_factor = _safe_float(context.get("profit_factor"), np.nan)
            win_rate = _safe_float(context.get("win_rate"), np.nan)
            if trades < config.min_context_trades:
                continue
            if not np.isfinite(expectancy_r) or not np.isfinite(profit_factor):
                continue
            rows.append(
                {
                    "setup": setup,
                    "market_session": context.get("market_session"),
                    "session_phase": context.get("session_phase"),
                    "trades": trades,
                    "win_rate": win_rate,
                    "expectancy_r": expectancy_r,
                    "profit_factor": profit_factor,
                    "total_r": _safe_float(context.get("total_r")),
                    "average_hold_bars": _safe_float(context.get("average_hold_bars")),
                    "base_threshold": base_threshold,
                    "setup_expectancy_r": setup_expectancy,
                }
            )
    return pd.DataFrame(rows)


def _normalize(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    low = float(series.min())
    high = float(series.max())
    if not np.isfinite(low) or not np.isfinite(high) or math.isclose(low, high):
        return pd.Series(np.full(len(series), 0.5), index=series.index)
    return (series - low) / (high - low)


def score_contexts(
    context_frame: pd.DataFrame,
    trades: pd.DataFrame,
    policy_config: Dict[str, object],
    starting_balance: float,
) -> pd.DataFrame:
    if context_frame.empty:
        return context_frame.copy()

    path_stats = compute_context_path_stats(trades, policy_config, starting_balance)
    scored = context_frame.merge(
        path_stats,
        on=["setup", "market_session", "session_phase"],
        how="left",
    )
    for column in [
        "positive_day_rate",
        "avg_day_r",
        "avg_day_return_pct",
        "loss_cluster_penalty",
        "rolling_start_pass_rate",
        "profitable_day_hit_rate_day_10",
        "profitable_day_hit_rate_day_20",
        "avg_profitable_days_day_10",
        "avg_profitable_days_day_20",
    ]:
        scored[column] = scored[column].fillna(0.0)

    expectancy_z = _normalize(scored["expectancy_r"])
    pf_z = _normalize(scored["profit_factor"])
    positive_day_z = _normalize(scored["positive_day_rate"])
    avg_day_r_z = _normalize(scored["avg_day_r"])
    pass_rate_z = _normalize(scored["rolling_start_pass_rate"])
    profit_day_10_z = _normalize(scored["profitable_day_hit_rate_day_10"])
    profit_day_20_z = _normalize(scored["profitable_day_hit_rate_day_20"])
    penalty_z = _normalize(scored["loss_cluster_penalty"])
    scored["path_utility_score"] = (
        0.25 * expectancy_z
        + 0.15 * pf_z
        + 0.15 * positive_day_z
        + 0.10 * avg_day_r_z
        + 0.20 * pass_rate_z
        + 0.075 * profit_day_10_z
        + 0.075 * profit_day_20_z
        - 0.15 * penalty_z
    )
    return scored.sort_values(
        ["setup", "path_utility_score", "rolling_start_pass_rate", "expectancy_r"],
        ascending=[True, False, False, False],
    )


def choose_context_threshold(base_threshold: float, utility_rank: float, config: PolicyBuildConfig) -> float:
    loosen = config.threshold_loosen_bps * max(utility_rank, 0.0)
    tighten = config.threshold_tighten_bps * max(1.0 - utility_rank, 0.0)
    return float(min(0.99, max(0.01, base_threshold - loosen + tighten)))


def build_policy_payload(
    analysis_report: Dict[str, object],
    baseline_report: Dict[str, object],
    trades: pd.DataFrame,
    config: PolicyBuildConfig,
) -> Dict[str, object]:
    current_policy = analysis_report.get("policy_summary", {})
    by_setup = pd.DataFrame(baseline_report.get("by_setup", []))
    fundedhive_config = fundedhive_backtest_defaults()
    starting_balance = _safe_float(
        baseline_report.get("challenge", {}).get("starting_balance"),
        100000.0,
    )
    context_frame = build_context_frame(analysis_report, baseline_report, config)
    scored_contexts = score_contexts(
        context_frame=context_frame,
        trades=trades,
        policy_config=fundedhive_config,
        starting_balance=starting_balance,
    )

    if not scored_contexts.empty:
        scored_contexts["utility_rank"] = scored_contexts.groupby("setup")["path_utility_score"].transform(_normalize)
        scored_contexts["context_threshold"] = scored_contexts.apply(
            lambda row: choose_context_threshold(
                _safe_float(row["base_threshold"]),
                _safe_float(row["utility_rank"], 0.5),
                config,
            ),
            axis=1,
        )
    else:
        scored_contexts["context_threshold"] = []

    setup_expectancy = {}
    disabled_experts = set()
    for row in by_setup.to_dict("records"):
        setup = row["setup"]
        expectancy = _safe_float(row.get("expectancy_r"))
        setup_expectancy[setup] = expectancy
        if expectancy <= config.disable_below_setup_expectancy_r:
            disabled_experts.add(setup)
    disabled_experts.update(DEFAULT_DISABLED_SETUPS & set(setup_expectancy))

    enabled_experts = [setup for setup in current_policy.get("enabled_experts", setup_expectancy.keys()) if setup not in disabled_experts]
    if not enabled_experts and setup_expectancy:
        enabled_experts = [max(setup_expectancy, key=setup_expectancy.get)]

    allowed_contexts: Dict[str, List[Dict[str, object]]] = {}
    context_thresholds: Dict[str, Dict[str, float]] = {}
    for setup, group in scored_contexts.groupby("setup"):
        if setup in disabled_experts:
            continue
        filtered = group[
            (group["expectancy_r"] >= config.min_context_expectancy_r)
            & (group["profit_factor"] >= config.min_context_profit_factor)
        ].head(config.max_contexts_per_setup)
        context_rows = []
        threshold_rows = {}
        for row in filtered.to_dict("records"):
            context_key = f"{row['market_session']}|{row['session_phase']}"
            threshold_rows[context_key] = round(_safe_float(row["context_threshold"]), 6)
            context_rows.append(
                {
                    "market_session": row["market_session"],
                    "session_phase": row["session_phase"],
                    "trades": int(row["trades"]),
                    "win_rate": round(_safe_float(row["win_rate"]), 6),
                    "expectancy_r": round(_safe_float(row["expectancy_r"]), 6),
                    "total_r": round(_safe_float(row["total_r"]), 6),
                    "profit_factor": round(_safe_float(row["profit_factor"]), 6),
                    "average_hold_bars": round(_safe_float(row["average_hold_bars"]), 6),
                    "positive_day_rate": round(_safe_float(row["positive_day_rate"]), 6),
                    "avg_day_r": round(_safe_float(row["avg_day_r"]), 6),
                    "rolling_start_pass_rate": round(_safe_float(row["rolling_start_pass_rate"]), 6),
                    "avg_days_to_pass": _round_or_none(row.get("avg_days_to_pass")),
                    "median_days_to_pass": _round_or_none(row.get("median_days_to_pass")),
                    "profitable_day_hit_rate_day_10": round(_safe_float(row["profitable_day_hit_rate_day_10"]), 6),
                    "profitable_day_hit_rate_day_20": round(_safe_float(row["profitable_day_hit_rate_day_20"]), 6),
                    "avg_profitable_days_day_10": round(_safe_float(row["avg_profitable_days_day_10"]), 6),
                    "avg_profitable_days_day_20": round(_safe_float(row["avg_profitable_days_day_20"]), 6),
                    "path_utility_score": round(_safe_float(row["path_utility_score"]), 6),
                    "context_threshold": round(_safe_float(row["context_threshold"]), 6),
                }
            )
        if context_rows:
            allowed_contexts[setup] = context_rows
            context_thresholds[setup] = threshold_rows
        else:
            disabled_experts.add(setup)

    enabled_experts = [setup for setup in enabled_experts if setup in allowed_contexts]
    disabled_experts = sorted(set(setup_expectancy) - set(enabled_experts))
    thresholds = {
        setup: _safe_float(payload.get("threshold"))
        for setup, payload in analysis_report.get("setup_signal_summary", {}).items()
    }
    bucket_controls = _targeted_bucket_rules(trades, config)

    return {
        "selection": "frontier_contextual_abstention_manager",
        "enabled_experts": enabled_experts,
        "disabled_experts": disabled_experts,
        "thresholds": thresholds,
        "context_thresholds": context_thresholds,
        "allowed_contexts": allowed_contexts,
        "bucket_controls": bucket_controls,
        "policy_config": asdict(config),
        "risk_model": {
            "mode": "tiered_probability_surplus_and_drawdown",
            "low_edge_risk_pct": config.low_edge_risk_pct,
            "normal_edge_risk_pct": config.normal_edge_risk_pct,
            "strong_edge_risk_pct": config.strong_edge_risk_pct,
            "low_edge_surplus": config.low_edge_surplus,
            "strong_edge_surplus": config.strong_edge_surplus,
            "drawdown_soft_pct": config.drawdown_soft_pct,
            "drawdown_hard_pct": config.drawdown_hard_pct,
            "sizing_rule": [
                "Use 0.20% when probability surplus is near zero or account is in soft drawdown.",
                "Use 0.25% for normal validated edge.",
                "Use 0.45% only when surplus is clearly above threshold and account drawdown is contained.",
            ],
        },
        "selection_utility": {
            "mode": "path_aware_context_ranking",
            "weights": {
                "expectancy_r": 0.25,
                "profit_factor": 0.15,
                "positive_day_rate": 0.15,
                "avg_day_r": 0.10,
                "rolling_start_pass_rate": 0.20,
                "profitable_day_hit_rate_day_10": 0.075,
                "profitable_day_hit_rate_day_20": 0.075,
                "loss_cluster_penalty": -0.15,
            },
            "objective": "Favor faster and smoother prop-style progress rather than raw classification lift alone.",
        },
        "state_controls": {
            "post_win_1_threshold_bump": config.post_win_1_threshold_bump,
            "post_win_2_threshold_bump": config.post_win_2_threshold_bump,
            "soft_drawdown_threshold_bump": config.soft_drawdown_threshold_bump,
            "recovery_after_loss_streak": config.recovery_after_loss_streak,
            "recovery_mode_max_trades": config.recovery_mode_max_trades,
            "hard_drawdown_action": "abstain",
            "weak_month_soft_floor_pct": config.weak_month_soft_floor_pct,
            "weak_month_hard_floor_pct": config.weak_month_hard_floor_pct,
        },
        "abstention": {
            "default_action": "trade_nothing",
            "max_trades_per_day": config.max_daily_trades,
            "abstain_when": [
                "expert disabled",
                "context not whitelisted",
                "probability below effective threshold",
                "account is in hard drawdown state",
                "signal is weak and only marginally above the minimum edge",
            ],
        },
        "regime_features": {
            "implemented_in_enrichment_script": True,
            "columns": [
                "session_range_expansion_state",
                "prior_session_imbalance",
                "opening_drive_strength",
                "volatility_regime_percentile",
                "intraday_trend_persistence",
                "intraday_chop_score",
            ],
        },
        "backtest_config": {
            **fundedhive_config,
            "risk_per_trade_pct": config.normal_edge_risk_pct,
            "starting_balance": starting_balance,
            "max_trades_per_day": config.max_daily_trades,
        },
        "notes": [
            "This policy disables both continuation experts by default until they clear realized prop-utility thresholds.",
            "Context thresholds are setup/session/phase specific instead of flat per expert.",
            "Risk sizing is conditional on probability surplus and drawdown state.",
            "Contexts are ranked with rolling-start pass rate and profitable-day accumulation, not only raw expectancy.",
            "State controls tighten thresholds after win streaks and in drawdown.",
            "Weak bucket rules can blacklist unstable probability buckets, including short_reversal/asia/build_20_40 and fragile long_continuation/asia/opening_0_20 tails.",
            "Abstention is explicit: trade nothing is the default when edge is marginal.",
        ],
    }


def apply_frontier_policy(trades: pd.DataFrame, policy: Dict[str, object]) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()

    enabled_experts = set(policy.get("enabled_experts", []))
    context_thresholds = policy.get("context_thresholds", {})
    bucket_controls = policy.get("bucket_controls", {})
    risk_model = policy.get("risk_model", {})
    state_controls = policy.get("state_controls", {})
    abstention = policy.get("abstention", {})
    low_risk = _safe_float(risk_model.get("low_edge_risk_pct"), 0.20)
    normal_risk = _safe_float(risk_model.get("normal_edge_risk_pct"), 0.25)
    strong_risk = _safe_float(risk_model.get("strong_edge_risk_pct"), 0.45)
    strong_edge_surplus = _safe_float(risk_model.get("strong_edge_surplus"), 0.015)
    soft_drawdown_pct = _safe_float(risk_model.get("drawdown_soft_pct"), 2.5)
    hard_drawdown_pct = _safe_float(risk_model.get("drawdown_hard_pct"), 5.0)
    post_win_1_bump = _safe_float(state_controls.get("post_win_1_threshold_bump"), 0.0)
    post_win_2_bump = _safe_float(state_controls.get("post_win_2_threshold_bump"), 0.0)
    soft_drawdown_bump = _safe_float(state_controls.get("soft_drawdown_threshold_bump"), 0.0)
    recovery_after_loss_streak = int(_safe_float(state_controls.get("recovery_after_loss_streak"), 3))
    recovery_mode_max_trades = int(_safe_float(state_controls.get("recovery_mode_max_trades"), 2))
    weak_month_soft_floor_pct = _safe_float(state_controls.get("weak_month_soft_floor_pct"), -0.75)
    weak_month_hard_floor_pct = _safe_float(state_controls.get("weak_month_hard_floor_pct"), -1.50)
    max_daily_trades = int(_safe_float(abstention.get("max_trades_per_day"), 3))

    filtered_rows: List[Dict[str, object]] = []
    running_peak: Optional[float] = None
    current_balance: Optional[float] = None
    day_trade_counts: Dict[object, int] = {}
    monthly_pnl_pct: Dict[str, float] = {}
    win_streak = 0
    loss_streak = 0

    for row in trades.to_dict("records"):
        setup = row["setup"]
        if setup not in enabled_experts:
            continue

        balance_before = current_balance if current_balance is not None else _safe_float(row.get("balance_before"), 100000.0)
        if running_peak is None:
            running_peak = balance_before
        running_peak = max(running_peak, balance_before)
        drawdown_pct = 0.0 if running_peak <= 0 else max(0.0, (running_peak - balance_before) / running_peak * 100.0)
        if drawdown_pct >= hard_drawdown_pct:
            continue
        month_key = str(row["session_date_utc"])[:7]
        month_return_pct = monthly_pnl_pct.get(month_key, 0.0)

        context_key = f"{row['market_session']}|{row['session_phase']}"
        base_threshold = _safe_float(
            context_thresholds.get(setup, {}).get(context_key, row.get("threshold")),
            _safe_float(row.get("threshold")),
        )
        threshold_adjustment = 0.0
        if win_streak >= 2:
            threshold_adjustment += post_win_2_bump
        elif win_streak >= 1:
            threshold_adjustment += post_win_1_bump
        if drawdown_pct >= soft_drawdown_pct:
            threshold_adjustment += soft_drawdown_bump
        if month_return_pct <= weak_month_hard_floor_pct:
            threshold_adjustment += soft_drawdown_bump + post_win_2_bump
        elif month_return_pct <= weak_month_soft_floor_pct:
            threshold_adjustment += post_win_1_bump
        required_threshold = min(0.99, max(0.01, base_threshold + threshold_adjustment))
        probability = _safe_float(row.get("probability"))
        slice_key = f"{setup}|{row['market_session']}|{row['session_phase']}"
        bucket_rule = bucket_controls.get(slice_key, {})
        bucket_rank = None
        if bucket_rule:
            for bucket_range in bucket_rule.get("bucket_ranges", []):
                if _safe_float(bucket_range.get("min_probability")) <= probability <= _safe_float(bucket_range.get("max_probability")):
                    bucket_rank = int(bucket_range.get("bucket_rank"))
                    break
            if bucket_rank is None and bucket_rule.get("bucket_ranges"):
                first_range = bucket_rule["bucket_ranges"][0]
                last_range = bucket_rule["bucket_ranges"][-1]
                if probability < _safe_float(first_range.get("min_probability")):
                    bucket_rank = int(first_range.get("bucket_rank"))
                elif probability > _safe_float(last_range.get("max_probability")):
                    bucket_rank = int(last_range.get("bucket_rank"))
        if bucket_rank is not None:
            if bucket_rank in set(bucket_rule.get("blacklisted_bucket_ranks", [])):
                continue
            if bucket_rank < int(_safe_float(bucket_rule.get("bucket_rank_floor"), 0)):
                continue
            if probability - required_threshold < _safe_float(bucket_rule.get("min_probability_surplus"), 0.0):
                continue
        if probability < required_threshold:
            continue

        session_date = row["session_date_utc"]
        day_trade_counts.setdefault(session_date, 0)
        day_trade_limit = max_daily_trades
        if loss_streak >= recovery_after_loss_streak or drawdown_pct >= soft_drawdown_pct:
            day_trade_limit = min(day_trade_limit, recovery_mode_max_trades)
        if day_trade_counts[session_date] >= day_trade_limit:
            continue

        surplus = probability - required_threshold
        if drawdown_pct >= soft_drawdown_pct:
            risk_pct = low_risk
        elif surplus >= strong_edge_surplus:
            risk_pct = strong_risk
        elif surplus > 0.0:
            risk_pct = normal_risk
        else:
            risk_pct = low_risk
        if bucket_rank is not None:
            risk_pct = min(risk_pct, _safe_float(bucket_rule.get("risk_pct_by_bucket", {}).get(str(bucket_rank)), risk_pct))

        original_risk_cash = _safe_float(row.get("risk_cash"))
        scale = 0.0 if original_risk_cash <= 0 else (risk_pct / 100.0 * balance_before) / original_risk_cash
        adjusted = dict(row)
        adjusted["base_context_threshold"] = round(base_threshold, 6)
        adjusted["effective_threshold"] = round(required_threshold, 6)
        adjusted["threshold_adjustment"] = round(threshold_adjustment, 6)
        adjusted["applied_risk_pct"] = risk_pct
        adjusted["drawdown_pct_before_trade"] = round(drawdown_pct, 6)
        adjusted["win_streak_before_trade"] = win_streak
        adjusted["loss_streak_before_trade"] = loss_streak
        adjusted["allowed_day_trade_limit"] = day_trade_limit
        adjusted["month_return_pct_before_trade"] = round(month_return_pct, 6)
        adjusted["bucket_rank"] = bucket_rank
        adjusted["pnl_cash"] = round(_safe_float(row["pnl_cash"]) * scale, 2)
        adjusted["risk_cash"] = round(original_risk_cash * scale, 2)
        adjusted["balance_before"] = round(balance_before, 2)
        adjusted["balance_after"] = round(balance_before + adjusted["pnl_cash"], 2)
        current_balance = adjusted["balance_after"]
        running_peak = max(running_peak, current_balance)
        filtered_rows.append(adjusted)
        day_trade_counts[session_date] += 1
        monthly_pnl_pct[month_key] = monthly_pnl_pct.get(month_key, 0.0) + ((adjusted["balance_after"] / adjusted["balance_before"] - 1.0) * 100.0 if adjusted["balance_before"] else 0.0)
        pnl_r = _safe_float(row.get("pnl_r"))
        if pnl_r > 0.0:
            win_streak += 1
            loss_streak = 0
        elif pnl_r < 0.0:
            loss_streak += 1
            win_streak = 0
        else:
            win_streak = 0
            loss_streak = 0

    return pd.DataFrame(filtered_rows)


def summarize_trade_path(trades: pd.DataFrame, starting_balance: float) -> Dict[str, object]:
    if trades.empty:
        return {
            "trades": 0,
            "trading_days": 0,
            "ending_balance": round(starting_balance, 2),
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "by_setup": [],
        }

    equity = trades["balance_after"].astype(float)
    running_peak = equity.cummax()
    drawdown_pct = ((running_peak - equity) / running_peak.replace(0, np.nan) * 100.0).fillna(0.0)
    by_setup = (
        trades.groupby("setup", dropna=False)
        .agg(
            trades=("setup", "size"),
            win_rate=("pnl_r", lambda s: float((s > 0).mean())),
            expectancy_r=("pnl_r", "mean"),
            pnl_cash=("pnl_cash", "sum"),
        )
        .reset_index()
        .to_dict("records")
    )
    return {
        "trades": int(len(trades)),
        "trading_days": int(trades["session_date_utc"].nunique()),
        "ending_balance": round(float(equity.iloc[-1]), 2),
        "total_return_pct": round((float(equity.iloc[-1]) / starting_balance - 1.0) * 100.0, 4),
        "max_drawdown_pct": round(float(drawdown_pct.max()), 4),
        "win_rate": round(float((trades["pnl_r"] > 0).mean()), 6),
        "expectancy_r": round(float(trades["pnl_r"].mean()), 6),
        "by_setup": by_setup,
    }


def summarize_challenge_path(trades: pd.DataFrame, policy: Dict[str, object], starting_balance: float) -> Dict[str, object]:
    config = policy.get("backtest_config", {})
    if trades.empty:
        return {
            "actual_path_passed": False,
            "actual_days_to_pass": None,
            "actual_profitable_days": 0,
            "rolling_start_pass_rate": 0.0,
            **_build_challenge_metric_block(trades, starting_balance, config),
        }

    daily = (
        trades.groupby("session_date_utc", as_index=False)
        .agg(day_pnl_cash=("pnl_cash", "sum"))
        .sort_values("session_date_utc")
        .reset_index(drop=True)
    )
    daily_returns_pct = _daily_returns_from_cash(daily["day_pnl_cash"].tolist(), starting_balance)
    actual = evaluate_propfirm_path(
        daily_returns_pct=daily_returns_pct,
        starting_balance=starting_balance,
        profit_target_pct=_safe_float(config.get("profit_target_pct"), 10.0),
        max_total_drawdown_pct=_safe_float(config.get("max_total_drawdown_pct"), 10.0),
        min_profitable_days=int(_safe_float(config.get("min_profitable_days"), 3)),
    )
    start_evaluations = [
        evaluate_propfirm_path(
            daily_returns_pct=daily_returns_pct[start_index:],
            starting_balance=starting_balance,
            profit_target_pct=_safe_float(config.get("profit_target_pct"), 10.0),
            max_total_drawdown_pct=_safe_float(config.get("max_total_drawdown_pct"), 10.0),
            min_profitable_days=int(_safe_float(config.get("min_profitable_days"), 3)),
        )
        for start_index in range(len(daily_returns_pct))
    ]
    pass_flags = [float(item["passed"]) for item in start_evaluations]
    pass_days = [float(item["days_to_pass"]) for item in start_evaluations if item["days_to_pass"] is not None]
    challenge_metrics = _build_challenge_metric_block(trades, starting_balance, config)
    return {
        "actual_path_passed": bool(actual["passed"]),
        "actual_days_to_pass": actual["days_to_pass"],
        "actual_profitable_days": int(actual["profitable_days"]),
        "rolling_start_pass_rate": round(float(np.mean(pass_flags)) if pass_flags else 0.0, 6),
        "rolling_start_avg_days_to_pass": _round_or_none(float(np.mean(pass_days)) if pass_days else np.nan),
        "rolling_start_median_days_to_pass": _round_or_none(float(np.median(pass_days)) if pass_days else np.nan),
        **challenge_metrics,
    }


def build_backtest_summary_payload(
    trades: pd.DataFrame,
    policy: Dict[str, object],
    starting_balance: float,
    policy_input: str,
) -> Dict[str, object]:
    summary = summarize_trade_path(trades, starting_balance)
    challenge = summarize_challenge_path(trades, policy, starting_balance)
    losing_r = float(abs(trades.loc[trades["pnl_r"] < 0, "pnl_r"].sum())) if not trades.empty else 0.0
    profit_factor = (
        round(float(trades.loc[trades["pnl_r"] > 0, "pnl_r"].sum() / losing_r), 6)
        if losing_r > 0.0
        else 0.0
    )
    return {
        "dataset": None,
        "artifacts_dir": None,
        "policy_input": policy_input,
        "split": "test",
        "execution_mode": "frontier_managed",
        "policy_selection": str(policy.get("selection", "frontier_contextual_abstention_manager")),
        "raw_source_summary": policy.get("raw_source_summary"),
        "summary": {
            "trades": summary["trades"],
            "trading_days": summary["trading_days"],
            "win_rate": summary["win_rate"],
            "expectancy_r": summary["expectancy_r"],
            "total_r": round(float(trades["pnl_r"].sum()), 6) if not trades.empty else 0.0,
            "profit_factor": profit_factor,
            "average_hold_bars": round(float(trades["bars_held"].mean()), 6) if not trades.empty else 0.0,
            "ending_balance": summary["ending_balance"],
            "total_return_pct": summary["total_return_pct"],
            "max_drawdown_pct": summary["max_drawdown_pct"],
            "reached_profit_target": challenge["actual_path_passed"],
            "days_to_target": challenge["actual_days_to_pass"],
            "breached_total_drawdown": False,
            "pass_probability_30": challenge["pass_probability_30"],
            "pass_probability_60": challenge["pass_probability_60"],
            "pass_probability_90": challenge["pass_probability_90"],
            "median_days_to_pass": challenge["median_days_to_pass"],
            "avg_days_to_pass": challenge["avg_days_to_pass"],
            "profitable_day_hit_rate_day_10": challenge["profitable_day_hit_rate_day_10"],
            "profitable_day_hit_rate_day_20": challenge["profitable_day_hit_rate_day_20"],
            "longest_trade_loss_streak": int(_longest_negative_streak(trades["pnl_r"].astype(float).tolist())) if not trades.empty else 0,
            "longest_negative_day_streak": challenge["longest_negative_day_streak"],
            "worst_month_return_pct": challenge["worst_month_return_pct"],
            "loss_cluster_penalty": challenge["loss_cluster_penalty"],
            "skip_counts": {
                "cooldown": 0,
                "ineligible": 0,
                "session_end_buffer": 0,
                "daily_lock": 0,
                "daily_trade_cap": 0,
                "daily_risk_budget": 0,
                "total_drawdown_budget": 0,
                "filtered_by_policy": 0,
            },
        },
    }


def enrich_with_regime_features(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    grouped = enriched.groupby("session_date_utc", sort=False)

    expansion_proxy = enriched["rolling_range_15_atr"] / enriched["rolling_range_60_atr"].replace(0.0, np.nan)
    enriched["session_range_expansion_state"] = expansion_proxy.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(0.0, 3.0)

    prior_body = (
        enriched["prev_session_body_return_1"].fillna(0.0)
        + 0.5 * enriched["prev_session_body_return_2"].fillna(0.0)
        + 0.25 * enriched["prev_session_body_return_3"].fillna(0.0)
    )
    enriched["prior_session_imbalance"] = prior_body

    opening_window = (enriched["session_progress"] <= 0.20).astype(float)
    opening_drive = (
        enriched["session_open_return_atr"].fillna(0.0).abs()
        * (1.0 + enriched["trend_score_10"].fillna(0.0).abs())
        * opening_window
    )
    enriched["opening_drive_strength"] = opening_drive

    vol_pct = grouped["rolling_vol_60"].transform(lambda s: s.rank(pct=True, method="average"))
    enriched["volatility_regime_percentile"] = vol_pct.fillna(0.5)

    persistence = (
        enriched["trend_score_10"].fillna(0.0).abs()
        + enriched["trend_score_30"].fillna(0.0).abs()
        + enriched["trend_score_60"].fillna(0.0).abs()
    ) / 3.0
    enriched["intraday_trend_persistence"] = persistence

    chop = (
        enriched["rolling_vol_15"].fillna(0.0)
        / enriched["rolling_range_15_atr"].replace(0.0, np.nan)
    ).replace([np.inf, -np.inf], np.nan)
    enriched["intraday_chop_score"] = chop.fillna(0.0).clip(lower=0.0)
    return enriched


def build_policy_command(args: argparse.Namespace) -> int:
    config = PolicyBuildConfig()
    analysis_report = _read_json(Path(args.analysis_report))
    baseline_report = _read_json(Path(args.baseline_report))
    trades = load_trade_frame(Path(args.trades))
    payload = build_policy_payload(analysis_report, baseline_report, trades, config)
    _write_json(Path(args.output), payload)
    print(Path(args.output))
    return 0


def evaluate_policy_command(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy)
    policy = _read_json(policy_path)
    trades = load_trade_frame(Path(args.trades))
    baseline = _read_json(Path(args.baseline_report))
    starting_balance = _safe_float(
        baseline.get("challenge", {}).get("starting_balance"),
        100000.0,
    )
    adjusted = apply_frontier_policy(trades, policy)
    summary = {
        "baseline": summarize_trade_path(trades, starting_balance),
        "baseline_challenge": baseline.get("challenge", {}),
        "frontier_policy_estimate": summarize_trade_path(adjusted, starting_balance),
        "frontier_policy_challenge": summarize_challenge_path(adjusted, policy, starting_balance),
    }
    if args.output:
        _write_json(Path(args.output), summary)
    if args.adjusted_trades_output:
        output_path = Path(args.adjusted_trades_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        adjusted.to_csv(
            output_path,
            index=False,
            compression="gzip" if str(output_path).endswith(".gz") else None,
        )
    if args.summary_output:
        _write_json(
            Path(args.summary_output),
            build_backtest_summary_payload(
                trades=adjusted,
                policy=policy,
                starting_balance=starting_balance,
                policy_input=str(policy_path.resolve()),
            ),
        )
    print(json.dumps(summary, indent=2))
    return 0


def enrich_features_command(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input)
    compression = "gzip" if str(output).endswith(".gz") else None
    wrote_any = False
    for chunk in pd.read_csv(input_path, chunksize=25000):
        enriched = enrich_with_regime_features(chunk)
        enriched.to_csv(
            output,
            mode="a" if wrote_any else "w",
            index=False,
            header=not wrote_any,
            compression=compression,
        )
        wrote_any = True
    print(output)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Frontier prop-manager utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_policy = subparsers.add_parser("build-policy", help="Build a contextual frontier manager policy.")
    build_policy.add_argument("--analysis-report", required=True)
    build_policy.add_argument("--baseline-report", required=True)
    build_policy.add_argument("--trades", required=True)
    build_policy.add_argument("--output", required=True)
    build_policy.set_defaults(func=build_policy_command)

    evaluate = subparsers.add_parser("evaluate-policy", help="Estimate policy changes on the existing trade path.")
    evaluate.add_argument("--policy", required=True)
    evaluate.add_argument("--trades", required=True)
    evaluate.add_argument("--baseline-report", required=True)
    evaluate.add_argument("--output")
    evaluate.add_argument("--adjusted-trades-output")
    evaluate.add_argument("--summary-output")
    evaluate.set_defaults(func=evaluate_policy_command)

    enrich = subparsers.add_parser("enrich-features", help="Add regime features to a feature dataset export.")
    enrich.add_argument("--input", required=True)
    enrich.add_argument("--output", required=True)
    enrich.set_defaults(func=enrich_features_command)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
