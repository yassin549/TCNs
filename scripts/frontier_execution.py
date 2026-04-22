from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


LONG_SETUPS = {"long_reversal", "long_continuation"}
SHORT_SETUPS = {"short_reversal", "short_continuation"}
VALID_SETUPS = LONG_SETUPS | SHORT_SETUPS
VALID_EXIT_REASONS = {"stop", "target", "breakeven", "session_end", "max_hold"}


@dataclass(frozen=True)
class ContractSpec:
    instrument_id: str
    point_value: float
    min_size: float
    size_step: float
    max_positions_per_epic: int = 1
    stop_atr_multiple: float = 0.75
    target_atr_multiple: float = 1.25


@dataclass(frozen=True)
class ExecutionPolicy:
    stop_atr_multiple: float = 0.75
    target_atr_multiple: float = 1.25
    breakeven_trigger_r: Optional[float] = None
    max_hold_bars: int = 0
    intrabar_conflict_resolution: str = "conservative_stop"


@dataclass(frozen=True)
class OrderPlan:
    instrument_id: str
    direction: str
    chosen_setup: str
    signal_timestamp: str
    entry_price: float
    stop_price: float
    target_price: float
    stop_distance: float
    target_distance: float
    size: float
    risk_pct: float
    risk_cash: float
    point_value: float
    predicted_frontier_score: float
    predicted_frontier_score_raw: float
    probability: float


@dataclass(frozen=True)
class TradeResolution:
    entry_timestamp: str
    exit_timestamp: str
    entry_price: float
    exit_price: float
    bars_held: int
    exit_reason: str
    pnl_r: float
    pnl_cash: float
    risk_cash: float
    risk_pct: float
    stop_price: float
    target_price: float
    max_favorable_excursion_r: float
    max_adverse_excursion_r: float


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(parsed):
        return default
    return float(parsed)


def direction_for_setup(setup: str) -> str:
    if setup in LONG_SETUPS:
        return "BUY"
    if setup in SHORT_SETUPS:
        return "SELL"
    raise ValueError(f"Unknown setup for direction: {setup}")


def signed_direction(direction: str) -> float:
    normalized = str(direction).upper()
    if normalized == "BUY":
        return 1.0
    if normalized == "SELL":
        return -1.0
    raise ValueError(f"Unsupported direction: {direction}")


def round_to_step(value: float, step: float, minimum: float) -> float:
    if step <= 0.0:
        return round(max(value, minimum), 10)
    units = np.floor(max(value, minimum) / step)
    rounded = float(units * step)
    if rounded < minimum:
        rounded = minimum
    return round(float(rounded), 10)


def validate_contract_spec(contract: ContractSpec) -> None:
    if contract.point_value <= 0.0:
        raise ValueError(f"{contract.instrument_id}: point_value must be > 0.")
    if contract.min_size <= 0.0:
        raise ValueError(f"{contract.instrument_id}: min_size must be > 0.")
    if contract.size_step <= 0.0:
        raise ValueError(f"{contract.instrument_id}: size_step must be > 0.")
    if contract.stop_atr_multiple <= 0.0:
        raise ValueError(f"{contract.instrument_id}: stop_atr_multiple must be > 0.")
    if contract.target_atr_multiple <= 0.0:
        raise ValueError(f"{contract.instrument_id}: target_atr_multiple must be > 0.")
    if contract.max_positions_per_epic <= 0:
        raise ValueError(f"{contract.instrument_id}: max_positions_per_epic must be >= 1.")


