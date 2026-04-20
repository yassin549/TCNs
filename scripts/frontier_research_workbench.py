import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def challenge_score(report: Dict[str, object]) -> tuple:
    metrics = report.get("challenge_metrics", {})
    performance = report.get("performance", {})
    return (
        float(metrics.get("pass_probability_60", 0.0)),
        float(metrics.get("pass_probability_30", 0.0)),
        float(metrics.get("pass_probability_90", 0.0)),
        -float(metrics.get("median_days_to_pass") or 1e9),
        -float(metrics.get("avg_days_to_pass") or 1e9),
        float(metrics.get("profitable_day_hit_rate_day_10", 0.0)),
        float(metrics.get("profitable_day_hit_rate_day_20", 0.0)),
        -float(metrics.get("longest_negative_day_streak", 1e9)),
        -float(metrics.get("worst_month_return_pct", 0.0)),
        -float(metrics.get("loss_cluster_penalty", 0.0)),
        float(performance.get("expectancy_r", 0.0)),
    )


def run_step(args: list[str], workdir: Path) -> None:
    completed = subprocess.run(args, cwd=workdir, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def ensure_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def enrich_dataset_command(args: argparse.Namespace) -> int:
    run_step(
        [
            PYTHON,
            "-B",
            "scripts/frontier_prop_manager.py",
            "enrich-features",
            "--input",
            args.input,
            "--output",
            args.output,
        ],
        REPO_ROOT,
    )
    return 0


def build_utility_dataset_command(args: argparse.Namespace) -> int:
    command = [
        PYTHON,
        "-B",
        "scripts/frontier_utility_dataset.py",
        "build",
        "--input",
        args.input,
        "--output",
        args.output,
    ]
    if args.reference_trades:
        command.extend(["--reference-trades", args.reference_trades])
    if args.schema_output:
        command.extend(["--schema-output", args.schema_output])
    if args.label_report_output:
        command.extend(["--label-report-output", args.label_report_output])
    if args.max_rows is not None:
        command.extend(["--max-rows", str(args.max_rows)])
    if args.max_trades_per_day is not None:
        command.extend(["--max-trades-per-day", str(args.max_trades_per_day)])
    if args.risk_per_trade_pct is not None:
        command.extend(["--risk-per-trade-pct", str(args.risk_per_trade_pct)])
    if args.account_stage:
        command.extend(["--account-stage", str(args.account_stage)])
    run_step(command, REPO_ROOT)
    return 0


def train_utility_model_command(args: argparse.Namespace) -> int:
    command = [
        PYTHON,
        "-B",
        "scripts/frontier_utility_model.py",
        "train",
        "--dataset",
        args.dataset,
        "--artifacts-dir",
        args.artifacts_dir,
        "--device",
        args.device,
    ]
    if args.epochs is not None:
        command.extend(["--epochs", str(args.epochs)])
    if args.lookback is not None:
        command.extend(["--lookback", str(args.lookback)])
    if args.batch_size is not None:
        command.extend(["--batch-size", str(args.batch_size)])
    if args.max_train_samples is not None:
        command.extend(["--max-train-samples", str(args.max_train_samples)])
    if args.max_eval_samples is not None:
        command.extend(["--max-eval-samples", str(args.max_eval_samples)])
    run_step(command, REPO_ROOT)
    return 0


def score_candidates_command(args: argparse.Namespace) -> int:
    command = [
        PYTHON,
        "-B",
        "scripts/frontier_utility_model.py",
        "score",
        "--dataset",
        args.dataset,
        "--artifacts-dir",
        args.artifacts_dir,
        "--output",
        args.output,
        "--split",
        args.split,
        "--device",
        args.device,
    ]
    if args.analysis_output:
        command.extend(["--analysis-output", args.analysis_output])
    run_step(command, REPO_ROOT)
    return 0


def replay_frontier_command(args: argparse.Namespace) -> int:
    command = [
        PYTHON,
        "-B",
        "scripts/frontier_replay.py",
        "replay",
        "--candidates",
        args.candidates,
        "--artifacts-dir",
        args.artifacts_dir,
        "--split",
        args.split,
        "--starting-balance",
        str(args.starting_balance),
        "--max-trades-per-day",
        str(args.max_trades_per_day),
        "--risk-per-trade-pct",
        str(args.risk_per_trade_pct),
        "--account-stage",
        str(args.account_stage),
        "--min-trade-score",
        str(args.min_trade_score),
        "--bootstrap-simulations",
        str(args.bootstrap_simulations),
        "--bootstrap-seed",
        str(args.bootstrap_seed),
    ]
    if args.dataset:
        command.extend(["--dataset", args.dataset])
    if args.allow_continuation:
        command.append("--allow-continuation")
    run_step(command, REPO_ROOT)
    return 0


def full_utility_cycle_command(args: argparse.Namespace) -> int:
    utility_dataset = Path(args.utility_dataset)
    utility_dataset.parent.mkdir(parents=True, exist_ok=True)
    run_step(
        [
            PYTHON,
            "-B",
            "scripts/frontier_utility_dataset.py",
            "build",
            "--input",
            args.input_dataset,
            "--output",
            str(utility_dataset),
            "--schema-output",
            str(Path(args.artifact_dir) / "dataset_schema.json"),
            "--label-report-output",
            str(Path(args.artifact_dir) / "label_report.json"),
        ]
        + (["--max-rows", str(args.max_rows)] if args.max_rows is not None else [])
        + (["--reference-trades", args.reference_trades] if args.reference_trades else [])
        + (["--account-stage", str(args.account_stage)] if args.account_stage else []),
        REPO_ROOT,
    )

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/frontier_utility_model.py",
            "train",
            "--dataset",
            str(utility_dataset),
            "--artifacts-dir",
            args.artifact_dir,
            "--device",
            args.device,
        ]
        + (["--epochs", str(args.epochs)] if args.epochs is not None else [])
        + (["--max-train-samples", str(args.max_train_samples)] if args.max_train_samples is not None else [])
        + (["--max-eval-samples", str(args.max_eval_samples)] if args.max_eval_samples is not None else []),
        REPO_ROOT,
    )

    candidates_output = Path(args.artifact_dir) / "scored_candidates.csv.gz"
    run_step(
        [
            PYTHON,
            "-B",
            "scripts/frontier_utility_model.py",
            "score",
            "--dataset",
            str(utility_dataset),
            "--artifacts-dir",
            args.artifact_dir,
            "--output",
            str(candidates_output),
            "--analysis-output",
            str(Path(args.artifact_dir) / "analysis_report.json"),
            "--split",
            args.split,
            "--device",
            args.device,
        ],
        REPO_ROOT,
    )

    replay_command = [
        PYTHON,
        "-B",
        "scripts/frontier_replay.py",
        "replay",
        "--candidates",
        str(candidates_output),
        "--artifacts-dir",
        args.artifact_dir,
        "--dataset",
        str(utility_dataset),
        "--split",
        args.split,
        "--max-trades-per-day",
        str(args.max_trades_per_day),
        "--risk-per-trade-pct",
        str(args.risk_per_trade_pct),
        "--account-stage",
        str(args.account_stage),
        "--min-trade-score",
        str(args.min_trade_score),
        "--bootstrap-simulations",
        str(args.bootstrap_simulations),
        "--bootstrap-seed",
        str(args.bootstrap_seed),
    ]
    if args.allow_continuation:
        replay_command.append("--allow-continuation")
    run_step(replay_command, REPO_ROOT)

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/generate_baseline_report.py",
            "--artifact-dir",
            args.artifact_dir,
            "--artifact-name",
            args.artifact_name,
            "--output-md",
            args.output_md,
        ],
        REPO_ROOT,
    )
    return 0


