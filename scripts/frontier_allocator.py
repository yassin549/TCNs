from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class AllocationConfig:
    min_trade_score: float = 0.0
    max_trades_per_day: int = 2
    max_setup_share: float = 0.67
    challenge_max_setup_share: float = 1.0
    allow_continuation: bool = False
    continuation_setups: Tuple[str, ...] = ("long_continuation", "short_continuation")
    challenge_score_weight_utility: float = 1.10
    challenge_score_weight_pass5: float = 1.40
    challenge_score_weight_pass10: float = 1.00
    challenge_score_weight_pass20: float = 0.60
    challenge_score_weight_fail5: float = -1.20
    challenge_score_weight_fail10: float = -0.80
    challenge_score_weight_days_to_resolution: float = -0.08
    challenge_score_weight_distance_delta: float = 0.25
    challenge_score_weight_daily_loss_consumption: float = -0.08
    challenge_score_weight_total_drawdown_consumption: float = -0.05
    funded_score_weight_utility: float = 0.50
    funded_score_weight_return5: float = 0.80
    funded_score_weight_return20: float = 1.20
    funded_score_weight_breach5: float = -0.90
    funded_score_weight_breach20: float = -1.25
    funded_score_weight_drawdown: float = -0.60
    funded_score_weight_payout_growth: float = 0.90
    drawdown_soft_pct: float = 2.5
    drawdown_hard_pct: float = 5.0
    distance_to_target_soft_pct: float = 2.0
    soft_defensive_rolling_10_floor_pct: float = -0.75
    hard_defensive_rolling_10_floor_pct: float = -1.50
    shutdown_rolling_20_floor_pct: float = -2.50
    soft_loss_cluster_penalty_ceiling: float = 0.45
    hard_loss_cluster_penalty_ceiling: float = 0.75
    shutdown_loss_cluster_penalty_ceiling: float = 1.10
    soft_month_return_floor_pct: float = -0.75
    hard_month_return_floor_pct: float = -1.50
    shutdown_month_return_floor_pct: float = -2.25
    soft_defensive_max_trades: int = 2
    hard_defensive_max_trades: int = 1
    soft_defensive_score_bump: float = 0.05
    hard_defensive_score_bump: float = 0.12
    hard_defensive_disable_asia_build_20_40: bool = True
    challenge_min_risk_pct: float = 0.25
    challenge_base_risk_pct: float = 0.50
    challenge_max_risk_pct: float = 1.00
    challenge_near_target_risk_pct: float = 0.35
    funded_min_risk_pct: float = 0.10
    funded_base_risk_pct: float = 0.20
    funded_max_risk_pct: float = 0.50
    funded_defensive_risk_pct: float = 0.10


def _account_stage(account_state: Dict[str, float], config: AllocationConfig) -> str:
    stage = str(account_state.get("account_stage", "challenge"))
    return "funded" if stage == "funded" else "challenge"


def determine_kill_switch_state(account_state: Dict[str, float], config: AllocationConfig) -> str:
    account_stage = _account_stage(account_state, config)
    drawdown_pct = float(account_state.get("account_drawdown_pct", 0.0))
    rolling_10 = float(account_state.get("rolling_10_day_return_pct", 0.0))
    rolling_20 = float(account_state.get("rolling_20_day_return_pct", 0.0))
    loss_cluster_penalty = float(account_state.get("rolling_loss_cluster_penalty", 0.0))
    current_month_return = float(account_state.get("current_month_return_pct", 0.0))
    daily_loss_budget_remaining = float(account_state.get("day_loss_budget_remaining_pct", 0.0))
    total_drawdown_budget_remaining = float(account_state.get("total_drawdown_budget_remaining_pct", 0.0))
    if account_stage == "challenge":
        if (
            drawdown_pct >= config.drawdown_hard_pct
            or daily_loss_budget_remaining <= 0.0
            or total_drawdown_budget_remaining <= 0.0
        ):
            return "shutdown"
        if total_drawdown_budget_remaining <= 1.0 or daily_loss_budget_remaining <= 0.75:
            return "hard_defensive"
        return "normal"
    if (
        drawdown_pct >= config.drawdown_hard_pct
        or rolling_20 <= config.shutdown_rolling_20_floor_pct
        or loss_cluster_penalty >= config.shutdown_loss_cluster_penalty_ceiling
        or current_month_return <= config.shutdown_month_return_floor_pct
    ):
        return "shutdown"
    if (
        drawdown_pct >= config.drawdown_soft_pct
        or rolling_10 <= config.hard_defensive_rolling_10_floor_pct
        or loss_cluster_penalty >= config.hard_loss_cluster_penalty_ceiling
        or current_month_return <= config.hard_month_return_floor_pct
    ):
        return "hard_defensive"
    if (
        rolling_10 <= config.soft_defensive_rolling_10_floor_pct
        or loss_cluster_penalty >= config.soft_loss_cluster_penalty_ceiling
        or current_month_return <= config.soft_month_return_floor_pct
    ):
        return "soft_defensive"
    return "normal"