def build_order_plan(
    candidate: Dict[str, object],
    contract: ContractSpec,
    account_balance: float,
    risk_pct: float,
    market_min_size: float = 0.0,
    market_size_step: float = 0.0,
) -> OrderPlan:
    validate_contract_spec(contract)
    setup = str(candidate.get("chosen_setup", ""))
    if setup not in VALID_SETUPS:
        raise ValueError(f"Unsupported chosen_setup: {setup}")
    entry_price = _safe_float(candidate.get("close"))
    atr_14 = _safe_float(candidate.get("atr_14"))
    if entry_price <= 0.0:
        raise ValueError(f"{contract.instrument_id}: entry_price must be > 0.")
    if atr_14 <= 0.0:
        raise ValueError(f"{contract.instrument_id}: atr_14 must be > 0.")
    if risk_pct <= 0.0:
        raise ValueError(f"{contract.instrument_id}: risk_pct must be > 0.")
    direction = direction_for_setup(setup)
    sign = signed_direction(direction)
    risk_cash = float(account_balance) * (float(risk_pct) / 100.0)
    stop_distance = max(atr_14 * contract.stop_atr_multiple, 0.25)
    target_distance = max(atr_14 * contract.target_atr_multiple, stop_distance)
    effective_min_size = max(contract.min_size, float(market_min_size))
    effective_size_step = max(contract.size_step, float(market_size_step))
    raw_size = risk_cash / max(stop_distance * contract.point_value, 1e-9)
    size = round_to_step(raw_size, effective_size_step, effective_min_size)
    stop_price = entry_price - sign * stop_distance
    target_price = entry_price + sign * target_distance
    return OrderPlan(
        instrument_id=contract.instrument_id,
        direction=direction,
        chosen_setup=setup,
        signal_timestamp=str(candidate.get("timestamp", "")),
        entry_price=round(entry_price, 10),
        stop_price=round(stop_price, 10),
        target_price=round(target_price, 10),
        stop_distance=round(stop_distance, 10),
        target_distance=round(target_distance, 10),
        size=size,
        risk_pct=round(float(risk_pct), 6),
        risk_cash=round(risk_cash, 6),
        point_value=round(contract.point_value, 10),
        predicted_frontier_score=round(_safe_float(candidate.get("predicted_frontier_score")), 6),
        predicted_frontier_score_raw=round(_safe_float(candidate.get("predicted_frontier_score_raw")), 6),
        probability=round(_safe_float(candidate.get("probability")), 6),
    )


def order_plan_to_dict(plan: OrderPlan) -> Dict[str, object]:
    return asdict(plan)


def resolution_to_dict(resolution: TradeResolution) -> Dict[str, object]:
    return asdict(resolution)


def validate_resolution(resolution: TradeResolution) -> None:
    if resolution.exit_reason not in VALID_EXIT_REASONS:
        raise ValueError(f"Unsupported exit_reason: {resolution.exit_reason}")
    if resolution.bars_held < 1:
        raise ValueError("bars_held must be >= 1.")
    if not np.isfinite(resolution.pnl_r):
        raise ValueError("pnl_r must be finite.")
    if resolution.risk_cash <= 0.0:
        raise ValueError("risk_cash must be > 0.")


def _hit_target(direction: str, high: float, low: float, target_price: float) -> bool:
    if direction == "BUY":
        return high >= target_price
    return low <= target_price


def _hit_stop(direction: str, high: float, low: float, stop_price: float) -> bool:
    if direction == "BUY":
        return low <= stop_price
    return high >= stop_price


def _conservative_intrabar_exit(direction: str, stop_price: float, target_price: float) -> tuple[str, float]:
    return "stop", stop_price


