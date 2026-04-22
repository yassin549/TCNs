from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib import error, parse, request

import numpy as np
import pandas as pd
import torch

from frontier_account_state import AccountStateConfig
from frontier_allocator import AllocationConfig
from frontier_execution import ContractSpec, ExecutionPolicy, build_order_plan as build_shared_order_plan
from frontier_replay import _stage_risk_pct
from live_config_validation import raise_for_invalid_contracts
from paper_execution import append_open_position, build_paper_summary, load_paper_state, save_paper_state, sync_paper_positions
from portfolio_allocator import PortfolioConstraints, allocate_portfolio
from snapshot_updater import SnapshotUpdateResult, SnapshotUpdaterConfig, update_snapshot
from frontier_utility_model import (
    ACCOUNT_COLUMNS,
    BASE_COLUMNS,
    MARKET_FEATURE_COLUMNS,
    FrontierUtilityModel,
    TrainConfig,
    _challenge_score_from_outputs,
    _funded_score_from_outputs,
    normalize_frontier_score_array,
)


DEMO_BASE_URL = "https://demo-api-capital.backend-capital.com"
SETUPS = ["long_reversal", "long_continuation", "short_reversal", "short_continuation"]
MODEL_CACHE: Dict[str, "ModelBundle"] = {}


@dataclass
class CapitalCredentials:
    api_key: str
    identifier: str
    password: str
    base_url: str = DEMO_BASE_URL


@dataclass
class CapitalSession:
    cst: str
    security_token: str
    current_account_id: str
    account_balance: float
    currency: str


@dataclass
class InstrumentLiveConfig:
    instrument_id: str
    epic: str
    dataset_path: Path
    artifacts_dir: Path
    point_value: float
    min_size: float
    size_step: float
    stop_atr_multiple: float
    target_atr_multiple: float
    max_positions_per_epic: int
    min_frontier_score: float
    log_dir: Path


@dataclass
class ModelBundle:
    config: TrainConfig
    model: FrontierUtilityModel
    checkpoint: Dict[str, object]
    frontier_stats: Dict[str, float]


@dataclass
class ScoredInstrument:
    live_config: InstrumentLiveConfig
    candidate: Dict[str, object]
    runtime_state_path: Path
    runtime_state: Dict[str, object]
    market_rules: Dict[str, object]
    market_details: Dict[str, object]
    snapshot_status: Optional[Dict[str, object]] = None
    precheck_hold_reason: Optional[str] = None
    precheck_extra: Optional[Dict[str, object]] = None


def _read_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    out: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _get_env(name: str, env_map: Dict[str, str], default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is not None and value != "":
        return value
    value = env_map.get(name)
    if value is not None and value != "":
        return value
    return default


def _require_env(name: str, env_map: Dict[str, str]) -> str:
    value = _get_env(name, env_map)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _require_float(value: Optional[str], field_name: str, instrument_id: str) -> float:
    if value is None or value == "":
        raise ValueError(f"Missing required {field_name} for instrument {instrument_id}.")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {field_name} on {instrument_id}: {value}") from exc
    if not np.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{field_name} must be > 0 for instrument {instrument_id}.")
    return float(parsed)


def _round_to_step(value: float, step: float, minimum: float) -> float:
    if step <= 0.0:
        return max(value, minimum)
    units = math.floor(max(value, minimum) / step)
    rounded = units * step
    if rounded < minimum:
        rounded = minimum
    return round(float(rounded), 10)


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_instrument_id(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.strip().upper())


def _instrument_env_or_default(
    env_map: Dict[str, str],
    instrument_key: str,
    specific_name: str,
    generic_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    value = _get_env(f"{specific_name}_{instrument_key}", env_map)
    if value is not None:
        return value
    return _get_env(generic_name, env_map, default)


def _instrument_env_only(
    env_map: Dict[str, str],
    instrument_key: str,
    specific_name: str,
) -> Optional[str]:
    return _get_env(f"{specific_name}_{instrument_key}", env_map)


def _resolve_path(value: Optional[str]) -> Optional[Path]:
    if value is None or value == "":
        return None
    return Path(value).resolve()


class CapitalComClient:
    def __init__(self, credentials: CapitalCredentials):
        self.credentials = credentials
        self.session: Optional[CapitalSession] = None

    def _headers(self, include_auth: bool = True) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-CAP-API-KEY": self.credentials.api_key,
        }
        if include_auth:
            if self.session is None:
                raise RuntimeError("Capital session has not been created.")
            headers["CST"] = self.session.cst
            headers["X-SECURITY-TOKEN"] = self.session.security_token
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, object]] = None,
        include_auth: bool = True,
        retry_on_auth_error: bool = True,
    ) -> Tuple[Dict[str, object], Dict[str, str]]:
        url = f"{self.credentials.base_url.rstrip('/')}/api/v1{path}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, data=data, method=method, headers=self._headers(include_auth=include_auth))
        try:
            with request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                parsed = json.loads(body) if body else {}
                headers = {key: value for key, value in response.headers.items()}
                return parsed, headers
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            if include_auth and retry_on_auth_error and exc.code in (401, 403):
                self.create_session()
                return self._request(
                    method=method,
                    path=path,
                    payload=payload,
                    include_auth=include_auth,
                    retry_on_auth_error=False,
                )
            raise RuntimeError(f"Capital API error {exc.code} for {path}: {message}") from exc

    def create_session(self) -> CapitalSession:
        payload = {
            "identifier": self.credentials.identifier,
            "password": self.credentials.password,
        }
        body, headers = self._request("POST", "/session", payload=payload, include_auth=False)
        cst = headers.get("CST")
        security_token = headers.get("X-SECURITY-TOKEN")
        if not cst or not security_token:
            raise RuntimeError("Capital session response did not include CST / X-SECURITY-TOKEN headers.")
        session = CapitalSession(
            cst=cst,
            security_token=security_token,
            current_account_id=str(body.get("currentAccountId", "")),
            account_balance=float(body.get("accountInfo", {}).get("balance", 0.0)),
            currency=str(body.get("currencyIsoCode", "")),
        )
        self.session = session
        return session

    def list_positions(self) -> Dict[str, object]:
        body, _ = self._request("GET", "/positions")
        return body

    def get_market_details(self, epic: str) -> Dict[str, object]:
        try:
            body, _ = self._request("GET", f"/markets/{parse.quote(epic, safe='')}")
            if body:
                return dict(body)
        except Exception:
            pass
        body, _ = self._request("GET", f"/markets?epics={parse.quote(epic, safe='')}")
        markets = body.get("markets", [])
        if markets:
            return dict(markets[0])
        fallback_body, _ = self._request("GET", f"/markets?searchTerm={parse.quote(epic, safe='')}")
        fallback_markets = fallback_body.get("markets", [])
        for market in fallback_markets:
            market_epic = str(market.get("epic", "")).upper()
            market_symbol = str(market.get("symbol", "")).upper()
            if market_epic == epic.upper() or market_symbol == epic.upper():
                return dict(market)
        raise RuntimeError(f"Capital market lookup returned no market details for epic {epic}.")

    def get_historical_prices(
        self,
        epic: str,
        resolution: str = "MINUTE",
        max_rows: int = 10,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
    ) -> Dict[str, object]:
        query = [("resolution", resolution), ("max", str(int(max_rows)))]
        if from_time:
            query.append(("from", from_time))
        if to_time:
            query.append(("to", to_time))
        encoded = parse.urlencode(query)
        body, _ = self._request("GET", f"/prices/{parse.quote(epic, safe='')}?{encoded}")
        return body

    def place_position(
        self,
        epic: str,
        direction: str,
        size: float,
        stop_distance: float,
        profit_distance: float,
    ) -> Dict[str, object]:
        payload = {
            "epic": epic,
            "direction": direction,
            "size": size,
            "guaranteedStop": False,
            "stopDistance": stop_distance,
            "profitDistance": profit_distance,
        }
        body, _ = self._request("POST", "/positions", payload=payload)
        return body

    def confirm(self, deal_reference: str) -> Dict[str, object]:
        body, _ = self._request("GET", f"/confirms/{deal_reference}")
        return body


def _validate_instrument_configs(configs: List[InstrumentLiveConfig]) -> None:
    dataset_paths: Dict[str, str] = {}
    for config in configs:
        path_key = str(config.dataset_path)
        if path_key in dataset_paths:
            raise ValueError(
                f"Duplicate dataset path detected for {config.instrument_id} and {dataset_paths[path_key]}: "
                f"{config.dataset_path}. Each instrument needs its own live feature snapshot."
            )
        dataset_paths[path_key] = config.instrument_id