def _base_candidate_score(candidate: Dict[str, object], config: AllocationConfig) -> float:
    if "predicted_frontier_score" in candidate:
        return float(candidate.get("predicted_frontier_score", 0.0))
    if "predicted_trade_utility" not in candidate:
        return float(candidate.get("predicted_frontier_score", 0.0))
    account_stage = str(candidate.get("account_stage", "challenge"))
    if account_stage == "funded":
        return (
            config.funded_score_weight_utility * float(candidate.get("predicted_trade_utility", 0.0))
            + config.funded_score_weight_return5 * float(candidate.get("predicted_funded_expected_return_5d", 0.0))
            + config.funded_score_weight_return20 * float(candidate.get("predicted_funded_expected_return_20d", 0.0))
            + config.funded_score_weight_breach5 * float(candidate.get("predicted_funded_breach_risk_5d", 0.0))
            + config.funded_score_weight_breach20 * float(candidate.get("predicted_funded_breach_risk_20d", 0.0))
            + config.funded_score_weight_drawdown * float(candidate.get("predicted_funded_expected_drawdown", 0.0))
            + config.funded_score_weight_payout_growth * float(candidate.get("predicted_funded_expected_payout_growth", 0.0))
        )
    return (
        config.challenge_score_weight_utility * float(candidate.get("predicted_trade_utility", 0.0))
        + config.challenge_score_weight_pass5 * float(candidate.get("predicted_challenge_pass_prob_5d", 0.0))
        + config.challenge_score_weight_pass10 * float(candidate.get("predicted_challenge_pass_prob_10d", 0.0))
        + config.challenge_score_weight_pass20 * float(candidate.get("predicted_challenge_pass_prob_20d", 0.0))
        + config.challenge_score_weight_fail5 * float(candidate.get("predicted_challenge_fail_prob_5d", 0.0))
        + config.challenge_score_weight_fail10 * float(candidate.get("predicted_challenge_fail_prob_10d", 0.0))
        + config.challenge_score_weight_days_to_resolution * float(candidate.get("predicted_challenge_expected_days_to_resolution", 0.0))
        + config.challenge_score_weight_distance_delta * float(candidate.get("predicted_challenge_distance_to_target_delta", 0.0))
        + config.challenge_score_weight_daily_loss_consumption * float(candidate.get("predicted_challenge_daily_loss_budget_consumption", 0.0))
        + config.challenge_score_weight_total_drawdown_consumption * float(candidate.get("predicted_challenge_total_drawdown_budget_consumption", 0.0))
    )


def _marginal_score(candidate: Dict[str, object], account_state: Dict[str, float], config: AllocationConfig) -> float:
    score = _base_candidate_score(candidate, config)
    account_stage = _account_stage(account_state, config)
    drawdown_pct = float(account_state.get("account_drawdown_pct", 0.0))
    distance_to_target = float(account_state.get("account_distance_to_target_pct", 0.0))
    profitable_days_remaining = float(account_state.get("account_profitable_days_remaining", 0.0))
    days_elapsed = float(account_state.get("account_days_elapsed", 0.0))
    day_loss_budget_remaining = float(account_state.get("day_loss_budget_remaining_pct", 0.0))
    total_drawdown_budget_remaining = float(account_state.get("total_drawdown_budget_remaining_pct", 0.0))
    kill_switch_state = determine_kill_switch_state(account_state, config)
    if drawdown_pct >= config.drawdown_hard_pct:
        return -1e9
    if kill_switch_state == "shutdown":
        return -1e9
    if account_stage == "challenge":
        if distance_to_target >= 6.0 and drawdown_pct <= 1.5 and day_loss_budget_remaining >= 3.0:
            score += 0.15
        if days_elapsed >= 15 and distance_to_target >= 4.0:
            score += 0.15
        if profitable_days_remaining > 0:
            score += 0.20 * float(candidate.get("predicted_challenge_pass_prob_10d", 0.0))
        if total_drawdown_budget_remaining <= 2.0 or day_loss_budget_remaining <= 1.0:
            score -= 0.25
        return score
    if drawdown_pct >= config.drawdown_soft_pct:
        score -= 0.20
    if kill_switch_state == "soft_defensive":
        score -= config.soft_defensive_score_bump
    elif kill_switch_state == "hard_defensive":
        score -= config.hard_defensive_score_bump
    if distance_to_target <= config.distance_to_target_soft_pct and profitable_days_remaining > 0:
        score += 0.10 * float(candidate.get("predicted_challenge_pass_prob_5d", 0.0))
    return score


