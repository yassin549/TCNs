from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd


def load_replay_trades(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, compression="gzip" if str(path).endswith(".gz") else None)
    if frame.empty:
        return frame
    frame["entry_timestamp"] = pd.to_datetime(frame["entry_timestamp"], utc=True)
    frame["exit_timestamp"] = pd.to_datetime(frame["exit_timestamp"], utc=True)
    return frame.sort_values(["entry_timestamp", "exit_timestamp"]).reset_index(drop=True)


def load_paper_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: List[Dict[str, object]] = []
    for item in payload.get("closed_trades", []):
        candidate = dict(item.get("candidate", {}))
        resolution = dict(item.get("resolution", {}))
        rows.append(
            {
                "instrument_id": item.get("instrument_id"),
                "chosen_setup": candidate.get("chosen_setup"),
                "entry_timestamp": resolution.get("entry_timestamp") or candidate.get("timestamp"),
                "exit_timestamp": resolution.get("exit_timestamp"),
                "exit_reason": resolution.get("exit_reason"),
                "pnl_r": resolution.get("pnl_r"),
                "pnl_cash": resolution.get("pnl_cash"),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["entry_timestamp"] = pd.to_datetime(frame["entry_timestamp"], utc=True)
    frame["exit_timestamp"] = pd.to_datetime(frame["exit_timestamp"], utc=True)
    frame["pnl_r"] = pd.to_numeric(frame["pnl_r"], errors="coerce")
    frame["pnl_cash"] = pd.to_numeric(frame["pnl_cash"], errors="coerce")
    return frame.sort_values(["entry_timestamp", "exit_timestamp"]).reset_index(drop=True)


def summarize(frame: pd.DataFrame) -> Dict[str, object]:
    if frame.empty:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "breakeven_rate": 0.0,
            "expectancy_r": 0.0,
            "median_r": 0.0,
            "exit_reason_counts": {},
            "by_setup": {},
        }
    pnl_r = pd.to_numeric(frame["pnl_r"], errors="coerce").fillna(0.0)
    win_mask = pnl_r > 0.0
    loss_mask = pnl_r < 0.0
    be_mask = pnl_r.eq(0.0) | frame["exit_reason"].fillna("").eq("breakeven")
    setup_column = "chosen_setup" if "chosen_setup" in frame.columns else "setup"
    by_setup: Dict[str, Dict[str, object]] = {}
    for setup, setup_frame in frame.groupby(setup_column, dropna=False):
        setup_pnl_r = pd.to_numeric(setup_frame["pnl_r"], errors="coerce").fillna(0.0)
        by_setup[str(setup)] = {
            "trades": int(len(setup_frame)),
            "win_rate": round(float((setup_pnl_r > 0.0).mean()), 6),
            "loss_rate": round(float((setup_pnl_r < 0.0).mean()), 6),
            "breakeven_rate": round(float((setup_pnl_r == 0.0).mean()), 6),
            "expectancy_r": round(float(setup_pnl_r.mean()), 6),
        }
    return {
        "trades": int(len(frame)),
        "win_rate": round(float(win_mask.mean()), 6),
        "loss_rate": round(float(loss_mask.mean()), 6),
        "breakeven_rate": round(float(be_mask.mean()), 6),
        "expectancy_r": round(float(pnl_r.mean()), 6),
        "median_r": round(float(pnl_r.median()), 6),
        "exit_reason_counts": frame["exit_reason"].fillna("missing").astype(str).value_counts(dropna=False).to_dict(),
        "by_setup": by_setup,
    }


def build_comparison(replay_summary: Dict[str, object], paper_summary: Dict[str, object], min_live_trades: int) -> Dict[str, object]:
    paper_trades = int(paper_summary["trades"])
    deltas = {
        "win_rate_delta": round(float(paper_summary["win_rate"]) - float(replay_summary["win_rate"]), 6),
        "loss_rate_delta": round(float(paper_summary["loss_rate"]) - float(replay_summary["loss_rate"]), 6),
        "breakeven_rate_delta": round(float(paper_summary["breakeven_rate"]) - float(replay_summary["breakeven_rate"]), 6),
        "expectancy_r_delta": round(float(paper_summary["expectancy_r"]) - float(replay_summary["expectancy_r"]), 6),
    }
    if paper_trades < int(min_live_trades):
        status = "insufficient_live_trades"
    elif float(paper_summary["breakeven_rate"]) > 0.30:
        status = "live_breakeven_rate_invalid"
    else:
        status = "comparable"
    return {
        "status": status,
        "min_live_trades_required": int(min_live_trades),
        "replay": replay_summary,
        "paper": paper_summary,
        "deltas": deltas,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare corrected replay trade distribution against paper/live trade distribution.")
    parser.add_argument("--replay-trades", required=True)
    parser.add_argument("--paper-state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-live-trades", type=int, default=20)
    args = parser.parse_args()

    replay = load_replay_trades(Path(args.replay_trades))
    paper = load_paper_trades(Path(args.paper_state))
    comparison = build_comparison(summarize(replay), summarize(paper), min_live_trades=int(args.min_live_trades))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
