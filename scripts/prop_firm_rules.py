from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class PropFirmPolicy:
    name: str
    evaluation_steps: int
    profit_split_pct: float
    profit_target_pct: float
    min_profitable_days: int
    max_daily_loss_pct: float
    max_total_drawdown_pct: float
    max_loss_per_trade_pct: float
    drawdown_type: str
    stop_loss_required: bool
    leverage: str
    swap_free: bool
    weekend_holding_allowed_evaluation: bool
    weekend_holding_allowed_funded: bool
    no_time_limit: bool


FUNDEDHIVE_POLICY = PropFirmPolicy(
    name="FundedHive",
    evaluation_steps=1,
    profit_split_pct=80.0,
    profit_target_pct=10.0,
    min_profitable_days=3,
    max_daily_loss_pct=5.0,
    max_total_drawdown_pct=10.0,
    max_loss_per_trade_pct=3.0,
    drawdown_type="static",
    stop_loss_required=True,
    leverage="1:50",
    swap_free=True,
    weekend_holding_allowed_evaluation=True,
    weekend_holding_allowed_funded=False,
    no_time_limit=True,
)


def fundedhive_backtest_defaults() -> Dict[str, object]:
    return {
        "policy_name": FUNDEDHIVE_POLICY.name,
        "profit_target_pct": FUNDEDHIVE_POLICY.profit_target_pct,
        "min_profitable_days": FUNDEDHIVE_POLICY.min_profitable_days,
        "max_daily_loss_pct": FUNDEDHIVE_POLICY.max_daily_loss_pct,
        "max_total_drawdown_pct": FUNDEDHIVE_POLICY.max_total_drawdown_pct,
        "max_loss_per_trade_pct": FUNDEDHIVE_POLICY.max_loss_per_trade_pct,
        "drawdown_type": FUNDEDHIVE_POLICY.drawdown_type,
        "stop_loss_required": FUNDEDHIVE_POLICY.stop_loss_required,
    }


def policy_metadata() -> Dict[str, object]:
    return asdict(FUNDEDHIVE_POLICY)


def evaluate_propfirm_path(
    daily_returns_pct: Iterable[float],
    starting_balance: float,
    profit_target_pct: float,
    max_total_drawdown_pct: float,
    min_profitable_days: int,
) -> Dict[str, Optional[object]]:
    balance = float(starting_balance)
    floor_balance = starting_balance * (1.0 - max_total_drawdown_pct / 100.0)
    profit_target = starting_balance * (1.0 + profit_target_pct / 100.0)
    profitable_days = 0
    breached = False
    passed = False
    days_to_pass = None

    for day_number, day_return_pct in enumerate(daily_returns_pct, start=1):
        day_return_pct = float(day_return_pct)
        balance *= 1.0 + day_return_pct / 100.0
        if day_return_pct > 0.0:
            profitable_days += 1
        if balance <= floor_balance:
            breached = True
            break
        if balance >= profit_target and profitable_days >= min_profitable_days:
            passed = True
            days_to_pass = day_number
            break

    return {
        "passed": passed,
        "days_to_pass": days_to_pass,
        "profitable_days": profitable_days,
        "breached_total_drawdown": breached,
        "ending_balance": round(balance, 2),
    }
