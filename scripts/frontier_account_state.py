from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AccountStateConfig:
    starting_balance: float = 100000.0
    profit_target_pct: float = 10.0
    min_profitable_days: int = 3
    max_daily_loss_pct: float = 5.0
    max_total_drawdown_pct: float = 10.0
    max_trades_per_day: int = 2
    risk_per_trade_pct: float = 0.25
    initial_account_stage: str = "challenge"

    @property
    def target_balance(self) -> float:
        return self.starting_balance * (1.0 + self.profit_target_pct / 100.0)

    @property
    def floor_balance(self) -> float:
        return self.starting_balance * (1.0 - self.max_total_drawdown_pct / 100.0)


@dataclass
class AccountState:
    balance: float
    running_peak: float
    profitable_days: int
    losing_days: int
    day_pnl_cash: float
    day_pnl_pct: float
    trades_taken_today: int
    win_streak: int
    loss_streak: int
    days_elapsed: int
    current_day: Optional[date] = None
    last_trade_pnl_r: float = 0.0
    completed_days: Tuple[float, ...] = ()
    completed_day_pnls_cash: Tuple[float, ...] = ()
    completed_day_dates: Tuple[str, ...] = ()

    def snapshot(self, config: AccountStateConfig) -> Dict[str, float]:
        passed_challenge = (
            self.balance >= config.target_balance
            and self.profitable_days >= config.min_profitable_days
        )
        if str(config.initial_account_stage) == "funded":
            account_stage = "funded"
        else:
            account_stage = "funded" if passed_challenge else "challenge"
        distance_to_target_pct = max(
            0.0,
            (config.target_balance - self.balance) / config.starting_balance * 100.0,
        )
        drawdown_pct = 0.0
        if self.running_peak > 0.0:
            drawdown_pct = max(0.0, (self.running_peak - self.balance) / self.running_peak * 100.0)
        profitable_days_remaining = max(0, config.min_profitable_days - self.profitable_days)
        day_loss_budget_remaining_pct = max(0.0, config.max_daily_loss_pct + self.day_pnl_pct)
        total_drawdown_budget_remaining_pct = max(
            0.0,
            (self.balance - config.floor_balance) / config.starting_balance * 100.0,
        )
        completed_returns = list(self.completed_days)
        if self.current_day is not None and self.stateful_day_has_activity():
            completed_returns = completed_returns + [self.day_pnl_pct]
        rolling_10 = completed_returns[-10:]
        rolling_20 = completed_returns[-20:]
        current_month_return_pct = 0.0
        current_month_trade_days = 0
        if self.current_day is not None:
            month_prefix = self.current_day.strftime("%Y-%m")
            for day_label, day_return in zip(self.completed_day_dates, self.completed_days):
                if day_label.startswith(month_prefix):
                    current_month_return_pct += float(day_return)
                    current_month_trade_days += 1
            if self.stateful_day_has_activity() and self.current_day.strftime("%Y-%m") == month_prefix:
                current_month_return_pct += float(self.day_pnl_pct)
                current_month_trade_days += 1
        rolling_loss_cluster_penalty = self._loss_cluster_penalty(completed_returns)
        return {
            "account_stage": account_stage,
            "account_stage_code": 1.0 if account_stage == "funded" else 0.0,
            "account_passed_challenge": 1.0 if passed_challenge else 0.0,
            "account_balance": round(self.balance, 6),
            "account_return_pct_to_date": round(
                (self.balance / config.starting_balance - 1.0) * 100.0,
                6,
            ),
            "account_drawdown_pct": round(drawdown_pct, 6),
            "account_distance_to_target_pct": round(distance_to_target_pct, 6),
            "account_profitable_days_so_far": int(self.profitable_days),
            "account_profitable_days_remaining": int(profitable_days_remaining),
            "account_days_elapsed": int(self.days_elapsed),
            "day_pnl_pct_so_far": round(self.day_pnl_pct, 6),
            "day_loss_budget_remaining_pct": round(day_loss_budget_remaining_pct, 6),
            "total_drawdown_budget_remaining_pct": round(total_drawdown_budget_remaining_pct, 6),
            "trades_taken_today": int(self.trades_taken_today),
            "trade_slots_remaining_today": int(max(0, config.max_trades_per_day - self.trades_taken_today)),
            "last_trade_pnl_r": round(self.last_trade_pnl_r, 6),
            "win_streak": int(self.win_streak),
            "loss_streak": int(self.loss_streak),
            "rolling_10_day_return_pct": round(sum(rolling_10), 6),
            "rolling_20_day_return_pct": round(sum(rolling_20), 6),
            "rolling_10_day_avg_return_pct": round(sum(rolling_10) / len(rolling_10), 6) if rolling_10 else 0.0,
            "rolling_20_day_avg_return_pct": round(sum(rolling_20) / len(rolling_20), 6) if rolling_20 else 0.0,
            "rolling_loss_cluster_penalty": round(rolling_loss_cluster_penalty, 6),
            "current_month_return_pct": round(current_month_return_pct, 6),
            "current_month_trade_days": int(current_month_trade_days),
        }

    def stateful_day_has_activity(self) -> bool:
        return self.trades_taken_today > 0 or abs(self.day_pnl_cash) > 0.0

    @staticmethod
    def _loss_cluster_penalty(values: List[float]) -> float:
        if not values:
            return 0.0
        negative_days = [value for value in values if value < 0.0]
        negative_rate = len(negative_days) / len(values)
        avg_negative = abs(sum(negative_days) / len(negative_days)) if negative_days else 0.0
        longest = 0
        current = 0
        for value in values:
            if value < 0.0:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        return negative_rate * avg_negative + 0.10 * longest