def allocate_day(
    day_candidates: List[Dict[str, object]],
    account_state: Dict[str, float],
    config: AllocationConfig,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    accepted: List[Dict[str, object]] = []
    rejected: List[Dict[str, object]] = []
    setup_counts: Dict[str, int] = {}
    account_stage = _account_stage(account_state, config)
    kill_switch_state = determine_kill_switch_state(account_state, config)
    effective_max_trades = config.max_trades_per_day
    if account_stage == "funded" and kill_switch_state == "soft_defensive":
        effective_max_trades = min(effective_max_trades, config.soft_defensive_max_trades)
    elif kill_switch_state == "hard_defensive":
        effective_max_trades = min(effective_max_trades, config.hard_defensive_max_trades)

    ranked = sorted(
        day_candidates,
        key=lambda row: (_marginal_score(row, account_state, config), float(row.get("probability", 0.0))),
        reverse=True,
    )
    for rank, candidate in enumerate(ranked, start=1):
        candidate = dict(candidate)
        candidate["allocator_rank_within_day"] = rank
        candidate["kill_switch_state"] = kill_switch_state
        setup = str(candidate["chosen_setup"])
        if kill_switch_state == "shutdown":
            candidate["allocator_decision"] = "rejected_by_allocator_kill_switch_shutdown"
            rejected.append(candidate)
            continue
        if (
            kill_switch_state == "hard_defensive"
            and config.hard_defensive_disable_asia_build_20_40
            and setup == "short_reversal"
            and str(candidate.get("market_session")) == "asia"
            and str(candidate.get("session_phase")) == "build_20_40"
        ):
            candidate["allocator_decision"] = "rejected_by_allocator_kill_switch_slice"
            rejected.append(candidate)
            continue
        score = _marginal_score(candidate, account_state, config)
        if score < config.min_trade_score:
            candidate["allocator_decision"] = "rejected_by_allocator_low_marginal_utility"
            rejected.append(candidate)
            continue
        if (not config.allow_continuation) and setup in set(config.continuation_setups):
            candidate["allocator_decision"] = "rejected_by_allocator_slot_competition"
            rejected.append(candidate)
            continue
        if len(accepted) >= effective_max_trades:
            candidate["allocator_decision"] = "rejected_by_allocator_budget"
            rejected.append(candidate)
            continue
        projected_count = setup_counts.get(setup, 0) + 1
        projected_share = projected_count / float(len(accepted) + 1)
        setup_share_cap = config.challenge_max_setup_share if account_stage == "challenge" else config.max_setup_share
        if len(accepted) >= 1 and projected_share > setup_share_cap:
            candidate["allocator_decision"] = "rejected_by_allocator_setup_concentration"
            rejected.append(candidate)
            continue
        candidate["allocator_decision"] = "accepted"
        candidate["allocator_score"] = round(score, 6)
        accepted.append(candidate)
        setup_counts[setup] = projected_count
    return accepted, rejected


def build_policy_payload(config: AllocationConfig) -> Dict[str, object]:
    return {
        "selection": "frontier_daily_allocator",
        "enabled_experts": [
            "long_reversal",
            "short_reversal",
        ]
        if not config.allow_continuation
        else [
            "long_reversal",
            "long_continuation",
            "short_reversal",
            "short_continuation",
        ],
        "disabled_experts": list(config.continuation_setups) if not config.allow_continuation else [],
        "allocation_config": asdict(config),
        "notes": [
            "Daily trade selection is performed jointly across same-day candidates.",
            "Selection uses the model's stage-aware frontier score directly when available so acceptance stays aligned with training-time ranking.",
            "Continuation experts stay disabled by default until they improve replay utility after slot competition.",
            "Allocator rank is stage-aware: challenge mode prioritizes fast pass or fast resolution, funded mode prioritizes return with breach control.",
            "Challenge mode is intentionally more aggressive and tolerates higher drawdown so long as hard prop-firm limits are respected.",
            "Weak-month and rolling-loss-cluster states mainly govern funded-mode survival rather than challenge-mode aggression.",
        ],
    }
