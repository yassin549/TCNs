# Frontier Pipeline Integration Plan

Date: `2026-04-16`

Objective: move the frontier manager from a standalone post-processing tool into the actual `specialist_tcn_pipeline.py backtest` path so the main pipeline can emit frontier-managed backtest outputs directly.

## Goals

1. Detect when `manager_policy.json` is a frontier policy.
2. Reuse the cached bytecode backtest only as a raw trade-path generator.
3. Apply the frontier manager in source after the raw trade path is produced.
4. Write final frontier-managed outputs to the user-requested:
   - JSON summary
   - Markdown summary
   - trade log
5. Avoid Windows temp-directory cleanup failures.
6. Preserve compatibility with non-frontier policies.

## Implementation Steps

### Step 1. Add frontier-policy detection to the wrapper

File:

- [scripts/specialist_tcn_pipeline.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/specialist_tcn_pipeline.py:1)

Change:

- inspect `policy_input`
- if `selection = frontier_contextual_abstention_manager`, route `backtest` through wrapper-managed frontier orchestration
- otherwise keep the old cached-bytecode backtest path

### Step 2. Use the cached module only to generate the raw trade path

Change:

- when a frontier policy is active:
  - run the cached backtest with `manager_policy_legacy.json` when available
  - store raw outputs in an artifact-local cache

Reason:

- the cached bytecode path does not understand the new frontier manager semantics
- but it still provides the raw trade candidates the frontier layer can filter and resize

### Step 3. Apply the frontier manager in source

Change:

- import and call:
  - `load_trade_frame`
  - `apply_frontier_policy`
  - `build_backtest_summary_payload`
from [frontier_prop_manager.py](C:/Users/khoua/OneDrive/Desktop/TCNs/scripts/frontier_prop_manager.py:1)

### Step 4. Write frontier-managed outputs back to normal backtest targets

Change:

- emit:
  - `backtest_summary*.json`
  - `backtest_summary*.md`
  - `backtest_trades*.csv.gz`
using the same output arguments the main pipeline already accepts

### Step 5. Replace temp directories with deterministic cache folders

Change:

- use `artifacts/.../_frontier_raw_cache/`
- reuse cached raw outputs on reruns

Reason:

- avoids Windows cleanup failures observed with `TemporaryDirectory`
- makes reruns much faster after the first full raw backtest

### Step 6. Generate a dedicated frontier-pipeline artifact and report

Artifact:

- `artifacts/specialist_tcns/us100_session_refined_rerun_20260415_frontier_pipeline`

Report:

- `docs/us100_session_refined_rerun_20260415_frontier_pipeline.md`

## Acceptance Criteria

- `python scripts/specialist_tcn_pipeline.py backtest ...` exits successfully with the frontier policy active
- the resulting outputs reflect frontier-managed metrics rather than legacy gated-MoE metrics
- reruns no longer fail due to temp-directory cleanup on Windows
- the integrated frontier pipeline matches the standalone frontier-manager estimate on the latest artifact