def _load_instrument_configs(args: argparse.Namespace, env_map: Dict[str, str]) -> Tuple[List[InstrumentLiveConfig], Path]:
    configured = args.instruments or _get_env("CAPITAL_INSTRUMENTS", env_map)
    if configured:
        instrument_ids = [_sanitize_instrument_id(item) for item in configured.split(",") if item.strip()]
    else:
        fallback_epic = args.epic or _get_env("CAPITAL_EPIC", env_map)
        if not fallback_epic:
            raise ValueError(
                "Missing instrument configuration. Pass --instruments or set CAPITAL_INSTRUMENTS, "
                "or provide --epic / CAPITAL_EPIC for single-instrument mode."
            )
        instrument_ids = [_sanitize_instrument_id(fallback_epic)]

    base_log_dir = Path(args.log_dir or _get_env("CAPITAL_LOG_DIR", env_map, "artifacts/live_capital")).resolve()
    configs: List[InstrumentLiveConfig] = []
    for instrument_id in instrument_ids:
        dataset_override = args.dataset
        artifacts_override = args.artifacts_dir
        epic_override = args.epic if len(instrument_ids) == 1 else None
        point_value_override = args.point_value
        min_size_override = args.min_size
        size_step_override = args.size_step
        stop_atr_override = args.stop_atr_multiple
        target_atr_override = args.target_atr_multiple
        max_positions_override = args.max_positions_per_epic
        min_frontier_score_override = args.min_frontier_score

        epic = epic_override or _instrument_env_only(env_map, instrument_id, "CAPITAL_EPIC")
        if not epic:
            epic = instrument_id if len(instrument_ids) > 1 else _get_env("CAPITAL_EPIC", env_map)
        if not epic:
            raise ValueError(f"Missing epic for instrument {instrument_id}. Set CAPITAL_EPIC_{instrument_id}.")
        dataset_path = _resolve_path(
            dataset_override or _instrument_env_or_default(env_map, instrument_id, "CAPITAL_DATASET", "CAPITAL_DATASET")
        )
        if dataset_path is None:
            raise ValueError(f"Missing dataset for instrument {instrument_id}. Set CAPITAL_DATASET_{instrument_id}.")
        artifacts_dir = _resolve_path(
            artifacts_override or _instrument_env_or_default(env_map, instrument_id, "CAPITAL_ARTIFACTS_DIR", "CAPITAL_ARTIFACTS_DIR")
        )
        if artifacts_dir is None:
            raise ValueError(
                f"Missing artifacts directory for instrument {instrument_id}. "
                f"Set CAPITAL_ARTIFACTS_DIR_{instrument_id}."
            )
        configs.append(
            InstrumentLiveConfig(
                instrument_id=instrument_id,
                epic=epic,
                dataset_path=dataset_path,
                artifacts_dir=artifacts_dir,
                point_value=float(point_value_override) if point_value_override is not None else _require_float(
                    _instrument_env_or_default(env_map, instrument_id, "CAPITAL_POINT_VALUE", "CAPITAL_POINT_VALUE"),
                    "point_value",
                    instrument_id,
                ),
                min_size=float(min_size_override) if min_size_override is not None else _require_float(
                    _instrument_env_or_default(env_map, instrument_id, "CAPITAL_MIN_SIZE", "CAPITAL_MIN_SIZE"),
                    "min_size",
                    instrument_id,
                ),
                size_step=float(size_step_override) if size_step_override is not None else _require_float(
                    _instrument_env_or_default(env_map, instrument_id, "CAPITAL_SIZE_STEP", "CAPITAL_SIZE_STEP"),
                    "size_step",
                    instrument_id,
                ),
                stop_atr_multiple=float(
                    stop_atr_override
                    or _instrument_env_or_default(env_map, instrument_id, "CAPITAL_STOP_ATR_MULTIPLE", "CAPITAL_STOP_ATR_MULTIPLE", "0.75")
                ),
                target_atr_multiple=float(
                    target_atr_override
                    or _instrument_env_or_default(env_map, instrument_id, "CAPITAL_TARGET_ATR_MULTIPLE", "CAPITAL_TARGET_ATR_MULTIPLE", "1.25")
                ),
                max_positions_per_epic=int(
                    max_positions_override
                    or _instrument_env_or_default(
                        env_map,
                        instrument_id,
                        "CAPITAL_MAX_POSITIONS_PER_EPIC",
                        "CAPITAL_MAX_POSITIONS_PER_EPIC",
                        "1",
                    )
                ),
                min_frontier_score=float(
                    min_frontier_score_override
                    if min_frontier_score_override is not None
                    else _instrument_env_or_default(
                        env_map,
                        instrument_id,
                        "CAPITAL_MIN_FRONTIER_SCORE",
                        "CAPITAL_MIN_FRONTIER_SCORE",
                        "0.0",
                    )
                ),
                log_dir=(base_log_dir / instrument_id.lower()).resolve(),
            )
        )
    _validate_instrument_configs(configs)
    return configs, base_log_dir


def _load_credentials(env_map: Dict[str, str]) -> CapitalCredentials:
    return CapitalCredentials(
        api_key=_require_env("CAPITAL_API_KEY", env_map),
        identifier=_require_env("CAPITAL_IDENTIFIER", env_map),
        password=_require_env("CAPITAL_PASSWORD", env_map),
        base_url=_get_env("CAPITAL_BASE_URL", env_map, DEMO_BASE_URL) or DEMO_BASE_URL,
    )


def _compression_for_path(path: Path) -> Optional[str]:
    return "gzip" if str(path).endswith(".gz") else None


def _load_live_snapshot(path: Path) -> pd.DataFrame:
    compression = _compression_for_path(path)
    header = pd.read_csv(path, compression=compression, nrows=0)
    available_columns = list(header.columns)
    required = set(BASE_COLUMNS + MARKET_FEATURE_COLUMNS + ["model_sample_eligible"])
    missing = sorted(required - set(available_columns))
    if missing:
        raise ValueError(f"Live snapshot is missing required columns: {missing}")
    selected = [column for column in list(dict.fromkeys(BASE_COLUMNS + MARKET_FEATURE_COLUMNS + ACCOUNT_COLUMNS + ["account_stage", "model_sample_eligible"])) if column in available_columns]
    frame = pd.read_csv(path, compression=compression, usecols=selected)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["session_date_utc"] = pd.to_datetime(frame["session_date_utc"]).dt.date
    for column in frame.columns:
        if column in {"timestamp", "session_date_utc", "account_stage"}:
            continue
        if column == "model_sample_eligible":
            frame[column] = frame[column].fillna(0).astype(bool)
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values(["timestamp"]).reset_index(drop=True)


def _get_model_bundle(artifacts_dir: Path) -> ModelBundle:
    cache_key = str(artifacts_dir.resolve())
    bundle = MODEL_CACHE.get(cache_key)
    if bundle is not None:
        return bundle
    checkpoint = torch.load(artifacts_dir / "model.pt", map_location="cpu")
    config = TrainConfig(**checkpoint["train_config"])
    model = FrontierUtilityModel(len(MARKET_FEATURE_COLUMNS), len(ACCOUNT_COLUMNS), config)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    bundle = ModelBundle(
        config=config,
        model=model,
        checkpoint=checkpoint,
        frontier_stats=checkpoint.get("frontier_score_stats", {"mean": 0.0, "std": 1.0}),
    )
    MODEL_CACHE[cache_key] = bundle
    return bundle