def materialize_frontier_artifact_command(args: argparse.Namespace) -> int:
    base_artifact = Path(args.base_artifact_dir)
    output_artifact = Path(args.output_artifact_dir)
    output_artifact.mkdir(parents=True, exist_ok=True)

    legacy_policy = base_artifact / "manager_policy_legacy.json"
    if not legacy_policy.exists():
        current_policy = base_artifact / "manager_policy.json"
        if current_policy.exists():
            ensure_copy(current_policy, legacy_policy)

    frontier_policy = output_artifact / "manager_policy.json"
    run_step(
        [
            PYTHON,
            "-B",
            "scripts/frontier_prop_manager.py",
            "build-policy",
            "--analysis-report",
            str(base_artifact / "analysis_report.json"),
            "--baseline-report",
            str(base_artifact / "baseline_report.json"),
            "--trades",
            str(base_artifact / "backtest_trades.csv.gz"),
            "--output",
            str(frontier_policy),
        ],
        REPO_ROOT,
    )

    for filename in ["training_summary.json", "analysis_report.json", "dataset_schema.json"]:
        src = base_artifact / filename
        if src.exists():
            ensure_copy(src, output_artifact / filename)

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/specialist_tcn_pipeline.py",
            "backtest",
            "--dataset",
            args.dataset,
            "--artifacts-dir",
            str(base_artifact),
            "--policy-input",
            str(frontier_policy),
            "--split",
            args.split,
            "--json-output",
            str(output_artifact / "backtest_summary.json"),
            "--markdown-output",
            str(output_artifact / "backtest_summary.md"),
            "--trades-output",
            str(output_artifact / "backtest_trades.csv.gz"),
            "--device",
            args.device,
        ],
        REPO_ROOT,
    )

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/generate_baseline_report.py",
            "--artifact-dir",
            str(output_artifact),
            "--artifact-name",
            args.artifact_name,
            "--output-md",
            args.output_md,
        ],
        REPO_ROOT,
    )
    return 0


