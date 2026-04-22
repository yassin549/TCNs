from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import pandas as pd


def load_trades(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, compression="gzip" if str(path).endswith(".gz") else None)
    frame["entry_timestamp"] = pd.to_datetime(frame["entry_timestamp"], utc=True)
    frame["exit_timestamp"] = pd.to_datetime(frame["exit_timestamp"], utc=True)
    return frame.sort_values(["entry_timestamp", "exit_timestamp"]).reset_index(drop=True)


def build_audit(frame: pd.DataFrame) -> Dict[str, object]:
    if frame.empty:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "breakeven_rate": 0.0,
            "zero_r_rate": 0.0,
            "exit_reason_counts": {},
            "r_distribution": {},
            "invariants": {
                "all_trades_have_exit_timestamp": True,
                "all_trades_have_valid_exit_reason": True,
                "all_trades_have_nonzero_risk_cash": True,
                "all_trades_have_positive_bars_held": True,
            },
        }

    exit_reasons = frame["exit_reason"].fillna("missing").astype(str)
    pnl_r = pd.to_numeric(frame["pnl_r"], errors="coerce")
    risk_cash = pd.to_numeric(frame["risk_cash"], errors="coerce")
    bars_held = pd.to_numeric(frame["bars_held"], errors="coerce")
    be_mask = exit_reasons.eq("breakeven") | pnl_r.eq(0.0)
    win_mask = pnl_r > 0.0
    loss_mask = pnl_r < 0.0
    audit = {
        "trades": int(len(frame)),
        "win_rate": round(float(win_mask.mean()), 6),
        "loss_rate": round(float(loss_mask.mean()), 6),
        "breakeven_rate": round(float(be_mask.mean()), 6),
        "zero_r_rate": round(float(pnl_r.eq(0.0).mean()), 6),
        "exit_reason_counts": exit_reasons.value_counts(dropna=False).to_dict(),
        "r_distribution": {
            "min": round(float(pnl_r.min()), 6),
            "p05": round(float(pnl_r.quantile(0.05)), 6),
            "median": round(float(pnl_r.median()), 6),
            "p95": round(float(pnl_r.quantile(0.95)), 6),
            "max": round(float(pnl_r.max()), 6),
        },
        "invariants": {
            "all_trades_have_exit_timestamp": bool(frame["exit_timestamp"].notna().all()),
            "all_trades_have_valid_exit_reason": bool(exit_reasons.isin(["stop", "target", "breakeven", "session_end", "max_hold"]).all()),
            "all_trades_have_nonzero_risk_cash": bool((risk_cash > 0.0).all()),
            "all_trades_have_positive_bars_held": bool((bars_held >= 1).all()),
        },
    }
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit trade lifecycle and R-multiple distribution.")
    parser.add_argument("--trades", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-breakeven-rate", type=float, default=0.30)
    args = parser.parse_args()

    frame = load_trades(Path(args.trades))
    audit = build_audit(frame)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(output)
    if float(audit["breakeven_rate"]) > float(args.max_breakeven_rate):
        raise SystemExit(
            f"Breakeven rate {audit['breakeven_rate']:.6f} exceeds allowed maximum {float(args.max_breakeven_rate):.6f}."
        )
    if not all(bool(value) for value in audit["invariants"].values()):
        raise SystemExit("Trade lifecycle invariant failure detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