def resolve_trade_on_bars(
    bars: pd.DataFrame,
    entry_timestamp: object,
    segment_id: int,
    plan: OrderPlan,
    policy: ExecutionPolicy,
    settle_on_last_bar: bool = True,
) -> TradeResolution:
    if policy.intrabar_conflict_resolution != "conservative_stop":
        raise ValueError(f"Unsupported intrabar_conflict_resolution: {policy.intrabar_conflict_resolution}")
    required_columns = {"timestamp", "segment_id", "open", "high", "low", "close"}
    missing = sorted(required_columns - set(bars.columns))
    if missing:
        raise ValueError(f"Bars are missing required columns: {missing}")
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    entry_ts = pd.Timestamp(entry_timestamp)
    if entry_ts.tzinfo is None:
        entry_ts = entry_ts.tz_localize("UTC")
    same_segment = frame["segment_id"].astype(int) == int(segment_id)
    future = frame.loc[same_segment & (frame["timestamp"] > entry_ts)].copy()
    if future.empty:
        raise ValueError(f"No future bars available to resolve trade for {entry_ts.isoformat()}.")
    future = future.sort_values("timestamp").reset_index(drop=True)

    current_stop = float(plan.stop_price)
    entry_price = float(plan.entry_price)
    target_price = float(plan.target_price)
    direction = str(plan.direction).upper()
    sign = signed_direction(direction)
    stop_distance = max(abs(entry_price - current_stop), 1e-9)
    max_favorable_excursion_r = 0.0
    max_adverse_excursion_r = 0.0
    breakeven_armed = False

    if policy.breakeven_trigger_r is not None and policy.breakeven_trigger_r <= 0.0:
        raise ValueError("breakeven_trigger_r must be > 0 when provided.")

    for index, row in enumerate(future.itertuples(index=False), start=1):
        high = _safe_float(row.high)
        low = _safe_float(row.low)
        close = _safe_float(row.close)
        favorable_price = high if direction == "BUY" else low
        adverse_price = low if direction == "BUY" else high
        favorable_r = sign * (favorable_price - entry_price) / stop_distance
        adverse_r = sign * (adverse_price - entry_price) / stop_distance
        max_favorable_excursion_r = max(max_favorable_excursion_r, favorable_r)
        max_adverse_excursion_r = min(max_adverse_excursion_r, adverse_r)

        if policy.breakeven_trigger_r is not None and not breakeven_armed:
            if favorable_r >= float(policy.breakeven_trigger_r):
                current_stop = entry_price
                breakeven_armed = True

        target_hit = _hit_target(direction, high, low, target_price)
        stop_hit = _hit_stop(direction, high, low, current_stop)
        if target_hit and stop_hit:
            exit_reason, exit_price = _conservative_intrabar_exit(direction, current_stop, target_price)
        elif target_hit:
            exit_reason, exit_price = "target", target_price
        elif stop_hit:
            exit_reason = "breakeven" if breakeven_armed and abs(current_stop - entry_price) <= 1e-9 else "stop"
            exit_price = current_stop
        else:
            if policy.max_hold_bars > 0 and index >= int(policy.max_hold_bars):
                exit_reason = "max_hold"
                exit_price = close
            else:
                continue
        pnl_r = sign * (exit_price - entry_price) / stop_distance
        resolution = TradeResolution(
            entry_timestamp=entry_ts.isoformat(),
            exit_timestamp=pd.Timestamp(row.timestamp).isoformat(),
            entry_price=round(entry_price, 10),
            exit_price=round(float(exit_price), 10),
            bars_held=int(index),
            exit_reason=exit_reason,
            pnl_r=round(float(pnl_r), 6),
            pnl_cash=round(float(plan.risk_cash) * float(pnl_r), 6),
            risk_cash=round(float(plan.risk_cash), 6),
            risk_pct=round(float(plan.risk_pct), 6),
            stop_price=round(float(plan.stop_price), 10),
            target_price=round(float(plan.target_price), 10),
            max_favorable_excursion_r=round(float(max_favorable_excursion_r), 6),
            max_adverse_excursion_r=round(float(max_adverse_excursion_r), 6),
        )
        validate_resolution(resolution)
        return resolution

    if not settle_on_last_bar:
        raise ValueError(f"Trade remains open for {entry_ts.isoformat()}.")

    last_row = future.iloc[-1]
    exit_price = _safe_float(last_row["close"])
    pnl_r = sign * (exit_price - entry_price) / stop_distance
    resolution = TradeResolution(
        entry_timestamp=entry_ts.isoformat(),
        exit_timestamp=pd.Timestamp(last_row["timestamp"]).isoformat(),
        entry_price=round(entry_price, 10),
        exit_price=round(float(exit_price), 10),
        bars_held=int(len(future)),
        exit_reason="session_end",
        pnl_r=round(float(pnl_r), 6),
        pnl_cash=round(float(plan.risk_cash) * float(pnl_r), 6),
        risk_cash=round(float(plan.risk_cash), 6),
        risk_pct=round(float(plan.risk_pct), 6),
        stop_price=round(float(plan.stop_price), 10),
        target_price=round(float(plan.target_price), 10),
        max_favorable_excursion_r=round(float(max_favorable_excursion_r), 6),
        max_adverse_excursion_r=round(float(max_adverse_excursion_r), 6),
    )
    validate_resolution(resolution)
    return resolution


def try_resolve_trade_on_bars(
    bars: pd.DataFrame,
    entry_timestamp: object,
    segment_id: int,
    plan: OrderPlan,
    policy: ExecutionPolicy,
) -> Optional[TradeResolution]:
    try:
        return resolve_trade_on_bars(
            bars=bars,
            entry_timestamp=entry_timestamp,
            segment_id=segment_id,
            plan=plan,
            policy=policy,
            settle_on_last_bar=False,
        )
    except ValueError as exc:
        if "remains open" in str(exc):
            return None
        raise
