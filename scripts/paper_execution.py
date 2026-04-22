from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from sklearn.metrics import average_precision_score

from frontier_execution import ExecutionPolicy, OrderPlan, TradeResolution, try_resolve_trade_on_bars


def _load_price_bars(path: Path) -> pd.DataFrame:
    usecols = ["timestamp", "segment_id", "open", "high", "low", "close"]
    frame = pd.read_csv(path, compression="gzip" if str(path).endswith(".gz") else None, usecols=usecols)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["segment_id"] = pd.to_numeric(frame["segment_id"], errors="raise").astype(int)
    return frame.sort_values("timestamp").reset_index(drop=True)


def load_paper_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"open_positions": [], "closed_trades": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_paper_state(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_open_position(
    state: Dict[str, object],
    instrument_id: str,
    dataset_path: str,
    segment_id: int,
    order_plan: Dict[str, object],
    candidate: Dict[str, object],
) -> None:
    open_positions = list(state.get("open_positions", []))
    open_positions.append(
        {
            "instrument_id": instrument_id,
            "dataset_path": dataset_path,
            "segment_id": int(segment_id),
            "order_plan": order_plan,
            "candidate": candidate,
        }
    )
    state["open_positions"] = open_positions


def sync_paper_positions(
    state: Dict[str, object],
    execution_policy: ExecutionPolicy,
) -> Dict[str, object]:
    remaining: List[Dict[str, object]] = []
    closed_trades = list(state.get("closed_trades", []))
    for item in state.get("open_positions", []):
        bars = _load_price_bars(Path(item["dataset_path"]))
        order_plan_payload = dict(item["order_plan"])
        order_plan = OrderPlan(
            instrument_id=order_plan_payload["instrument_id"],
            direction=order_plan_payload["direction"],
            chosen_setup=order_plan_payload["chosen_setup"],
            signal_timestamp=order_plan_payload["signal_timestamp"],
            entry_price=float(order_plan_payload["entry_price"]),
            stop_price=float(order_plan_payload["stop_price"]),
            target_price=float(order_plan_payload["target_price"]),
            stop_distance=float(order_plan_payload["stop_distance"]),
            target_distance=float(order_plan_payload["target_distance"]),
            size=float(order_plan_payload["size"]),
            risk_pct=float(order_plan_payload["risk_pct"]),
            risk_cash=float(order_plan_payload["risk_cash"]),
            point_value=float(order_plan_payload["point_value"]),
            predicted_frontier_score=float(order_plan_payload["predicted_frontier_score"]),
            predicted_frontier_score_raw=float(order_plan_payload["predicted_frontier_score_raw"]),
            probability=float(order_plan_payload["probability"]),
        )
        resolution = try_resolve_trade_on_bars(
            bars=bars,
            entry_timestamp=item["order_plan"]["signal_timestamp"],
            segment_id=int(item["segment_id"]),
            plan=order_plan,
            policy=execution_policy,
        )
        if resolution is None:
            remaining.append(item)
            continue
        closed_trades.append(
            {
                "instrument_id": item["instrument_id"],
                "candidate": item["candidate"],
                "order_plan": item["order_plan"],
                "resolution": asdict(resolution),
            }
        )
    state["open_positions"] = remaining
    state["closed_trades"] = closed_trades
    return state


def build_paper_summary(state: Dict[str, object]) -> Dict[str, object]:
    closed = list(state.get("closed_trades", []))
    if not closed:
        return {
            "active_trades": len(state.get("open_positions", [])),
            "closed_trades": 0,
            "rolling_pnl_cash": 0.0,
            "rolling_pnl_r": 0.0,
            "drawdown_cash": 0.0,
            "by_setup": {},
        }
    equity = 0.0
    peak = 0.0
    worst_drawdown = 0.0
    by_setup: Dict[str, Dict[str, float]] = {}
    setup_samples: Dict[str, List[tuple[float, int, str]]] = {}
    for item in closed:
        candidate = item.get("candidate", {})
        resolution = item.get("resolution", {})
        setup = str(candidate.get("chosen_setup", ""))
        pnl_cash = float(resolution.get("pnl_cash", 0.0))
        pnl_r = float(resolution.get("pnl_r", 0.0))
        probability = float(candidate.get("probability", 0.0))
        label = 1 if pnl_r > 0.0 else 0
        context_key = f"{candidate.get('market_session', '')}|{candidate.get('session_phase', '')}"
        equity += pnl_cash
        peak = max(peak, equity)
        worst_drawdown = min(worst_drawdown, equity - peak)
        row = by_setup.setdefault(setup, {"trades": 0, "pnl_cash": 0.0, "pnl_r": 0.0})
        row["trades"] += 1
        row["pnl_cash"] += pnl_cash
        row["pnl_r"] += pnl_r
        setup_samples.setdefault(setup, []).append((probability, label, context_key))
    performance: Dict[str, Dict[str, object]] = {}
    for setup, samples in setup_samples.items():
        probs = [item[0] for item in samples[-50:]]
        labels = [item[1] for item in samples[-50:]]
        contexts: Dict[str, List[tuple[float, int]]] = {}
        for probability, label, context_key in samples[-50:]:
            contexts.setdefault(context_key, []).append((probability, label))
        performance[setup] = {
            "trades": len(samples),
            "rolling_pnl_r": round(float(by_setup.get(setup, {}).get("pnl_r", 0.0)), 6),
            "rolling_ap": round(float(average_precision_score(labels, probs)) if any(labels) else 0.0, 6),
            "contexts": {
                key: {
                    "trades": len(values),
                    "rolling_ap": round(
                        float(
                            average_precision_score(
                                [label for _, label in values],
                                [prob for prob, _ in values],
                            )
                        )
                        if any(label for _, label in values)
                        else 0.0,
                        6,
                    ),
                    "rolling_pnl_r": round(
                        float(
                            sum(
                                float(closed_item["resolution"].get("pnl_r", 0.0))
                                for closed_item in closed[-50:]
                                if str(closed_item.get("candidate", {}).get("chosen_setup", "")) == setup
                                and f"{closed_item.get('candidate', {}).get('market_session', '')}|{closed_item.get('candidate', {}).get('session_phase', '')}" == key
                            )
                        ),
                        6,
                    ),
                }
                for key, values in contexts.items()
            },
        }
    return {
        "active_trades": len(state.get("open_positions", [])),
        "closed_trades": len(closed),
        "rolling_pnl_cash": round(sum(float(item["resolution"].get("pnl_cash", 0.0)) for item in closed[-20:]), 6),
        "rolling_pnl_r": round(sum(float(item["resolution"].get("pnl_r", 0.0)) for item in closed[-20:]), 6),
        "drawdown_cash": round(abs(worst_drawdown), 6),
        "by_setup": by_setup,
        "performance": performance,
    }