def _standardize_market_frame(frame: pd.DataFrame, bundle: ModelBundle) -> np.ndarray:
    standardization = bundle.checkpoint["standardization"]
    market_means = pd.Series(standardization["market_means"])
    market_stds = pd.Series(standardization["market_stds"]).replace(0.0, 1.0)
    market = frame[MARKET_FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    market = ((market.fillna(market_means) - market_means) / market_stds).fillna(0.0)
    return market.to_numpy(np.float32)


def _account_row_from_state(live_account_state: Dict[str, object]) -> pd.Series:
    stage = str(live_account_state.get("account_stage", "challenge"))
    payload = {
        "account_stage_code": 1.0 if stage == "funded" else 0.0,
        "account_passed_challenge": float(live_account_state.get("account_passed_challenge", 0.0)),
        "is_challenge_stage": 1.0 if stage != "funded" else 0.0,
        "is_funded_stage": 1.0 if stage == "funded" else 0.0,
        "account_balance": float(live_account_state.get("account_balance", 0.0)),
        "account_return_pct_to_date": float(live_account_state.get("account_return_pct_to_date", 0.0)),
        "account_drawdown_pct": float(live_account_state.get("account_drawdown_pct", 0.0)),
        "account_distance_to_target_pct": float(live_account_state.get("account_distance_to_target_pct", 0.0)),
        "account_profitable_days_so_far": float(live_account_state.get("account_profitable_days_so_far", 0.0)),
        "account_profitable_days_remaining": float(live_account_state.get("account_profitable_days_remaining", 0.0)),
        "account_days_elapsed": float(live_account_state.get("account_days_elapsed", 0.0)),
        "day_pnl_pct_so_far": float(live_account_state.get("day_pnl_pct_so_far", 0.0)),
        "day_loss_budget_remaining_pct": float(live_account_state.get("day_loss_budget_remaining_pct", 5.0)),
        "total_drawdown_budget_remaining_pct": float(live_account_state.get("total_drawdown_budget_remaining_pct", 10.0)),
        "trades_taken_today": float(live_account_state.get("trades_taken_today", 0.0)),
        "trade_slots_remaining_today": float(live_account_state.get("trade_slots_remaining_today", 0.0)),
        "last_trade_pnl_r": float(live_account_state.get("last_trade_pnl_r", 0.0)),
        "win_streak": float(live_account_state.get("win_streak", 0.0)),
        "loss_streak": float(live_account_state.get("loss_streak", 0.0)),
    }
    return pd.Series(payload, index=ACCOUNT_COLUMNS, dtype=np.float32)


def _standardize_account_row(account_row: pd.Series, bundle: ModelBundle) -> np.ndarray:
    standardization = bundle.checkpoint["standardization"]
    account_means = pd.Series(standardization["account_means"])
    account_stds = pd.Series(standardization["account_stds"]).replace(0.0, 1.0)
    aligned = account_row.reindex(ACCOUNT_COLUMNS).replace([np.inf, -np.inf], np.nan)
    aligned = ((aligned.fillna(account_means) - account_means) / account_stds).fillna(0.0)
    return aligned.to_numpy(np.float32)


def _fallback_account_state_from_frame(frame: pd.DataFrame, latest_idx: int) -> Dict[str, object]:
    latest = frame.iloc[latest_idx]
    stage = str(latest.get("account_stage", "challenge"))
    return {
        "account_stage": stage,
        "account_passed_challenge": float(latest.get("account_passed_challenge", 1.0 if stage == "funded" else 0.0)),
        "account_balance": float(latest.get("account_balance", 100000.0)),
        "account_return_pct_to_date": float(latest.get("account_return_pct_to_date", 0.0)),
        "account_drawdown_pct": float(latest.get("account_drawdown_pct", 0.0)),
        "account_distance_to_target_pct": float(latest.get("account_distance_to_target_pct", 10.0)),
        "account_profitable_days_so_far": float(latest.get("account_profitable_days_so_far", 0.0)),
        "account_profitable_days_remaining": float(latest.get("account_profitable_days_remaining", 3.0)),
        "account_days_elapsed": float(latest.get("account_days_elapsed", 0.0)),
        "day_pnl_pct_so_far": float(latest.get("day_pnl_pct_so_far", 0.0)),
        "day_loss_budget_remaining_pct": float(latest.get("day_loss_budget_remaining_pct", 5.0)),
        "total_drawdown_budget_remaining_pct": float(latest.get("total_drawdown_budget_remaining_pct", 10.0)),
        "trades_taken_today": float(latest.get("trades_taken_today", 0.0)),
        "trade_slots_remaining_today": float(latest.get("trade_slots_remaining_today", 2.0)),
        "last_trade_pnl_r": float(latest.get("last_trade_pnl_r", 0.0)),
        "win_streak": float(latest.get("win_streak", 0.0)),
        "loss_streak": float(latest.get("loss_streak", 0.0)),
        "rolling_10_day_return_pct": float(latest.get("rolling_10_day_return_pct", 0.0)),
        "rolling_20_day_return_pct": float(latest.get("rolling_20_day_return_pct", 0.0)),
        "rolling_loss_cluster_penalty": float(latest.get("rolling_loss_cluster_penalty", 0.0)),
        "current_month_return_pct": float(latest.get("current_month_return_pct", 0.0)),
    }


def score_latest_candidate(
    dataset_path: Path,
    artifacts_dir: Path,
    live_account_state: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    bundle = _get_model_bundle(artifacts_dir)
    frame = _load_live_snapshot(dataset_path)
    if len(frame) < bundle.config.lookback:
        raise ValueError(f"Live dataset needs at least {bundle.config.lookback} rows; got {len(frame)}.")
    eligible = frame[frame["model_sample_eligible"]].copy()
    if eligible.empty:
        raise ValueError("No eligible live sample found in dataset.")
    latest_idx = int(eligible.index[-1])
    if int(frame.iloc[latest_idx]["bar_index_in_segment"]) < bundle.config.lookback - 1:
        raise ValueError("Latest eligible sample does not have enough same-segment lookback.")
    start_idx = latest_idx - bundle.config.lookback + 1
    segment_ids = frame["segment_id"].to_numpy()
    if int(segment_ids[start_idx]) != int(segment_ids[latest_idx]):
        raise ValueError("Latest eligible sample does not preserve a full same-segment lookback window.")
    market_features = _standardize_market_frame(frame, bundle)
    account_state = dict(live_account_state or _fallback_account_state_from_frame(frame, latest_idx))
    account_row = _account_row_from_state(account_state)
    account_features = _standardize_account_row(account_row, bundle)
    market_tensor = torch.from_numpy(market_features[start_idx : latest_idx + 1]).unsqueeze(0)
    account_tensor = torch.from_numpy(account_features).unsqueeze(0)
    with torch.no_grad():
        outputs = bundle.model(market_tensor, account_tensor)
    setup_probs = outputs["setup_probs"].cpu().numpy()[0]
    utility_outputs = outputs["utility_outputs"].cpu().numpy()
    row = frame.iloc[latest_idx]
    best_setup_idx = int(np.argmax(setup_probs))
    stage_code = 1.0 if str(account_state.get("account_stage", "challenge")) == "funded" else 0.0
    challenge_score_raw = float(_challenge_score_from_outputs(utility_outputs)[0])
    funded_score_raw = float(_funded_score_from_outputs(utility_outputs)[0])
    frontier_score_raw = funded_score_raw if stage_code >= 0.5 else challenge_score_raw
    frontier_score = float(
        normalize_frontier_score_array(
            np.array([frontier_score_raw], dtype=np.float32),
            bundle.frontier_stats,
        )[0]
    )
    return {
        "timestamp": str(row["timestamp"]),
        "session_date_utc": str(row["session_date_utc"]),
        "segment_id": int(row["segment_id"]),
        "close": float(row["close"]),
        "atr_14": float(row["atr_14"]),
        "account_stage": str(account_state.get("account_stage", "challenge")),
        "account_state": account_state,
        "chosen_setup": SETUPS[best_setup_idx],
        "probability": float(setup_probs[best_setup_idx]),
        "predicted_trade_utility": float(utility_outputs[0, 0]),
        "predicted_challenge_fail_prob_5d": float(utility_outputs[0, 4]),
        "predicted_challenge_fail_prob_10d": float(utility_outputs[0, 5]),
        "predicted_funded_breach_risk_5d": float(utility_outputs[0, 12]),
        "predicted_funded_breach_risk_20d": float(utility_outputs[0, 13]),
        "predicted_funded_expected_return_20d": float(utility_outputs[0, 11]),
        "predicted_frontier_score_raw": frontier_score_raw,
        "predicted_frontier_score": frontier_score,
        "bar_index_in_segment": int(row["bar_index_in_segment"]),
        "bars_remaining_in_segment": int(row["bars_remaining_in_segment"]),
    }


def _direction_for_setup(setup: str) -> str:
    return "BUY" if setup.startswith("long_") else "SELL"


def _load_runtime_state(path: Path, default_payload: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    if not path.exists():
        return dict(default_payload or {})
    return json.loads(path.read_text(encoding="utf-8"))


def _save_runtime_state(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _append_trade_txt_log(path: Path, result: Dict[str, object]) -> None:
    candidate = result.get("candidate", {})
    order_plan = result.get("order_plan", {})
    account = result.get("account", {})
    placement = result.get("placement", {})
    confirmation = result.get("confirmation", {})
    status = str(
        confirmation.get("dealStatus")
        or confirmation.get("status")
        or placement.get("status")
        or "submitted"
    )
    lines = [
        f"timestamp_utc: {result.get('timestamp_utc', '')}",
        f"mode: {result.get('mode', '')}",
        f"status: {status}",
        f"signal_timestamp: {order_plan.get('signal_timestamp', candidate.get('timestamp', ''))}",
        f"epic: {order_plan.get('epic', '')}",
        f"direction: {order_plan.get('direction', '')}",
        f"chosen_setup: {order_plan.get('chosen_setup', candidate.get('chosen_setup', ''))}",
        f"size: {order_plan.get('size', '')}",
        f"risk_pct: {order_plan.get('risk_pct', '')}",
        f"risk_cash: {order_plan.get('risk_cash', '')}",
        f"probability: {order_plan.get('probability', candidate.get('probability', ''))}",
        f"predicted_frontier_score: {order_plan.get('predicted_frontier_score', candidate.get('predicted_frontier_score', ''))}",
        f"predicted_frontier_score_raw: {order_plan.get('predicted_frontier_score_raw', candidate.get('predicted_frontier_score_raw', ''))}",
        f"predicted_trade_utility: {candidate.get('predicted_trade_utility', '')}",
        f"predicted_challenge_fail_prob_5d: {candidate.get('predicted_challenge_fail_prob_5d', '')}",
        f"predicted_challenge_fail_prob_10d: {candidate.get('predicted_challenge_fail_prob_10d', '')}",
        f"predicted_funded_breach_risk_5d: {candidate.get('predicted_funded_breach_risk_5d', '')}",
        f"predicted_funded_breach_risk_20d: {candidate.get('predicted_funded_breach_risk_20d', '')}",
        f"predicted_funded_expected_return_20d: {candidate.get('predicted_funded_expected_return_20d', '')}",
        f"price_reference: {order_plan.get('price_reference', candidate.get('close', ''))}",
        f"stop_distance: {order_plan.get('stop_distance', '')}",
        f"profit_distance: {order_plan.get('profit_distance', '')}",
        f"account_id: {account.get('current_account_id', '')}",
        f"account_balance: {account.get('account_balance', '')}",
        f"currency: {account.get('currency', '')}",
        f"deal_reference: {placement.get('dealReference', '')}",
        f"deal_id: {confirmation.get('dealId', '')}",
        f"broker_reason: {confirmation.get('reason', placement.get('reason', ''))}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _count_open_positions_for_epic(position_payload: Dict[str, object], epic: str) -> int:
    positions = position_payload.get("positions", [])
    total = 0
    for item in positions:
        market = item.get("market", {})
        if str(market.get("epic", "")) == epic:
            total += 1
    return total


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(parsed):
        return default
    return float(parsed)


def _extract_market_rules(market_details: Dict[str, object]) -> Dict[str, object]:
    instrument = market_details.get("instrument", {})
    dealing_rules = market_details.get("dealingRules", {})
    snapshot = market_details.get("snapshot", {})
    market_status = str(snapshot.get("marketStatus") or market_details.get("marketStatus") or "")
    snapshot_update_time = snapshot.get("updateTime") or market_details.get("updateTimeUTC") or market_details.get("updateTime")
    return {
        "market_status": market_status,
        "snapshot_update_time": snapshot_update_time,
        "bid": _safe_float(snapshot.get("bid", market_details.get("bid")), np.nan),
        "offer": _safe_float(snapshot.get("offer", market_details.get("offer")), np.nan),
        "min_deal_size": _safe_float(dealing_rules.get("minDealSize", {}).get("value"), _safe_float(instrument.get("lotSize", market_details.get("lotSize")), 0.0)),
        "min_size_increment": _safe_float(dealing_rules.get("minSizeIncrement", {}).get("value"), _safe_float(market_details.get("tickSize"), 0.0)),
    }


def _build_order_plan(
    candidate: Dict[str, object],
    session: CapitalSession,
    live_config: InstrumentLiveConfig,
    allocation_config: AllocationConfig,
    account_config: AccountStateConfig,
    market_rules: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    risk_pct = _stage_risk_pct(candidate, candidate["account_state"], account_config, allocation_config)
    risk_cash = session.account_balance * (risk_pct / 100.0)
    stop_distance = max(float(candidate["atr_14"]) * live_config.stop_atr_multiple, 0.25)
    target_distance = max(float(candidate["atr_14"]) * live_config.target_atr_multiple, stop_distance * 1.25)
    effective_min_size = max(live_config.min_size, _safe_float((market_rules or {}).get("min_deal_size"), 0.0))
    effective_size_step = max(live_config.size_step, _safe_float((market_rules or {}).get("min_size_increment"), 0.0))
    raw_size = risk_cash / max(stop_distance * live_config.point_value, 1e-6)
    size = _round_to_step(raw_size, effective_size_step, effective_min_size)
    return {
        "instrument_id": live_config.instrument_id,
        "epic": live_config.epic,
        "direction": _direction_for_setup(str(candidate["chosen_setup"])),
        "size": size,
        "risk_pct": round(float(risk_pct), 6),
        "risk_cash": round(float(risk_cash), 2),
        "stop_distance": round(float(stop_distance), 6),
        "profit_distance": round(float(target_distance), 6),
        "predicted_frontier_score": round(float(candidate["predicted_frontier_score"]), 6),
        "predicted_frontier_score_raw": round(float(candidate["predicted_frontier_score_raw"]), 6),
        "chosen_setup": candidate["chosen_setup"],
        "probability": round(float(candidate["probability"]), 6),
        "price_reference": round(float(candidate["close"]), 6),
        "signal_timestamp": str(candidate["timestamp"]),
        "market_status": str((market_rules or {}).get("market_status", "")),
    }


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


def _default_global_state(balance: float, now: datetime, args: argparse.Namespace) -> Dict[str, object]:
    start_balance = float(args.starting_balance) if args.starting_balance and args.starting_balance > 0.0 else float(balance)
    return {
        "prop_starting_balance": start_balance,
        "prop_running_peak": max(start_balance, float(balance)),
        "prop_current_day": str(now.date()),
        "prop_day_open_balance": float(balance),
        "prop_last_seen_balance": float(balance),
        "prop_days_elapsed": 1,
        "prop_profitable_days": 0,
        "prop_losing_days": 0,
        "prop_completed_day_returns_pct": [],
        "prop_completed_day_dates": [],
        "trades_taken_today": 0,
        "last_trade_pnl_r": 0.0,
        "win_streak": 0,
        "loss_streak": 0,
        "started_at_utc": _iso_utc_now(),
    }


def _roll_global_state_for_balance(state: Dict[str, object], balance: float, now: datetime) -> Dict[str, object]:
    if not state:
        return state
    today = str(now.date())
    current_day = str(state.get("prop_current_day") or today)
    if current_day != today:
        previous_close_balance = float(state.get("prop_last_seen_balance", balance))
        previous_open_balance = float(state.get("prop_day_open_balance", previous_close_balance))
        starting_balance = max(float(state.get("prop_starting_balance", previous_open_balance)), 1e-6)
        previous_return_pct = (previous_close_balance - previous_open_balance) / starting_balance * 100.0
        if previous_close_balance > previous_open_balance:
            state["prop_profitable_days"] = int(state.get("prop_profitable_days", 0)) + 1
        elif previous_close_balance < previous_open_balance:
            state["prop_losing_days"] = int(state.get("prop_losing_days", 0)) + 1
        if abs(previous_close_balance - previous_open_balance) > 0.0:
            returns = list(state.get("prop_completed_day_returns_pct", []))
            dates = list(state.get("prop_completed_day_dates", []))
            returns.append(round(float(previous_return_pct), 6))
            dates.append(current_day)
            state["prop_completed_day_returns_pct"] = returns
            state["prop_completed_day_dates"] = dates
        state["prop_current_day"] = today
        state["prop_day_open_balance"] = float(balance)
        state["prop_days_elapsed"] = int(state.get("prop_days_elapsed", 1)) + 1
        state["trades_taken_today"] = 0
    state["prop_last_seen_balance"] = float(balance)
    state["prop_running_peak"] = max(float(state.get("prop_running_peak", balance)), float(balance))
    return state


def _account_state_from_global_state(
    state: Dict[str, object],
    session: CapitalSession,
    args: argparse.Namespace,
) -> Dict[str, object]:
    current_balance = float(session.account_balance)
    starting_balance = max(float(state.get("prop_starting_balance", current_balance)), 1e-6)
    running_peak = max(float(state.get("prop_running_peak", current_balance)), 1e-6)
    target_balance = starting_balance * (1.0 + float(args.profit_target_pct) / 100.0)
    floor_balance = starting_balance * (1.0 - float(args.max_total_drawdown_pct) / 100.0)
    day_open_balance = float(state.get("prop_day_open_balance", current_balance))
    completed_returns = list(state.get("prop_completed_day_returns_pct", []))
    completed_dates = list(state.get("prop_completed_day_dates", []))
    day_pnl_pct = (current_balance - day_open_balance) / starting_balance * 100.0
    rolling_values = completed_returns.copy()
    if abs(current_balance - day_open_balance) > 0.0:
        rolling_values.append(day_pnl_pct)
    profitable_days = int(state.get("prop_profitable_days", 0))
    losing_days = int(state.get("prop_losing_days", 0))
    if current_balance > target_balance and profitable_days >= int(args.min_profitable_days):
        account_stage = "funded"
    else:
        account_stage = "challenge"
    distance_to_target_pct = max(0.0, (target_balance - current_balance) / starting_balance * 100.0)
    drawdown_pct = max(0.0, (running_peak - current_balance) / running_peak * 100.0)
    profitable_days_remaining = max(0, int(args.min_profitable_days) - profitable_days)
    current_month_return_pct = 0.0
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
    for day_label, day_return in zip(completed_dates, completed_returns):
        if str(day_label).startswith(today_prefix):
            current_month_return_pct += float(day_return)
    if str(state.get("prop_current_day", "")).startswith(today_prefix) and abs(current_balance - day_open_balance) > 0.0:
        current_month_return_pct += float(day_pnl_pct)
    return {
        "account_stage": account_stage,
        "account_passed_challenge": 1.0 if account_stage == "funded" else 0.0,
        "account_balance": round(current_balance, 6),
        "account_return_pct_to_date": round((current_balance / starting_balance - 1.0) * 100.0, 6),
        "account_drawdown_pct": round(drawdown_pct, 6),
        "account_distance_to_target_pct": round(distance_to_target_pct, 6),
        "account_profitable_days_so_far": profitable_days,
        "account_profitable_days_remaining": profitable_days_remaining,
        "account_days_elapsed": int(state.get("prop_days_elapsed", 1)),
        "day_pnl_pct_so_far": round(day_pnl_pct, 6),
        "day_loss_budget_remaining_pct": round(max(0.0, float(args.max_daily_loss_pct) + day_pnl_pct), 6),
        "total_drawdown_budget_remaining_pct": round(max(0.0, (current_balance - floor_balance) / starting_balance * 100.0), 6),
        "trades_taken_today": int(state.get("trades_taken_today", 0)),
        "trade_slots_remaining_today": max(0, int(args.max_trades_per_day) - int(state.get("trades_taken_today", 0))),
        "last_trade_pnl_r": round(float(state.get("last_trade_pnl_r", 0.0)), 6),
        "win_streak": int(state.get("win_streak", 0)),
        "loss_streak": int(state.get("loss_streak", 0)),
        "rolling_10_day_return_pct": round(sum(rolling_values[-10:]), 6),
        "rolling_20_day_return_pct": round(sum(rolling_values[-20:]), 6),
        "rolling_loss_cluster_penalty": round(_loss_cluster_penalty(rolling_values), 6),
        "current_month_return_pct": round(current_month_return_pct, 6),
        "realized_profitable_days": profitable_days,
        "realized_losing_days": losing_days,
    }


def _candidate_age_seconds(candidate_timestamp: str, now: datetime) -> float:
    timestamp = pd.Timestamp(candidate_timestamp)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return max(0.0, (now - timestamp.to_pydatetime()).total_seconds())


def _hold_result(
    live_config: InstrumentLiveConfig,
    reason: str,
    candidate: Dict[str, object],
    extra: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    result = {
        "timestamp_utc": _iso_utc_now(),
        "instrument_id": live_config.instrument_id,
        "mode": "hold",
        "reason": reason,
        "candidate": candidate,
    }
    if extra:
        result.update(extra)
    _append_jsonl(live_config.log_dir / "live_decisions.jsonl", result)
    return result


def _prepare_scored_instrument(
    args: argparse.Namespace,
    client: CapitalComClient,
    live_config: InstrumentLiveConfig,
    positions: Dict[str, object],
    market_details: Dict[str, object],
    live_account_state: Dict[str, object],
) -> ScoredInstrument:
    snapshot_status: Optional[SnapshotUpdateResult] = None
    resolved_epic = str(market_details.get("epic", live_config.epic) or live_config.epic)
    try:
        snapshot_status = update_snapshot(
            client,
            SnapshotUpdaterConfig(
                instrument_id=live_config.instrument_id,
                epic=resolved_epic,
                snapshot_path=live_config.dataset_path,
                log_dir=live_config.log_dir,
                stale_after_seconds=min(int(args.stale_data_seconds), 120),
            ),
        )
    except Exception as exc:  # noqa: BLE001
        runtime_state_path = live_config.log_dir / "state.json"
        runtime_state = _load_runtime_state(
            runtime_state_path,
            default_payload={"current_day": None, "last_signal_timestamp": None},
        )
        return ScoredInstrument(
            live_config=live_config,
            candidate={
                "instrument_id": live_config.instrument_id,
                "epic": live_config.epic,
                "dataset_path": str(live_config.dataset_path),
                "timestamp": "",
            },
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules={},
            market_details=market_details,
            snapshot_status={"error": str(exc)},
            precheck_hold_reason="snapshot_update_failed",
            precheck_extra={"error": str(exc)},
        )
    try:
        candidate = score_latest_candidate(
            dataset_path=live_config.dataset_path,
            artifacts_dir=live_config.artifacts_dir,
            live_account_state=live_account_state,
        )
    except Exception as exc:  # noqa: BLE001
        runtime_state_path = live_config.log_dir / "state.json"
        runtime_state = _load_runtime_state(
            runtime_state_path,
            default_payload={"current_day": None, "last_signal_timestamp": None},
        )
        return ScoredInstrument(
            live_config=live_config,
            candidate={
                "instrument_id": live_config.instrument_id,
                "epic": live_config.epic,
                "dataset_path": str(live_config.dataset_path),
                "timestamp": "",
            },
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules={},
            market_details=market_details,
            snapshot_status=asdict(snapshot_status) if snapshot_status else None,
            precheck_hold_reason="candidate_scoring_failed",
            precheck_extra={"error": str(exc)},
        )
    candidate["instrument_id"] = live_config.instrument_id
    candidate["epic"] = resolved_epic
    candidate["dataset_path"] = str(live_config.dataset_path)
    runtime_state_path = live_config.log_dir / "state.json"
    runtime_state = _load_runtime_state(
        runtime_state_path,
        default_payload={"current_day": None, "last_signal_timestamp": None},
    )
    today = str(datetime.now(timezone.utc).date())
    if runtime_state.get("current_day") != today:
        runtime_state = {"current_day": today, "last_signal_timestamp": None}

    now = datetime.now(timezone.utc)
    candidate_age_seconds = _candidate_age_seconds(candidate["timestamp"], now)
    candidate["signal_age_seconds"] = round(candidate_age_seconds, 3)
    market_rules = _extract_market_rules(market_details)
    candidate["market_status"] = market_rules["market_status"]
    candidate["broker_bid"] = market_rules["bid"]
    candidate["broker_offer"] = market_rules["offer"]
    candidate["broker_snapshot_update_time"] = market_rules["snapshot_update_time"]

    if runtime_state.get("last_signal_timestamp") == candidate["timestamp"]:
        return ScoredInstrument(
            live_config=live_config,
            candidate=candidate,
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules=market_rules,
            market_details=market_details,
            snapshot_status=asdict(snapshot_status) if snapshot_status else None,
            precheck_hold_reason="latest_signal_already_processed",
        )

    if candidate_age_seconds > float(args.stale_data_seconds):
        return ScoredInstrument(
            live_config=live_config,
            candidate=candidate,
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules=market_rules,
            market_details=market_details,
            snapshot_status=asdict(snapshot_status) if snapshot_status else None,
            precheck_hold_reason="stale_live_dataset",
            precheck_extra={
                "stale_data_seconds": args.stale_data_seconds,
                "snapshot_status": asdict(snapshot_status) if snapshot_status else None,
            },
        )

    if str(market_rules["market_status"]).upper() != "TRADEABLE":
        return ScoredInstrument(
            live_config=live_config,
            candidate=candidate,
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules=market_rules,
            market_details=market_details,
            snapshot_status=asdict(snapshot_status) if snapshot_status else None,
            precheck_hold_reason="market_not_tradeable",
            precheck_extra={"market_status": market_rules["market_status"]},
        )

    if float(candidate["predicted_frontier_score"]) < live_config.min_frontier_score:
        return ScoredInstrument(
            live_config=live_config,
            candidate=candidate,
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules=market_rules,
            market_details=market_details,
            snapshot_status=asdict(snapshot_status) if snapshot_status else None,
            precheck_hold_reason="frontier_score_below_threshold",
            precheck_extra={"threshold": live_config.min_frontier_score},
        )

    open_positions_for_epic = _count_open_positions_for_epic(positions, live_config.epic)
    if open_positions_for_epic >= live_config.max_positions_per_epic:
        return ScoredInstrument(
            live_config=live_config,
            candidate=candidate,
            runtime_state_path=runtime_state_path,
            runtime_state=runtime_state,
            market_rules=market_rules,
            market_details=market_details,
            snapshot_status=asdict(snapshot_status) if snapshot_status else None,
            precheck_hold_reason="open_position_limit_reached",
            precheck_extra={"open_positions_for_epic": open_positions_for_epic},
        )
    return ScoredInstrument(
        live_config=live_config,
        candidate=candidate,
        runtime_state_path=runtime_state_path,
        runtime_state=runtime_state,
        market_rules=market_rules,
        market_details=market_details,
        snapshot_status=asdict(snapshot_status) if snapshot_status else None,
    )


def _mark_processed_signal(scored: ScoredInstrument) -> None:
    scored.runtime_state["last_signal_timestamp"] = scored.candidate["timestamp"]
    _save_runtime_state(scored.runtime_state_path, scored.runtime_state)


def _result_from_precheck_hold(scored: ScoredInstrument) -> Dict[str, object]:
    result = _hold_result(
        scored.live_config,
        str(scored.precheck_hold_reason),
        scored.candidate,
        extra=scored.precheck_extra,
    )
    result["snapshot_status"] = scored.snapshot_status
    return result


def _run_accepted_instrument(
    args: argparse.Namespace,
    client: CapitalComClient,
    session: CapitalSession,
    scored: ScoredInstrument,
    global_state: Dict[str, object],
    paper_state: Dict[str, object],
) -> Dict[str, object]:
    candidate = scored.candidate
    account_config = AccountStateConfig(
        starting_balance=float(global_state.get("prop_starting_balance", session.account_balance)),
        profit_target_pct=float(args.profit_target_pct),
        min_profitable_days=int(args.min_profitable_days),
        max_daily_loss_pct=float(args.max_daily_loss_pct),
        max_total_drawdown_pct=float(args.max_total_drawdown_pct),
        max_trades_per_day=int(args.max_trades_per_day),
        risk_per_trade_pct=float(args.fallback_risk_pct),
        initial_account_stage=str(candidate["account_stage"]),
    )
    allocation_config = AllocationConfig(max_trades_per_day=int(args.max_trades_per_day))
    risk_pct = _stage_risk_pct(candidate, candidate["account_state"], account_config, allocation_config)
    order_plan = build_shared_order_plan(
        candidate,
        contract=ContractSpec(
            instrument_id=scored.live_config.instrument_id,
            point_value=scored.live_config.point_value,
            min_size=scored.live_config.min_size,
            size_step=scored.live_config.size_step,
            max_positions_per_epic=scored.live_config.max_positions_per_epic,
            stop_atr_multiple=scored.live_config.stop_atr_multiple,
            target_atr_multiple=scored.live_config.target_atr_multiple,
        ),
        account_balance=session.account_balance,
        risk_pct=risk_pct,
        market_min_size=_safe_float(scored.market_rules.get("min_deal_size"), 0.0),
        market_size_step=_safe_float(scored.market_rules.get("min_size_increment"), 0.0),
    )
    result = {
        "timestamp_utc": _iso_utc_now(),
        "instrument_id": scored.live_config.instrument_id,
        "mode": "simulation" if args.simulation_mode and not args.execute_live else ("dry_run" if not args.execute_live else "live"),
        "candidate": candidate,
        "order_plan": {
            **asdict(order_plan),
            "epic": scored.live_config.epic,
            "market_status": str(scored.market_rules.get("market_status", "")),
        },
        "account": asdict(session),
        "snapshot_status": scored.snapshot_status,
    }

    if args.execute_live:
        placement = client.place_position(
            epic=scored.live_config.epic,
            direction=order_plan.direction,
            size=float(order_plan.size),
            stop_distance=float(order_plan.stop_distance),
            profit_distance=float(order_plan.target_distance),
        )
        result["placement"] = placement
        deal_reference = str(placement.get("dealReference", ""))
        if deal_reference:
            try:
                result["confirmation"] = client.confirm(deal_reference)
            except Exception as exc:  # noqa: BLE001
                result["confirmation_error"] = str(exc)
        global_state["trades_taken_today"] = int(global_state.get("trades_taken_today", 0)) + 1
        _append_trade_txt_log(scored.live_config.log_dir / "trade_entries.txt", result)
    elif args.simulation_mode:
        append_open_position(
            paper_state,
            instrument_id=scored.live_config.instrument_id,
            dataset_path=str(scored.live_config.dataset_path),
            segment_id=int(candidate["segment_id"]),
            order_plan=result["order_plan"],
            candidate=candidate,
        )
        global_state["trades_taken_today"] = int(global_state.get("trades_taken_today", 0)) + 1

    _mark_processed_signal(scored)
    _append_jsonl(scored.live_config.log_dir / "live_decisions.jsonl", result)
    return result


def _build_metrics_snapshot(
    session: CapitalSession,
    global_state: Dict[str, object],
    live_account_state: Dict[str, object],
    positions: Dict[str, object],
    paper_state: Dict[str, object],
    results: List[Dict[str, object]],
) -> Dict[str, object]:
    open_positions = positions.get("positions", [])
    open_positions_by_epic: Dict[str, int] = {}
    mode_counts: Dict[str, int] = {}
    reason_counts: Dict[str, int] = {}
    setup_counts: Dict[str, int] = {}
    manager_bottlenecks: Dict[str, int] = {}
    snapshot_status_by_instrument: Dict[str, object] = {}
    instrument_status: Dict[str, Dict[str, object]] = {}
    for item in open_positions:
        epic = str(item.get("market", {}).get("epic", ""))
        open_positions_by_epic[epic] = open_positions_by_epic.get(epic, 0) + 1
    for result in results:
        mode = str(result.get("mode", "unknown"))
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        reason = str(result.get("reason", "accepted"))
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if reason.startswith("rejected_by_allocator") or reason.startswith("rejected_by_portfolio"):
            manager_bottlenecks["allocator"] = manager_bottlenecks.get("allocator", 0) + 1
        elif reason in {"frontier_score_below_threshold", "local_daily_trade_cap_reached"}:
            manager_bottlenecks["manager_policy"] = manager_bottlenecks.get("manager_policy", 0) + 1
        elif reason in {"market_not_tradeable", "open_position_limit_reached"}:
            manager_bottlenecks["broker_guard"] = manager_bottlenecks.get("broker_guard", 0) + 1
        elif reason in {"snapshot_update_failed", "candidate_scoring_failed", "stale_live_dataset"}:
            manager_bottlenecks["data_or_model"] = manager_bottlenecks.get("data_or_model", 0) + 1
        else:
            manager_bottlenecks["other"] = manager_bottlenecks.get("other", 0) + 1
        candidate = result.get("candidate", {})
        setup = str(candidate.get("chosen_setup", ""))
        if setup:
            setup_counts[setup] = setup_counts.get(setup, 0) + 1
        instrument_id = str(result.get("instrument_id", ""))
        if instrument_id:
            snapshot = result.get("snapshot_status", {})
            snapshot_status_by_instrument[instrument_id] = snapshot
            instrument_status[instrument_id] = {
                "mode": result.get("mode", ""),
                "reason": result.get("reason", "accepted"),
                "setup": setup,
                "frontier_score": round(float(candidate.get("predicted_frontier_score", 0.0)), 6) if candidate else None,
                "frontier_score_raw": round(float(candidate.get("predicted_frontier_score_raw", 0.0)), 6) if candidate else None,
                "probability": round(float(candidate.get("probability", 0.0)), 6) if candidate else None,
                "signal_age_seconds": round(float(candidate.get("signal_age_seconds", 0.0)), 3) if candidate else None,
                "market_status": candidate.get("market_status"),
                "signal_timestamp": candidate.get("timestamp"),
                "broker_bid": candidate.get("broker_bid"),
                "broker_offer": candidate.get("broker_offer"),
                "allocator_decision": candidate.get("allocator_decision"),
                "applied_risk_pct": candidate.get("applied_risk_pct"),
                "size": result.get("order_plan", {}).get("size"),
                "snapshot_latest_timestamp_utc": snapshot.get("latest_timestamp_utc") if isinstance(snapshot, dict) else None,
                "snapshot_latest_age_seconds": snapshot.get("latest_age_seconds") if isinstance(snapshot, dict) else None,
                "snapshot_rows_appended": snapshot.get("rows_appended") if isinstance(snapshot, dict) else None,
                "snapshot_missing_alert_count": len(snapshot.get("missing_data_alerts", [])) if isinstance(snapshot, dict) else None,
            }
    paper_summary = build_paper_summary(paper_state)
    return {
        "timestamp_utc": _iso_utc_now(),
        "account_id": session.current_account_id,
        "currency": session.currency,
        "account_balance": round(float(session.account_balance), 2),
        "starting_balance": round(float(global_state.get("prop_starting_balance", session.account_balance)), 2),
        "account_stage": live_account_state["account_stage"],
        "account_return_pct_to_date": live_account_state["account_return_pct_to_date"],
        "account_drawdown_pct": live_account_state["account_drawdown_pct"],
        "day_pnl_pct_so_far": live_account_state["day_pnl_pct_so_far"],
        "day_loss_budget_remaining_pct": live_account_state["day_loss_budget_remaining_pct"],
        "total_drawdown_budget_remaining_pct": live_account_state["total_drawdown_budget_remaining_pct"],
        "trade_slots_remaining_today": live_account_state["trade_slots_remaining_today"],
        "profitable_days": live_account_state["realized_profitable_days"],
        "losing_days": live_account_state["realized_losing_days"],
        "trades_taken_today": live_account_state["trades_taken_today"],
        "open_positions_total": len(open_positions),
        "open_positions_by_epic": open_positions_by_epic,
        "mode_counts": mode_counts,
        "reason_counts": reason_counts,
        "manager_bottlenecks": manager_bottlenecks,
        "setup_counts": setup_counts,
        "instrument_status": instrument_status,
        "snapshot_status_by_instrument": snapshot_status_by_instrument,
        "paper_summary": paper_summary,
        "results": results,
    }


def _print_metrics(snapshot: Dict[str, object]) -> None:
    print(
        "[{ts}] balance={bal:.2f} {ccy} stage={stage} return={ret:.4f}% drawdown={dd:.4f}% "
        "day_pnl={day_pnl:.4f}% day_budget_left={day_budget:.4f}% dd_budget_left={dd_budget:.4f}% "
        "profitable_days={pd} losing_days={ld} trades_today={tt} slots_left={slots} open_positions={op} "
        "modes={modes} bottlenecks={bottlenecks} setups={setups} paper_active={paper_active} paper_closed={paper_closed} "
        "paper_roll_pnl_r={paper_pnl_r:.4f}".format(
            ts=snapshot["timestamp_utc"],
            bal=float(snapshot["account_balance"]),
            ccy=snapshot["currency"],
            stage=snapshot["account_stage"],
            ret=float(snapshot["account_return_pct_to_date"]),
            dd=float(snapshot["account_drawdown_pct"]),
            day_pnl=float(snapshot.get("day_pnl_pct_so_far", 0.0)),
            day_budget=float(snapshot.get("day_loss_budget_remaining_pct", 0.0)),
            dd_budget=float(snapshot.get("total_drawdown_budget_remaining_pct", 0.0)),
            pd=int(snapshot["profitable_days"]),
            ld=int(snapshot["losing_days"]),
            tt=int(snapshot["trades_taken_today"]),
            slots=int(snapshot.get("trade_slots_remaining_today", 0)),
            op=int(snapshot["open_positions_total"]),
            modes=json.dumps(snapshot.get("mode_counts", {}), sort_keys=True),
            bottlenecks=json.dumps(snapshot.get("manager_bottlenecks", {}), sort_keys=True),
            setups=json.dumps(snapshot.get("setup_counts", {}), sort_keys=True),
            paper_active=int(snapshot.get("paper_summary", {}).get("active_trades", 0)),
            paper_closed=int(snapshot.get("paper_summary", {}).get("closed_trades", 0)),
            paper_pnl_r=float(snapshot.get("paper_summary", {}).get("rolling_pnl_r", 0.0)),
        )
    )
    for instrument_id, status in sorted(snapshot.get("instrument_status", {}).items()):
        print(
            "  {instrument} mode={mode} reason={reason} setup={setup} frontier={frontier:.6f} "
            "prob={prob:.6f} age_sec={age:.0f} risk_pct={risk} size={size} market={market} "
            "snap_age={snap_age} rows+={rows_added} gap_alerts={gap_alerts}".format(
                instrument=instrument_id,
                mode=status.get("mode", ""),
                reason=status.get("reason", "accepted"),
                setup=status.get("setup", ""),
                frontier=float(status.get("frontier_score", 0.0)),
                prob=float(status.get("probability", 0.0)),
                age=float(status.get("signal_age_seconds", 0.0)),
                risk=(
                    f"{float(status.get('applied_risk_pct')):.3f}%"
                    if status.get("applied_risk_pct") is not None
                    else "-"
                ),
                size=status.get("size", "-"),
                market=status.get("market_status", "-"),
                snap_age=(
                    f"{float(status.get('snapshot_latest_age_seconds')):.0f}s"
                    if status.get("snapshot_latest_age_seconds") is not None
                    else "-"
                ),
                rows_added=status.get("snapshot_rows_appended", "-"),
                gap_alerts=status.get("snapshot_missing_alert_count", "-"),
            )
        )
    for setup, perf in sorted(snapshot.get("paper_summary", {}).get("performance", {}).items()):
        print(
            "  specialist {setup} trades={trades} rolling_ap={rolling_ap:.4f} rolling_pnl_r={rolling_pnl_r:.4f}".format(
                setup=setup,
                trades=int(perf.get("trades", 0)),
                rolling_ap=float(perf.get("rolling_ap", 0.0)),
                rolling_pnl_r=float(perf.get("rolling_pnl_r", 0.0)),
            )
        )


def _single_cycle(
    args: argparse.Namespace,
    client: CapitalComClient,
    instrument_configs: List[InstrumentLiveConfig],
    base_log_dir: Path,
) -> Tuple[CapitalSession, Dict[str, object], Dict[str, object], Dict[str, object], List[Dict[str, object]]]:
    session = client.create_session()
    positions = client.list_positions()
    global_state_path = base_log_dir / "_server_state.json"
    paper_state_path = base_log_dir / "_paper_state.json"
    global_state = _load_runtime_state(global_state_path)
    paper_state = load_paper_state(paper_state_path)
    if not global_state:
        global_state = _default_global_state(session.account_balance, datetime.now(timezone.utc), args)
    global_state = _roll_global_state_for_balance(global_state, session.account_balance, datetime.now(timezone.utc))
    live_account_state = _account_state_from_global_state(global_state, session, args)
    results: List[Dict[str, object]] = []
    scored_instruments: List[ScoredInstrument] = []
    allocation_config = AllocationConfig(max_trades_per_day=int(args.max_trades_per_day))
    for config in instrument_configs:
        market_details = client.get_market_details(config.epic)
        scored = _prepare_scored_instrument(
            args=args,
            client=client,
            live_config=config,
            positions=positions,
            market_details=market_details,
            live_account_state=live_account_state,
        )
        scored_instruments.append(scored)

    if args.simulation_mode:
        default_stop_atr = float(instrument_configs[0].stop_atr_multiple) if instrument_configs else 0.75
        default_target_atr = float(instrument_configs[0].target_atr_multiple) if instrument_configs else 1.25
        paper_state = sync_paper_positions(
            paper_state,
            execution_policy=ExecutionPolicy(
                stop_atr_multiple=float(args.stop_atr_multiple if args.stop_atr_multiple is not None else default_stop_atr),
                target_atr_multiple=float(args.target_atr_multiple if args.target_atr_multiple is not None else default_target_atr),
                breakeven_trigger_r=float(args.breakeven_trigger_r) if args.breakeven_trigger_r > 0.0 else None,
                max_hold_bars=int(args.max_hold_bars),
            ),
        )

    allocatable = [item for item in scored_instruments if item.precheck_hold_reason is None]
    if int(global_state.get("trades_taken_today", 0)) >= int(args.max_trades_per_day):
        for scored in allocatable:
            _mark_processed_signal(scored)
            hold_result = _hold_result(scored.live_config, "local_daily_trade_cap_reached", scored.candidate)
            hold_result["snapshot_status"] = scored.snapshot_status
            results.append(hold_result)
        allocatable = []

    accepted_by_key: Dict[Tuple[str, str], Dict[str, object]] = {}
    rejected_by_key: Dict[Tuple[str, str], Dict[str, object]] = {}
    if allocatable:
        open_position_context = [
            {
                "instrument_id": str(item.get("market", {}).get("epic", "")),
                "direction": str(item.get("position", {}).get("direction", "")),
                "risk_pct": 0.0,
            }
            for item in positions.get("positions", [])
        ]
        accepted_rows, rejected_rows = allocate_portfolio(
            [item.candidate for item in allocatable],
            live_account_state,
            AccountStateConfig(
                starting_balance=float(global_state.get("prop_starting_balance", session.account_balance)),
                profit_target_pct=float(args.profit_target_pct),
                min_profitable_days=int(args.min_profitable_days),
                max_daily_loss_pct=float(args.max_daily_loss_pct),
                max_total_drawdown_pct=float(args.max_total_drawdown_pct),
                max_trades_per_day=int(args.max_trades_per_day),
                risk_per_trade_pct=float(args.fallback_risk_pct),
                initial_account_stage=str(live_account_state.get("account_stage", "challenge")),
            ),
            allocation_config,
            PortfolioConstraints(
                max_concurrent_trades=int(args.max_trades_per_day),
                max_portfolio_risk_pct=float(args.max_portfolio_risk_pct),
                max_same_direction_per_correlation_group=int(args.max_same_direction_per_correlation_group),
            ),
            current_open_positions=open_position_context,
            performance_state=build_paper_summary(paper_state).get("performance", {}),
        )
        accepted_by_key = {
            (str(row.get("instrument_id", "")), str(row.get("timestamp", ""))): row
            for row in accepted_rows
        }
        rejected_by_key = {
            (str(row.get("instrument_id", "")), str(row.get("timestamp", ""))): row
            for row in rejected_rows
        }

    for scored in scored_instruments:
        if scored.precheck_hold_reason is not None:
            results.append(_result_from_precheck_hold(scored))
            continue
        key = (scored.live_config.instrument_id, str(scored.candidate["timestamp"]))
        if key in accepted_by_key:
            scored.candidate.update(accepted_by_key[key])
            results.append(
                _run_accepted_instrument(
                    args=args,
                    client=client,
                    session=session,
                    scored=scored,
                    global_state=global_state,
                    paper_state=paper_state,
                )
            )
            continue
        if key in rejected_by_key:
            scored.candidate.update(rejected_by_key[key])
            _mark_processed_signal(scored)
            hold_result = _hold_result(
                scored.live_config,
                str(rejected_by_key[key].get("allocator_decision", "rejected_by_allocator")),
                scored.candidate,
                extra={"allocator_score": rejected_by_key[key].get("allocator_score")},
            )
            hold_result["snapshot_status"] = scored.snapshot_status
            results.append(hold_result)
            continue
        _mark_processed_signal(scored)
        hold_result = _hold_result(scored.live_config, "allocator_no_decision", scored.candidate)
        hold_result["snapshot_status"] = scored.snapshot_status
        results.append(hold_result)
    _save_runtime_state(global_state_path, global_state)
    if args.simulation_mode:
        save_paper_state(paper_state_path, paper_state)
    return session, global_state, positions, paper_state, results


def _run_once(
    args: argparse.Namespace,
    client: CapitalComClient,
    instrument_configs: List[InstrumentLiveConfig],
    base_log_dir: Path,
) -> int:
    session, global_state, positions, paper_state, results = _single_cycle(args, client, instrument_configs, base_log_dir)
    live_account_state = _account_state_from_global_state(global_state, session, args)
    metrics = _build_metrics_snapshot(session, global_state, live_account_state, positions, paper_state, results)
    print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    _append_jsonl(base_log_dir / "server_metrics.jsonl", metrics)
    return 0


def _serve_loop(
    args: argparse.Namespace,
    client: CapitalComClient,
    instrument_configs: List[InstrumentLiveConfig],
    base_log_dir: Path,
) -> int:
    loops = 0
    while True:
        loop_started = time.time()
        session, global_state, positions, paper_state, results = _single_cycle(args, client, instrument_configs, base_log_dir)
        live_account_state = _account_state_from_global_state(global_state, session, args)
        metrics = _build_metrics_snapshot(session, global_state, live_account_state, positions, paper_state, results)
        _append_jsonl(base_log_dir / "server_metrics.jsonl", metrics)
        _print_metrics(metrics)
        loops += 1
        if args.max_loops and loops >= args.max_loops:
            return 0
        elapsed = time.time() - loop_started
        sleep_seconds = max(1.0, float(args.poll_seconds) - elapsed)
        time.sleep(sleep_seconds)


def run_live(args: argparse.Namespace) -> int:
    env_map = _read_env_file(Path(args.env_file).resolve())
    credentials = _load_credentials(env_map)
    instrument_configs, base_log_dir = _load_instrument_configs(args, env_map)
    raise_for_invalid_contracts(
        [
            ContractSpec(
                instrument_id=config.instrument_id,
                point_value=config.point_value,
                min_size=config.min_size,
                size_step=config.size_step,
                max_positions_per_epic=config.max_positions_per_epic,
                stop_atr_multiple=config.stop_atr_multiple,
                target_atr_multiple=config.target_atr_multiple,
            )
            for config in instrument_configs
        ]
    )
    client = CapitalComClient(credentials)
    if args.serve:
        return _serve_loop(args, client, instrument_configs, base_log_dir)
    return _run_once(args, client, instrument_configs, base_log_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frontier utility model against a Capital.com demo account.")
    parser.add_argument("--dataset", help="Prepared live feature snapshot CSV/GZ with at least lookback rows.")
    parser.add_argument("--artifacts-dir", help="Utility-model artifact directory containing model.pt.")
    parser.add_argument("--instruments", help="Comma-separated instrument ids, for example US100,US500.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--epic", help="Capital.com epic to trade, for example the demo epic for US100.")
    parser.add_argument("--point-value", type=float)
    parser.add_argument("--min-size", type=float)
    parser.add_argument("--size-step", type=float)
    parser.add_argument("--stop-atr-multiple", type=float)
    parser.add_argument("--target-atr-multiple", type=float)
    parser.add_argument("--breakeven-trigger-r", type=float, default=0.0)
    parser.add_argument("--max-hold-bars", type=int, default=30)
    parser.add_argument("--max-positions-per-epic", type=int)
    parser.add_argument("--min-frontier-score", type=float)
    parser.add_argument("--max-trades-per-day", type=int, default=2)
    parser.add_argument("--max-portfolio-risk-pct", type=float, default=1.0)
    parser.add_argument("--max-same-direction-per-correlation-group", type=int, default=1)
    parser.add_argument("--fallback-risk-pct", type=float, default=0.25)
    parser.add_argument("--starting-balance", type=float, default=0.0)
    parser.add_argument("--profit-target-pct", type=float, default=10.0)
    parser.add_argument("--min-profitable-days", type=int, default=3)
    parser.add_argument("--max-daily-loss-pct", type=float, default=5.0)
    parser.add_argument("--max-total-drawdown-pct", type=float, default=10.0)
    parser.add_argument("--stale-data-seconds", type=int, default=900)
    parser.add_argument("--serve", "--server", dest="serve", action="store_true", help="Run continuously and print terminal metrics each cycle.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--max-loops", type=int, default=0)
    parser.add_argument("--log-dir")
    parser.add_argument("--simulation-mode", action="store_true", help="Record accepted trades into a paper ledger and resolve them from live bars.")
    parser.add_argument("--execute-live", action="store_true", help="Actually place an order. Default is dry-run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(run_live(args))


if __name__ == "__main__":
    raise SystemExit(main())
