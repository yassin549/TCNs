# Next Frontier Work Package

Date: `2026-04-16`

Objective: make the next research cycle executable as a repeatable workflow instead of a collection of ad hoc commands.

This work package focuses on two concrete deliverables:

1. A regime-feature research path for the next training cycle.
2. A reproducible frontier artifact materialization and comparison workflow.

## Scope

### Track 1. Regime-feature retraining path

Goal:

- make it easy to create an enriched dataset and use it for the next train/analyze/backtest cycle

Core command:

```powershell
python -B scripts\frontier_research_workbench.py enrich-dataset `
  --input data\features\us100_specialist_tcn_dataset_session_refined_rerun_20260415.csv.gz `
  --output data\features\us100_specialist_tcn_dataset_session_refined_rerun_20260415_regime.csv.gz
```

### Track 2. Frontier artifact materialization

Goal:

- take an existing trained artifact and generate a frontier-managed artifact with:
  - frontier policy
  - frontier backtest outputs
  - reproducible baseline report

Core command:

```powershell
python -B scripts\frontier_research_workbench.py materialize-frontier-artifact `
  --base-artifact-dir artifacts\specialist_tcns\us100_session_refined_rerun_20260415 `
  --output-artifact-dir artifacts\specialist_tcns\us100_session_refined_rerun_20260415_frontier_pipeline `
  --dataset data\features\us100_specialist_tcn_dataset_session_refined_rerun_20260415.csv.gz `
  --artifact-name specialist_tcns/us100_session_refined_rerun_20260415_frontier_pipeline `
  --output-md docs\us100_session_refined_rerun_20260415_frontier_pipeline.md
```

### Track 3. Full-cycle orchestration

Goal:

- support the next actual model cycle from one command:
  - optional regime enrichment
  - train
  - analyze
  - legacy backtest baseline
  - frontier policy build
  - frontier backtest
  - baseline report generation

Core command surface:

```powershell
python -B scripts\frontier_research_workbench.py full-cycle --help
```

## Implemented Tooling

New script:

- [scripts/frontier_research_workbench.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_research_workbench.py:1)

Implemented commands:

- `enrich-dataset`
- `materialize-frontier-artifact`
- `compare-reports`
- `full-cycle`

## Why This Work Package Matters

The repo now has three layers:

1. signal training
2. frontier policy logic
3. reproducible frontier research workflow

That third layer is what unlocks the next cycle. Without it, regime-feature retraining and frontier policy evaluation remain too manual and too error-prone.

## Immediate Next Usage

1. Build the regime-enriched dataset.
2. Run a smoke `full-cycle` on a capped sample to validate the next training loop.
3. After the smoke cycle passes, run the full training cycle on the enriched dataset.
4. Compare the new frontier artifact against:
   - the old latest baseline
   - the current frontier-pipeline baseline
