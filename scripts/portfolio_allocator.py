from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from frontier_account_state import AccountStateConfig
from frontier_allocator import AllocationConfig, allocate_day
from frontier_execution import ContractSpec, direction_for_setup


@dataclass(frozen=True)
class PortfolioConstraints:
    max_concurrent_trades: int = 2
    max_portfolio_risk_pct: float = 1.0
    max_same_direction_per_correlation_group: int = 1


@dataclass(frozen=True)
class SpecialistPerformanceConstraints:
    min_trades_for_disable: int = 10
    min_rolling_ap: float = 0.05
    min_rolling_pnl_r: float = -1.0


def default_correlation_group(instrument_id: str) -> str:
    normalized = str(instrument_id).upper()
    if normalized in {"US100", "US500"}:
        return "US_INDICES"
    return normalized


def specialist_is_enabled(
    candidate: Dict[str, object],
    performance_state: Optional[Dict[str, Dict[str, object]]] = None,
    performance_constraints: Optional[SpecialistPerformanceConstraints] = None,
) -> bool:
    setup = str(candidate.get("chosen_setup", ""))
    if setup != "short_reversal":
        pass
    elif not (
        str(candidate.get("market_session", "")) == "asia"
        and str(candidate.get("session_phase", "")) == "build_20_40"
    ):
        return False
    if not performance_state or not performance_constraints:
        return True
    setup_state = performance_state.get(setup)
    if not setup_state:
        return True
    if int(setup_state.get("trades", 0)) < int(performance_constraints.min_trades_for_disable):
        return True
    if float(setup_state.get("rolling_ap", 1.0)) < float(performance_constraints.min_rolling_ap):
        return False
    if float(setup_state.get("rolling_pnl_r", 0.0)) < float(performance_constraints.min_rolling_pnl_r):
        return False
    context_key = f"{candidate.get('market_session', '')}|{candidate.get('session_phase', '')}"
    context_state = setup_state.get("contexts", {}).get(context_key)
    if not context_state:
        return True
    if int(context_state.get("trades", 0)) < int(performance_constraints.min_trades_for_disable):
        return True
    if float(context_state.get("rolling_ap", 1.0)) < float(performance_constraints.min_rolling_ap):
        return False
    if float(context_state.get("rolling_pnl_r", 0.0)) < float(performance_constraints.min_rolling_pnl_r):
        return False
    return True


def allocate_portfolio(
    candidates: List[Dict[str, object]],
    account_state: Dict[str, object],
    account_config: AccountStateConfig,
    allocation_config: AllocationConfig,
    constraints: PortfolioConstraints,
    contract_specs: Optional[Dict[str, ContractSpec]] = None,
    current_open_positions: Optional[List[Dict[str, object]]] = None,
    performance_state: Optional[Dict[str, Dict[str, object]]] = None,
    performance_constraints: Optional[SpecialistPerformanceConstraints] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    prefiltered: List[Dict[str, object]] = []
    rejected: List[Dict[str, object]] = []
    for row in candidates:
        candidate = dict(row)
        if not specialist_is_enabled(candidate, performance_state, performance_constraints):
            candidate["allocator_decision"] = "rejected_by_specialist_guard"
            rejected.append(candidate)
            continue
        prefiltered.append(candidate)

    accepted, allocator_rejected = allocate_day(prefiltered, account_state, allocation_config)
    rejected.extend(allocator_rejected)

    open_positions = current_open_positions or []
    active_risk_pct = sum(float(item.get("risk_pct", 0.0)) for item in open_positions)
    active_count = len(open_positions)
    accepted_final: List[Dict[str, object]] = []
    direction_by_group: Dict[str, Dict[str, int]] = {}
    for open_position in open_positions:
        instrument_id = str(open_position.get("instrument_id", ""))
        group = default_correlation_group(instrument_id)
        direction = str(open_position.get("direction", ""))
        group_counts = direction_by_group.setdefault(group, {})
        group_counts[direction] = group_counts.get(direction, 0) + 1

    for candidate in accepted:
        from frontier_replay import _stage_risk_pct

        instrument_id = str(candidate.get("instrument_id", ""))
        group = default_correlation_group(instrument_id)
        direction = direction_for_setup(str(candidate.get("chosen_setup", "")))
        risk_pct = _stage_risk_pct(candidate, account_state, account_config, allocation_config)
        if active_count + len(accepted_final) >= int(constraints.max_concurrent_trades):
            candidate["allocator_decision"] = "rejected_by_portfolio_concurrency"
            rejected.append(candidate)
            continue
        if active_risk_pct + sum(float(item.get("applied_risk_pct", 0.0)) for item in accepted_final) + risk_pct > float(constraints.max_portfolio_risk_pct):
            candidate["allocator_decision"] = "rejected_by_portfolio_risk"
            rejected.append(candidate)
            continue
        group_counts = direction_by_group.setdefault(group, {})
        if group_counts.get(direction, 0) >= int(constraints.max_same_direction_per_correlation_group):
            candidate["allocator_decision"] = "rejected_by_portfolio_correlation"
            rejected.append(candidate)
            continue
        candidate["applied_risk_pct"] = round(float(risk_pct), 6)
        candidate["correlation_group"] = group
        accepted_final.append(candidate)
        group_counts[direction] = group_counts.get(direction, 0) + 1
    return accepted_final, rejected