def compare_reports_command(args: argparse.Namespace) -> int:
    baseline_a = read_json(Path(args.baseline_a))
    baseline_b = read_json(Path(args.baseline_b))

    perf_a = baseline_a["performance"]
    perf_b = baseline_b["performance"]
    challenge_a = baseline_a["challenge"]
    challenge_b = baseline_b["challenge"]
    challenge_metrics_a = baseline_a.get("challenge_metrics", {})
    challenge_metrics_b = baseline_b.get("challenge_metrics", {})
    daily_a = baseline_a["daily"]
    daily_b = baseline_b["daily"]

    lines = [
        f"# {args.title}",
        "",
        f"- A: `{baseline_a['baseline']['artifact_name']}`",
        f"- B: `{baseline_b['baseline']['artifact_name']}`",
        "",
        f"- Acceptance baseline: `{baseline_b['baseline'].get('execution_mode')}` for `{baseline_b['baseline']['artifact_name']}`",
        "",
        "| Metric | A | B | Delta B-A |",
        "| --- | ---: | ---: | ---: |",
        f"| Execution mode | `{baseline_a['baseline'].get('execution_mode')}` | `{baseline_b['baseline'].get('execution_mode')}` | `` |",
        f"| Trades | `{perf_a['trades']}` | `{perf_b['trades']}` | `{perf_b['trades'] - perf_a['trades']}` |",
        f"| Win rate | `{perf_a['win_rate']}` | `{perf_b['win_rate']}` | `{round(perf_b['win_rate'] - perf_a['win_rate'], 6)}` |",
        f"| Expectancy R | `{perf_a['expectancy_r']}` | `{perf_b['expectancy_r']}` | `{round(perf_b['expectancy_r'] - perf_a['expectancy_r'], 6)}` |",
        f"| Return % | `{perf_a['total_return_pct']}` | `{perf_b['total_return_pct']}` | `{round(perf_b['total_return_pct'] - perf_a['total_return_pct'], 4)}` |",
        f"| Max DD % | `{perf_a['max_drawdown_pct']}` | `{perf_b['max_drawdown_pct']}` | `{round(perf_b['max_drawdown_pct'] - perf_a['max_drawdown_pct'], 4)}` |",
        f"| Days to pass | `{challenge_a['actual_days_to_pass']}` | `{challenge_b['actual_days_to_pass']}` | `{challenge_b['actual_days_to_pass'] - challenge_a['actual_days_to_pass'] if challenge_a['actual_days_to_pass'] is not None and challenge_b['actual_days_to_pass'] is not None else 'None'}` |",
        f"| Pass prob 30 | `{challenge_metrics_a.get('pass_probability_30')}` | `{challenge_metrics_b.get('pass_probability_30')}` | `{round(float(challenge_metrics_b.get('pass_probability_30', 0.0)) - float(challenge_metrics_a.get('pass_probability_30', 0.0)), 6)}` |",
        f"| Pass prob 60 | `{challenge_metrics_a.get('pass_probability_60')}` | `{challenge_metrics_b.get('pass_probability_60')}` | `{round(float(challenge_metrics_b.get('pass_probability_60', 0.0)) - float(challenge_metrics_a.get('pass_probability_60', 0.0)), 6)}` |",
        f"| Pass prob 90 | `{challenge_metrics_a.get('pass_probability_90')}` | `{challenge_metrics_b.get('pass_probability_90')}` | `{round(float(challenge_metrics_b.get('pass_probability_90', 0.0)) - float(challenge_metrics_a.get('pass_probability_90', 0.0)), 6)}` |",
        f"| Worst month % | `{challenge_metrics_a.get('worst_month_return_pct')}` | `{challenge_metrics_b.get('worst_month_return_pct')}` | `{round(float(challenge_metrics_b.get('worst_month_return_pct', 0.0)) - float(challenge_metrics_a.get('worst_month_return_pct', 0.0)), 6)}` |",
        f"| Loss cluster penalty | `{challenge_metrics_a.get('loss_cluster_penalty')}` | `{challenge_metrics_b.get('loss_cluster_penalty')}` | `{round(float(challenge_metrics_b.get('loss_cluster_penalty', 0.0)) - float(challenge_metrics_a.get('loss_cluster_penalty', 0.0)), 6)}` |",
        f"| Rolling-start pass rate | `{challenge_a['rolling_start']['pass_rate']}` | `{challenge_b['rolling_start']['pass_rate']}` | `{round(challenge_b['rolling_start']['pass_rate'] - challenge_a['rolling_start']['pass_rate'], 6)}` |",
        f"| Profitable days | `{challenge_a['actual_profitable_days']}` | `{challenge_b['actual_profitable_days']}` | `{challenge_b['actual_profitable_days'] - challenge_a['actual_profitable_days']}` |",
        f"| Positive day rate | `{daily_a['positive_day_rate']}` | `{daily_b['positive_day_rate']}` | `{round(daily_b['positive_day_rate'] - daily_a['positive_day_rate'], 6)}` |",
        "",
    ]
    if args.output_md:
        write_text(Path(args.output_md), "\n".join(lines) + "\n")
    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(
            json.dumps(
                {
                    "a": baseline_a["baseline"]["artifact_name"],
                    "b": baseline_b["baseline"]["artifact_name"],
                    "delta": {
                        "trades": perf_b["trades"] - perf_a["trades"],
                        "win_rate": round(perf_b["win_rate"] - perf_a["win_rate"], 6),
                        "expectancy_r": round(perf_b["expectancy_r"] - perf_a["expectancy_r"], 6),
                        "return_pct": round(perf_b["total_return_pct"] - perf_a["total_return_pct"], 4),
                        "max_drawdown_pct": round(perf_b["max_drawdown_pct"] - perf_a["max_drawdown_pct"], 4),
                        "pass_probability_30": round(float(challenge_metrics_b.get("pass_probability_30", 0.0)) - float(challenge_metrics_a.get("pass_probability_30", 0.0)), 6),
                        "pass_probability_60": round(float(challenge_metrics_b.get("pass_probability_60", 0.0)) - float(challenge_metrics_a.get("pass_probability_60", 0.0)), 6),
                        "pass_probability_90": round(float(challenge_metrics_b.get("pass_probability_90", 0.0)) - float(challenge_metrics_a.get("pass_probability_90", 0.0)), 6),
                        "days_to_pass": None
                        if challenge_a["actual_days_to_pass"] is None or challenge_b["actual_days_to_pass"] is None
                        else challenge_b["actual_days_to_pass"] - challenge_a["actual_days_to_pass"],
                        "rolling_start_pass_rate": round(
                            challenge_b["rolling_start"]["pass_rate"] - challenge_a["rolling_start"]["pass_rate"], 6
                        ),
                        "worst_month_return_pct": round(float(challenge_metrics_b.get("worst_month_return_pct", 0.0)) - float(challenge_metrics_a.get("worst_month_return_pct", 0.0)), 6),
                        "loss_cluster_penalty": round(float(challenge_metrics_b.get("loss_cluster_penalty", 0.0)) - float(challenge_metrics_a.get("loss_cluster_penalty", 0.0)), 6),
                        "profitable_days": challenge_b["actual_profitable_days"] - challenge_a["actual_profitable_days"],
                        "positive_day_rate": round(daily_b["positive_day_rate"] - daily_a["positive_day_rate"], 6),
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    print("\n".join(lines))
    return 0


def benchmark_scoreboard_command(args: argparse.Namespace) -> int:
    rows = []
    for report_path in args.reports:
        report = read_json(Path(report_path))
        metrics = report.get("challenge_metrics", {})
        performance = report.get("performance", {})
        rows.append(
            {
                "artifact_name": report["baseline"]["artifact_name"],
                "execution_mode": report["baseline"].get("execution_mode"),
                "pass_probability_30": metrics.get("pass_probability_30"),
                "pass_probability_60": metrics.get("pass_probability_60"),
                "pass_probability_90": metrics.get("pass_probability_90"),
                "median_days_to_pass": metrics.get("median_days_to_pass"),
                "avg_days_to_pass": metrics.get("avg_days_to_pass"),
                "profitable_day_hit_rate_day_10": metrics.get("profitable_day_hit_rate_day_10"),
                "profitable_day_hit_rate_day_20": metrics.get("profitable_day_hit_rate_day_20"),
                "longest_negative_day_streak": metrics.get("longest_negative_day_streak"),
                "worst_month_return_pct": metrics.get("worst_month_return_pct"),
                "loss_cluster_penalty": metrics.get("loss_cluster_penalty"),
                "expectancy_r": performance.get("expectancy_r"),
                "_score": challenge_score(report),
            }
        )
    ranked = sorted(rows, key=lambda row: row["_score"], reverse=True)
    lines = [
        "# Frontier Benchmark Scoreboard",
        "",
        "| Rank | Artifact | Mode | Pass30 | Pass60 | Pass90 | Median Days | Day10 Hit | Day20 Hit | Worst Month % | Loss Cluster | Expectancy R |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | `{row['artifact_name']}` | `{row['execution_mode']}` | `{row['pass_probability_30']}` | `{row['pass_probability_60']}` | `{row['pass_probability_90']}` | `{row['median_days_to_pass']}` | `{row['profitable_day_hit_rate_day_10']}` | `{row['profitable_day_hit_rate_day_20']}` | `{row['worst_month_return_pct']}` | `{row['loss_cluster_penalty']}` | `{row['expectancy_r']}` |"
        )
    if args.output_md:
        write_text(Path(args.output_md), "\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def full_cycle_command(args: argparse.Namespace) -> int:
    if args.enriched_dataset:
        run_step(
            [
                PYTHON,
                "-B",
                "scripts/frontier_prop_manager.py",
                "enrich-features",
                "--input",
                args.dataset,
                "--output",
                args.enriched_dataset,
            ],
            REPO_ROOT,
        )
        dataset_for_cycle = args.enriched_dataset
    else:
        dataset_for_cycle = args.dataset

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    train_cmd = [
        PYTHON,
        "-B",
        "scripts/specialist_tcn_pipeline.py",
        "train",
        "--dataset",
        dataset_for_cycle,
        "--artifacts-dir",
        str(artifact_dir),
        "--device",
        args.device,
    ]
    if args.epochs is not None:
        train_cmd.extend(["--epochs", str(args.epochs)])
    if args.max_train_samples is not None:
        train_cmd.extend(["--max-train-samples", str(args.max_train_samples)])
    if args.max_eval_samples is not None:
        train_cmd.extend(["--max-eval-samples", str(args.max_eval_samples)])
    run_step(train_cmd, REPO_ROOT)

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/specialist_tcn_pipeline.py",
            "analyze",
            "--dataset",
            dataset_for_cycle,
            "--artifacts-dir",
            str(artifact_dir),
            "--json-output",
            str(artifact_dir / "analysis_report.json"),
            "--markdown-output",
            str(artifact_dir / "analysis_report.md"),
            "--policy-output",
            str(artifact_dir / "manager_policy.json"),
            "--device",
            args.device,
        ],
        REPO_ROOT,
    )

    ensure_copy(artifact_dir / "manager_policy.json", artifact_dir / "manager_policy_legacy.json")
    run_step(
        [
            PYTHON,
            "-B",
            "scripts/specialist_tcn_pipeline.py",
            "backtest",
            "--dataset",
            dataset_for_cycle,
            "--artifacts-dir",
            str(artifact_dir),
            "--policy-input",
            str(artifact_dir / "manager_policy_legacy.json"),
            "--split",
            args.split,
            "--json-output",
            str(artifact_dir / "backtest_summary_legacy.json"),
            "--markdown-output",
            str(artifact_dir / "backtest_summary_legacy.md"),
            "--trades-output",
            str(artifact_dir / "backtest_trades_legacy.csv.gz"),
            "--device",
            args.device,
        ],
        REPO_ROOT,
    )

    shutil.copy2(artifact_dir / "backtest_summary_legacy.json", artifact_dir / "backtest_summary.json")
    shutil.copy2(artifact_dir / "backtest_summary_legacy.md", artifact_dir / "backtest_summary.md")
    shutil.copy2(artifact_dir / "backtest_trades_legacy.csv.gz", artifact_dir / "backtest_trades.csv.gz")

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/generate_baseline_report.py",
            "--artifact-dir",
            str(artifact_dir),
            "--artifact-name",
            args.artifact_name,
            "--output-md",
            args.legacy_output_md,
        ],
        REPO_ROOT,
    )

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/frontier_prop_manager.py",
            "build-policy",
            "--analysis-report",
            str(artifact_dir / "analysis_report.json"),
            "--baseline-report",
            str(artifact_dir / "baseline_report.json"),
            "--trades",
            str(artifact_dir / "backtest_trades_legacy.csv.gz"),
            "--output",
            str(artifact_dir / "manager_policy.json"),
        ],
        REPO_ROOT,
    )

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/specialist_tcn_pipeline.py",
            "backtest",
            "--dataset",
            dataset_for_cycle,
            "--artifacts-dir",
            str(artifact_dir),
            "--policy-input",
            str(artifact_dir / "manager_policy.json"),
            "--split",
            args.split,
            "--json-output",
            str(artifact_dir / "backtest_summary.json"),
            "--markdown-output",
            str(artifact_dir / "backtest_summary.md"),
            "--trades-output",
            str(artifact_dir / "backtest_trades.csv.gz"),
            "--device",
            args.device,
        ],
        REPO_ROOT,
    )

    run_step(
        [
            PYTHON,
            "-B",
            "scripts/generate_baseline_report.py",
            "--artifact-dir",
            str(artifact_dir),
            "--artifact-name",
            args.artifact_name,
            "--output-md",
            args.output_md,
        ],
        REPO_ROOT,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Frontier research workbench.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enrich = subparsers.add_parser("enrich-dataset", help="Create a regime-enriched feature dataset.")
    enrich.add_argument("--input", required=True)
    enrich.add_argument("--output", required=True)
    enrich.set_defaults(func=enrich_dataset_command)

    utility = subparsers.add_parser("build-utility-dataset", help="Create a utility-enriched dataset export.")
    utility.add_argument("--input", required=True)
    utility.add_argument("--output", required=True)
    utility.add_argument("--reference-trades")
    utility.add_argument("--schema-output")
    utility.add_argument("--label-report-output")
    utility.add_argument("--max-rows", type=int, default=0)
    utility.add_argument("--max-trades-per-day", type=int)
    utility.add_argument("--risk-per-trade-pct", type=float)
    utility.add_argument("--account-stage", choices=["challenge", "funded"], default="challenge")
    utility.set_defaults(func=build_utility_dataset_command)

    train_utility = subparsers.add_parser("train-utility-model", help="Train the frontier utility model.")
    train_utility.add_argument("--dataset", required=True)
    train_utility.add_argument("--artifacts-dir", required=True)
    train_utility.add_argument("--device", default="cpu")
    train_utility.add_argument("--epochs", type=int)
    train_utility.add_argument("--lookback", type=int)
    train_utility.add_argument("--batch-size", type=int)
    train_utility.add_argument("--max-train-samples", type=int)
    train_utility.add_argument("--max-eval-samples", type=int)
    train_utility.set_defaults(func=train_utility_model_command)

    score = subparsers.add_parser("score-candidates", help="Score replay candidates from the utility model.")
    score.add_argument("--dataset", required=True)
    score.add_argument("--artifacts-dir", required=True)
    score.add_argument("--output", required=True)
    score.add_argument("--analysis-output")
    score.add_argument("--split", default="test")
    score.add_argument("--device", default="cpu")
    score.set_defaults(func=score_candidates_command)

    replay = subparsers.add_parser("replay-frontier", help="Run full integrated replay on scored candidates.")
    replay.add_argument("--candidates", required=True)
    replay.add_argument("--artifacts-dir", required=True)
    replay.add_argument("--dataset")
    replay.add_argument("--split", default="test")
    replay.add_argument("--starting-balance", type=float, default=100000.0)
    replay.add_argument("--max-trades-per-day", type=int, default=3)
    replay.add_argument("--risk-per-trade-pct", type=float, default=0.25)
    replay.add_argument("--account-stage", choices=["challenge", "funded"], default="challenge")
    replay.add_argument("--min-trade-score", type=float, default=0.0)
    replay.add_argument("--allow-continuation", action="store_true")
    replay.add_argument("--bootstrap-simulations", type=int, default=500)
    replay.add_argument("--bootstrap-seed", type=int, default=7)
    replay.set_defaults(func=replay_frontier_command)

    materialize = subparsers.add_parser("materialize-frontier-artifact", help="Create a frontier-managed artifact from an existing trained artifact.")
    materialize.add_argument("--base-artifact-dir", required=True)
    materialize.add_argument("--output-artifact-dir", required=True)
    materialize.add_argument("--dataset", required=True)
    materialize.add_argument("--artifact-name", required=True)
    materialize.add_argument("--output-md", required=True)
    materialize.add_argument("--split", default="test")
    materialize.add_argument("--device", default="cpu")
    materialize.set_defaults(func=materialize_frontier_artifact_command)

    compare = subparsers.add_parser("compare-reports", help="Compare two baseline reports.")
    compare.add_argument("--baseline-a", required=True)
    compare.add_argument("--baseline-b", required=True)
    compare.add_argument("--title", default="Frontier Comparison")
    compare.add_argument("--output-md")
    compare.add_argument("--output-json")
    compare.set_defaults(func=compare_reports_command)

    scoreboard = subparsers.add_parser("benchmark-scoreboard", help="Rank baseline reports by challenge utility first.")
    scoreboard.add_argument("--reports", nargs="+", required=True)
    scoreboard.add_argument("--output-md")
    scoreboard.set_defaults(func=benchmark_scoreboard_command)

    cycle = subparsers.add_parser("full-cycle", help="Run an end-to-end train/analyze/frontier-backtest cycle.")
    cycle.add_argument("--dataset", required=True)
    cycle.add_argument("--artifact-dir", required=True)
    cycle.add_argument("--artifact-name", required=True)
    cycle.add_argument("--output-md", required=True)
    cycle.add_argument("--legacy-output-md", required=True)
    cycle.add_argument("--split", default="test")
    cycle.add_argument("--device", default="cpu")
    cycle.add_argument("--enriched-dataset")
    cycle.add_argument("--epochs", type=int)
    cycle.add_argument("--max-train-samples", type=int)
    cycle.add_argument("--max-eval-samples", type=int)
    cycle.set_defaults(func=full_cycle_command)

    utility_cycle = subparsers.add_parser("full-utility-cycle", help="Run the end-to-end utility-model frontier cycle.")
    utility_cycle.add_argument("--input-dataset", required=True)
    utility_cycle.add_argument("--utility-dataset", required=True)
    utility_cycle.add_argument("--artifact-dir", required=True)
    utility_cycle.add_argument("--artifact-name", required=True)
    utility_cycle.add_argument("--output-md", required=True)
    utility_cycle.add_argument("--reference-trades")
    utility_cycle.add_argument("--split", default="test")
    utility_cycle.add_argument("--device", default="cpu")
    utility_cycle.add_argument("--epochs", type=int)
    utility_cycle.add_argument("--max-rows", type=int)
    utility_cycle.add_argument("--max-train-samples", type=int)
    utility_cycle.add_argument("--max-eval-samples", type=int)
    utility_cycle.add_argument("--max-trades-per-day", type=int, default=3)
    utility_cycle.add_argument("--risk-per-trade-pct", type=float, default=0.25)
    utility_cycle.add_argument("--account-stage", choices=["challenge", "funded"], default="challenge")
    utility_cycle.add_argument("--min-trade-score", type=float, default=0.0)
    utility_cycle.add_argument("--allow-continuation", action="store_true")
    utility_cycle.add_argument("--bootstrap-simulations", type=int, default=500)
    utility_cycle.add_argument("--bootstrap-seed", type=int, default=7)
    utility_cycle.set_defaults(func=full_utility_cycle_command)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