class AccountStateTracker:
    def __init__(self, config: AccountStateConfig):
        self.config = config
        self.state = AccountState(
            balance=config.starting_balance,
            running_peak=config.starting_balance,
            profitable_days=0,
            losing_days=0,
            day_pnl_cash=0.0,
            day_pnl_pct=0.0,
            trades_taken_today=0,
            win_streak=0,
            loss_streak=0,
            days_elapsed=0,
            current_day=None,
            last_trade_pnl_r=0.0,
        )

    def _roll_day_if_needed(self, trade_day: date) -> None:
        if self.state.current_day is None:
            self.state.current_day = trade_day
            self.state.days_elapsed = 1
            return
        if trade_day == self.state.current_day:
            return
        self._finalize_current_day()
        self.state.current_day = trade_day
        self.state.day_pnl_cash = 0.0
        self.state.day_pnl_pct = 0.0
        self.state.trades_taken_today = 0
        self.state.days_elapsed += 1

    def _finalize_current_day(self) -> None:
        if self.state.current_day is None:
            return
        if self.state.day_pnl_cash > 0.0:
            self.state.profitable_days += 1
        elif self.state.day_pnl_cash < 0.0:
            self.state.losing_days += 1
        if self.state.stateful_day_has_activity():
            self.state.completed_days = self.state.completed_days + (float(self.state.day_pnl_pct),)
            self.state.completed_day_pnls_cash = self.state.completed_day_pnls_cash + (float(self.state.day_pnl_cash),)
            self.state.completed_day_dates = self.state.completed_day_dates + (self.state.current_day.isoformat(),)

    def observe_day(self, trade_day: date) -> Dict[str, float]:
        self._roll_day_if_needed(trade_day)
        return self.state.snapshot(self.config)

    def apply_trade(self, trade_day: date, pnl_cash: float, pnl_r: float) -> Dict[str, float]:
        self._roll_day_if_needed(trade_day)
        self.state.day_pnl_cash += float(pnl_cash)
        self.state.day_pnl_pct = self.state.day_pnl_cash / self.config.starting_balance * 100.0
        self.state.trades_taken_today += 1
        self.state.balance += float(pnl_cash)
        self.state.running_peak = max(self.state.running_peak, self.state.balance)
        self.state.last_trade_pnl_r = float(pnl_r)
        if pnl_r > 0.0:
            self.state.win_streak += 1
            self.state.loss_streak = 0
        elif pnl_r < 0.0:
            self.state.loss_streak += 1
            self.state.win_streak = 0
        else:
            self.state.win_streak = 0
            self.state.loss_streak = 0
        return self.state.snapshot(self.config)

    def finalize(self) -> Dict[str, object]:
        profitable_days = self.state.profitable_days
        losing_days = self.state.losing_days
        if self.state.current_day is not None:
            if self.state.day_pnl_cash > 0.0:
                profitable_days += 1
            elif self.state.day_pnl_cash < 0.0:
                losing_days += 1
        completed_returns = list(self.state.completed_days)
        completed_dates = list(self.state.completed_day_dates)
        if self.state.current_day is not None and self.state.stateful_day_has_activity():
            completed_returns.append(float(self.state.day_pnl_pct))
            completed_dates.append(self.state.current_day.isoformat())
        return {
            "config": asdict(self.config),
            "final_state": self.state.snapshot(self.config),
            "realized_profitable_days": int(profitable_days),
            "realized_losing_days": int(losing_days),
            "completed_day_returns_pct": completed_returns,
            "completed_day_dates": completed_dates,
        }
