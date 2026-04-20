import importlib.machinery
import importlib.util
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from frontier_prop_manager import (
    _read_json as _frontier_read_json,
    apply_frontier_policy,
    build_backtest_summary_payload,
    load_trade_frame as load_frontier_trade_frame,
)


def _load_cached_module():
    cache_dir = Path(__file__).with_name("__pycache__")
    candidates = sorted(
        cache_dir.glob("specialist_tcn_pipeline.cpython-*.pyc*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for pyc_path in candidates:
        # Skip wrapper-only bytecode artifacts; the substantive pipeline caches
        # are materially larger and do not recurse back into this loader.
        if pyc_path.stat().st_size <= 10000:
            continue
        loader = importlib.machinery.SourcelessFileLoader(
            "_cached_specialist_tcn_pipeline",
            str(pyc_path),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        if spec is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        loader.exec_module(module)
        return module
    raise FileNotFoundError("No usable cached specialist_tcn_pipeline bytecode was found.")


_CACHED = _load_cached_module()


def _is_frontier_policy(policy_path: Path) -> bool:
    if not policy_path.exists():
        return False
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("selection") == "frontier_contextual_abstention_manager"


def _write_frontier_markdown(summary_payload: dict, policy_payload: dict, output_path: Path) -> None:
    enabled = ", ".join(policy_payload.get("enabled_experts", [])) or "none"
    disabled = ", ".join(policy_payload.get("disabled_experts", [])) or "none"
    summary = summary_payload.get("summary", {})
    raw_source_summary = summary_payload.get("raw_source_summary") or {}
    lines = [
        "# Frontier Manager Backtest",
        "",
        f"- Execution mode: `{summary_payload.get('execution_mode', 'frontier_managed')}`",
        f"- Policy selection: `{summary_payload.get('policy_selection', policy_payload.get('selection'))}`",
        f"- Split: `{summary_payload.get('split', 'test')}`",
        f"- Enabled experts: `{enabled}`",
        f"- Disabled experts: `{disabled}`",
        f"- Trades: `{summary.get('trades')}`",
        f"- Trading days: `{summary.get('trading_days')}`",
        f"- Win rate: `{summary.get('win_rate')}`",
        f"- Expectancy (R): `{summary.get('expectancy_r')}`",
        f"- Total R: `{summary.get('total_r')}`",
        f"- Profit factor: `{summary.get('profit_factor')}`",
        f"- Average hold bars: `{summary.get('average_hold_bars')}`",
        f"- Max drawdown %: `{summary.get('max_drawdown_pct')}`",
        f"- Ending balance: `{summary.get('ending_balance')}`",
        f"- Return %: `{summary.get('total_return_pct')}`",
        f"- Reached profit target: `{summary.get('reached_profit_target')}`",
        f"- Days to target: `{summary.get('days_to_target')}`",
        f"- Breached total drawdown: `{summary.get('breached_total_drawdown')}`",
        f"- 30/60/90 day pass probability: `{summary.get('pass_probability_30')}` / `{summary.get('pass_probability_60')}` / `{summary.get('pass_probability_90')}`",
        f"- Median / avg days to pass: `{summary.get('median_days_to_pass')}` / `{summary.get('avg_days_to_pass')}`",
        f"- Profitable-day hit rate day 10 / 20: `{summary.get('profitable_day_hit_rate_day_10')}` / `{summary.get('profitable_day_hit_rate_day_20')}`",
        f"- Longest negative day streak: `{summary.get('longest_negative_day_streak')}`",
        f"- Worst month return %: `{summary.get('worst_month_return_pct')}`",
        f"- Loss cluster penalty: `{summary.get('loss_cluster_penalty')}`",
        "",
        "## Canonical Benchmark",
        "",
        "- Frontier-managed outputs are the acceptance baseline for this artifact.",
        f"- Raw candidate source summary: `{raw_source_summary}`",
        "",
        "## Active Contexts",
        "",
    ]
    allowed_contexts = policy_payload.get("allowed_contexts", {})
    for setup, contexts in allowed_contexts.items():
        rendered = "; ".join(
            f"{item['market_session']}/{item['session_phase']} (trades {item['trades']}, expectancy {item['expectancy_r']}, pf {item['profit_factor']}, threshold {item['context_threshold']})"
            for item in contexts
        )
        lines.append(f"- `{setup}`: {rendered}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def frontier_backtest_command(args) -> int:
    artifacts_dir = Path(args.artifacts_dir).resolve()
    frontier_policy_path = Path(args.policy_input).resolve() if args.policy_input else artifacts_dir / "manager_policy.json"
    if not _is_frontier_policy(frontier_policy_path):
        return _CACHED.backtest_command(args)

    legacy_policy_path = artifacts_dir / "manager_policy_legacy.json"
    raw_policy_input = legacy_policy_path if legacy_policy_path.exists() else frontier_policy_path
    cache_dir = artifacts_dir / "_frontier_raw_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_args = argparse.Namespace(**vars(args))
    raw_args.policy_input = str(raw_policy_input)
    raw_args.json_output = str(cache_dir / "raw_backtest_summary.json")
    raw_args.markdown_output = str(cache_dir / "raw_backtest_summary.md")
    raw_args.trades_output = str(cache_dir / "raw_backtest_trades.csv.gz")
    if not (
        Path(raw_args.json_output).exists()
        and Path(raw_args.trades_output).exists()
        and Path(raw_args.markdown_output).exists()
    ):
        status = _CACHED.backtest_command(raw_args)
        if status != 0:
            return status

    policy_payload = _frontier_read_json(frontier_policy_path)
    raw_summary_payload = _frontier_read_json(Path(raw_args.json_output))
    policy_payload["raw_source_summary"] = raw_summary_payload.get("summary")
    raw_trades = load_frontier_trade_frame(Path(raw_args.trades_output))
    adjusted_trades = apply_frontier_policy(raw_trades, policy_payload)
    starting_balance = float(policy_payload.get("backtest_config", {}).get("starting_balance", 100000.0))
    summary_payload = build_backtest_summary_payload(
        trades=adjusted_trades,
        policy=policy_payload,
        starting_balance=starting_balance,
        policy_input=str(frontier_policy_path),
    )
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    if args.trades_output:
        trades_output = Path(args.trades_output)
        trades_output.parent.mkdir(parents=True, exist_ok=True)
        adjusted_trades.to_csv(
            trades_output,
            index=False,
            compression="gzip" if str(trades_output).endswith(".gz") else None,
        )
    if args.markdown_output:
        _write_frontier_markdown(summary_payload, policy_payload, Path(args.markdown_output))
    return 0


def train_command(args) -> int:
    _CACHED.set_random_seed(7)
    dataset_path = Path(args.dataset).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    device = _CACHED.torch.device(args.device)

    frame = _CACHED.load_dataset(dataset_path)
    train_config = _CACHED.TrainConfig(
        lookback=args.lookback,
        batch_size=args.batch_size,
        epochs=args.epochs,
        negative_ratio=args.negative_ratio,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
    )
    split_masks = _CACHED.build_split_masks(
        frame=frame,
        train_fraction=train_config.train_fraction,
        val_fraction=train_config.val_fraction,
    )
    train_rows = frame.loc[split_masks["train"] & frame["model_sample_eligible"]].copy()
    scaler_stats = _CACHED.fit_standardization(train_rows, _CACHED.FEATURE_COLUMNS)
    feature_matrix = _CACHED.apply_standardization(frame, scaler_stats, _CACHED.FEATURE_COLUMNS)

    model_reports = {}
    selection_policy = {"labels": [], "thresholds": {}, "calibrators": {}}
    for label_name in _CACHED.SETUP_LABELS:
        label_dir = artifacts_dir / label_name
        model_path = label_dir / "model.pt"
        metrics_path = label_dir / "metrics.json"

        if model_path.exists() and model_path.stat().st_size > 0 and metrics_path.exists():
            report_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        else:
            result = _CACHED.train_single_model(
                frame=frame,
                features=feature_matrix,
                split_masks=split_masks,
                train_config=train_config,
                label_name=label_name,
                device=device,
            )
            label_dir.mkdir(parents=True, exist_ok=True)
            _CACHED.torch.save(
                result["state_dict"],
                model_path,
                _use_new_zipfile_serialization=False,
            )
            report_payload = {
                "label_name": label_name,
                "feature_columns": _CACHED.FEATURE_COLUMNS,
                "history": result["history"],
                "train_metrics": result["train_metrics"],
                "val_metrics": result["val_metrics"],
                "test_metrics": result["test_metrics"],
                "calibrated_test_metrics": result["calibrated_test_metrics"],
                "calibrator": result["calibrator"],
                "selection_threshold": result["selection_threshold"],
                "class_balance": result["class_balance"],
                "train_rows": int(len(result["train_indices"])),
                "val_rows": int(len(result["val_indices"])),
                "test_rows": int(len(result["test_indices"])),
            }
            _CACHED.serialize_json(metrics_path, report_payload)

        model_reports[label_name] = report_payload
        selection_policy["labels"].append(label_name)
        selection_policy["thresholds"][label_name] = report_payload["selection_threshold"]
        selection_policy["calibrators"][label_name] = report_payload["calibrator"]

    _CACHED.serialize_json(
        artifacts_dir / "dataset_schema.json",
        {
            "feature_columns": _CACHED.FEATURE_COLUMNS,
            "context_columns": _CACHED.CONTEXT_COLUMNS,
            "base_columns": _CACHED.BASE_COLUMNS,
            "lookback": train_config.lookback,
            "scaler_stats": scaler_stats,
        },
    )
    _CACHED.serialize_json(
        artifacts_dir / "selection_policy.json",
        {
            "selection": "winner_takes_highest_probability_above_model_threshold",
            "labels": selection_policy["labels"],
            "thresholds": selection_policy["thresholds"],
            "calibrators": selection_policy["calibrators"],
            "model_architecture": {
                "channels": list(train_config.channels),
                "kernel_size": train_config.kernel_size,
                "dropout": train_config.dropout,
                "hidden_dim": train_config.hidden_dim,
            },
            "notes": [
                "Only rows marked model_sample_eligible should be scored.",
                "If news blackouts are enforced by the upstream server, the model layer can assume that control is already active.",
                "The model layer forecasts setup probability. Position sizing and stop placement must still satisfy FundedHive hard limits: 3 percent max loss per trade, 5 percent static daily loss, and 10 percent static total drawdown.",
            ],
        },
    )
    _CACHED.serialize_json(
        artifacts_dir / "training_summary.json",
        {
            "dataset": str(dataset_path),
            "artifacts_dir": str(artifacts_dir),
            "train_config": asdict(train_config),
            "model_reports": model_reports,
        },
    )
    return 0


def main() -> int:
    args = _CACHED.parse_args()
    if args.command == "build-dataset":
        return _CACHED.build_dataset_command(args)
    if args.command == "train":
        return train_command(args)
    if args.command == "score":
        return _CACHED.score_command(args)
    if args.command == "analyze":
        return _CACHED.analyze_command(args)
    if args.command == "backtest":
        return frontier_backtest_command(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
