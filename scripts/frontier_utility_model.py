from __future__ import annotations

import argparse
import gzip
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, Dataset


SETUPS = [
    "long_reversal",
    "long_continuation",
    "short_reversal",
    "short_continuation",
]
LABEL_COLUMNS = [f"label_{setup}" for setup in SETUPS]
UTILITY_SETUP_COLUMNS = [f"utility_{setup}_r" for setup in SETUPS]
CHALLENGE_TARGET_COLUMNS = [
    "challenge_pass_prob_5d",
    "challenge_pass_prob_10d",
    "challenge_pass_prob_20d",
    "challenge_fail_prob_5d",
    "challenge_fail_prob_10d",
    "challenge_expected_days_to_resolution",
    "challenge_distance_to_target_delta",
    "challenge_daily_loss_budget_consumption",
    "challenge_total_drawdown_budget_consumption",
]
FUNDED_TARGET_COLUMNS = [
    "funded_expected_return_5d",
    "funded_expected_return_20d",
    "funded_breach_risk_5d",
    "funded_breach_risk_20d",
    "funded_expected_drawdown",
    "funded_expected_payout_growth",
]
UTILITY_TARGET_COLUMNS = [
    "trade_challenge_utility",
    *CHALLENGE_TARGET_COLUMNS,
    *FUNDED_TARGET_COLUMNS,
]
BASE_COLUMNS = [
    "timestamp",
    "session_date_utc",
    "segment_id",
    "bar_index_in_segment",
    "bars_remaining_in_segment",
    "open",
    "high",
    "low",
    "close",
    "atr_14",
]
ACCOUNT_COLUMNS = [
    "account_stage_code",
    "account_passed_challenge",
    "is_challenge_stage",
    "is_funded_stage",
    "account_balance",
    "account_return_pct_to_date",
    "account_drawdown_pct",
    "account_distance_to_target_pct",
    "account_profitable_days_so_far",
    "account_profitable_days_remaining",
    "account_days_elapsed",
    "day_pnl_pct_so_far",
    "day_loss_budget_remaining_pct",
    "total_drawdown_budget_remaining_pct",
    "trades_taken_today",
    "trade_slots_remaining_today",
    "last_trade_pnl_r",
    "win_streak",
    "loss_streak",
]
MARKET_FEATURE_COLUMNS = [
    "return_1",
    "return_5",
    "return_15",
    "body_return",
    "upper_wick_pct",
    "lower_wick_pct",
    "true_range_pct",
    "atr_pct",
    "rolling_vol_15",
    "rolling_vol_60",
    "rolling_range_15_atr",
    "rolling_range_60_atr",
    "trend_score_10",
    "trend_score_30",
    "trend_score_60",
    "pullback_score_5",
    "pullback_score_10",
    "session_progress",
    "bars_remaining_pct",
    "session_range_pos",
    "session_range_atr",
    "distance_to_session_high_atr",
    "distance_to_session_low_atr",
    "session_open_return_atr",
    "minute_sin",
    "minute_cos",
    "weekday_sin",
    "weekday_cos",
    "london_minute_sin",
    "london_minute_cos",
    "new_york_minute_sin",
    "new_york_minute_cos",
    "is_asia_session",
    "is_europe_session",
    "is_us_session",
    "is_session_open_window",
    "is_session_close_window",
    "is_london_open_window",
    "is_new_york_open_window",
    "is_london_new_york_overlap",
    "prev_session_body_return_1",
    "prev_session_body_return_2",
    "prev_session_body_return_3",
    "prev_session_body_return_4",
    "prev_session_body_return_5",
    "prev_session_direction_1",
    "prev_session_direction_2",
    "prev_session_direction_3",
    "prev_session_direction_4",
    "prev_session_direction_5",
    "prev5_bullish_fraction",
    "prev5_bearish_fraction",
    "prev5_net_body_return",
    "prev_session_streak_sign",
    "prev_session_streak_length",
]
ALL_FEATURE_COLUMNS = MARKET_FEATURE_COLUMNS + ACCOUNT_COLUMNS


@dataclass
class TrainConfig:
    train_fraction: float = 0.70
    val_fraction: float = 0.15
    lookback: int = 96
    batch_size: int = 256
    epochs: int = 6
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    dropout: float = 0.15
    hidden_dim: int = 128
    kernel_size: int = 3
    channels: Tuple[int, ...] = (64, 64, 96)
    max_train_samples: int = 0
    max_eval_samples: int = 0
    seed: int = 7
    setup_loss_weight: float = 0.40
    utility_loss_weight: float = 1.00
    challenge_pass_loss_weight: float = 0.80
    challenge_fail_loss_weight: float = 0.70
    challenge_resolution_loss_weight: float = 0.35
    challenge_distance_loss_weight: float = 0.40
    challenge_budget_loss_weight: float = 0.40
    funded_return_loss_weight: float = 0.60
    funded_risk_loss_weight: float = 0.60
    funded_drawdown_loss_weight: float = 0.40
    funded_payout_loss_weight: float = 0.45
    ranking_loss_weight: float = 0.15


class SequenceDataset(Dataset):
    def __init__(
        self,
        market_features: np.ndarray,
        account_features: np.ndarray,
        setup_targets: np.ndarray,
        utility_targets: np.ndarray,
        end_indices: np.ndarray,
        lookback: int,
    ):
        self.market_features = torch.from_numpy(np.ascontiguousarray(market_features.astype(np.float32)))
        self.account_features = torch.from_numpy(np.ascontiguousarray(account_features.astype(np.float32)))
        self.setup_targets = torch.from_numpy(np.ascontiguousarray(setup_targets.astype(np.float32)))
        self.utility_targets = torch.from_numpy(np.ascontiguousarray(utility_targets.astype(np.float32)))
        self.end_indices = np.ascontiguousarray(end_indices.astype(np.int64))
        self.lookback = int(lookback)

    def __len__(self) -> int:
        return int(len(self.end_indices))

    def __getitem__(self, idx: int):
        end_idx = int(self.end_indices[idx])
        start_idx = end_idx - self.lookback + 1
        return (
            self.market_features[start_idx : end_idx + 1],
            self.account_features[end_idx],
            self.setup_targets[end_idx],
            self.utility_targets[end_idx],
            end_idx,
        )


class Chomp1d(nn.Module):
    def __init__(self, chomp_size: int):
        super().__init__()
        self.chomp_size = int(chomp_size)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.chomp_size <= 0:
            return tensor
        return tensor[:, :, : -self.chomp_size]


class ResidualTemporalBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int, dilation: int, dropout: float):
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.act1 = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size, padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.act2 = nn.GELU()
        self.drop2 = nn.Dropout(dropout)
        self.residual = nn.Conv1d(in_channels, out_channels, kernel_size=1) if in_channels != out_channels else nn.Identity()
        self.output_act = nn.GELU()

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        residual = self.residual(tensor)
        out = self.drop1(self.act1(self.chomp1(self.conv1(tensor))))
        out = self.drop2(self.act2(self.chomp2(self.conv2(out))))
        return self.output_act(out + residual)


class TemporalEncoder(nn.Module):
    def __init__(self, feature_dim: int, config: TrainConfig):
        super().__init__()
        self.input_norm = nn.LayerNorm(feature_dim)
        blocks = []
        in_channels = feature_dim
        for level, out_channels in enumerate(config.channels):
            blocks.append(
                ResidualTemporalBlock(
                    in_channels=in_channels,
                    out_channels=out_channels,
                    kernel_size=config.kernel_size,
                    dilation=2 ** level,
                    dropout=config.dropout,
                )
            )
            in_channels = out_channels
        self.blocks = nn.ModuleList(blocks)
        self.output_norm = nn.LayerNorm(in_channels)
        self.output_dim = in_channels

    def forward(self, market_sequences: torch.Tensor) -> torch.Tensor:
        tensor = self.input_norm(market_sequences).transpose(1, 2)
        for block in self.blocks:
            tensor = block(tensor)
        return self.output_norm(tensor[:, :, -1])


class FrontierUtilityModel(nn.Module):
    def __init__(self, market_dim: int, account_dim: int, config: TrainConfig):
        super().__init__()
        self.encoder = TemporalEncoder(market_dim, config)
        self.account_tower = nn.Sequential(
            nn.LayerNorm(account_dim),
            nn.Linear(account_dim, config.hidden_dim),
            nn.GELU(),
            nn.Dropout(config.dropout),
        )
        merged_dim = self.encoder.output_dim + config.hidden_dim
        self.trunk = nn.Sequential(
            nn.Linear(merged_dim, config.hidden_dim),
            nn.GELU(),
            nn.Dropout(config.dropout),
        )
        self.setup_head = nn.Linear(config.hidden_dim, len(SETUPS))
        self.utility_head = nn.Linear(config.hidden_dim, len(UTILITY_TARGET_COLUMNS))

    def forward(self, market_sequences: torch.Tensor, account_features: torch.Tensor) -> Dict[str, torch.Tensor]:
        market_state = self.encoder(market_sequences)
        account_state = self.account_tower(account_features)
        trunk = self.trunk(torch.cat([market_state, account_state], dim=1))
        setup_logits = self.setup_head(trunk)
        utility_outputs = self.utility_head(trunk)
        return {
            "setup_logits": setup_logits,
            "setup_probs": torch.sigmoid(setup_logits),
            "utility_outputs": utility_outputs,
        }


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def market_session_for_row(row: pd.Series) -> str:
    if float(row.get("is_asia_session", 0.0)) >= 0.5:
        return "asia"
    if float(row.get("is_europe_session", 0.0)) >= 0.5:
        return "europe"
    return "us"


def session_phase_for_progress(progress: float) -> str:
    if progress < 0.2:
        return "opening_0_20"
    if progress < 0.4:
        return "build_20_40"
    if progress < 0.6:
        return "mid_40_60"
    if progress < 0.8:
        return "late_60_80"
    return "close_80_100"


def load_dataset(path: Path) -> pd.DataFrame:
    usecols = list(dict.fromkeys(BASE_COLUMNS + ALL_FEATURE_COLUMNS + LABEL_COLUMNS + UTILITY_TARGET_COLUMNS + UTILITY_SETUP_COLUMNS + [
        "setup_label",
        "account_stage",
        "model_sample_eligible",
        "utility_best_setup",
        "utility_best_setup_r",
        "trade_realized_pnl_r",
        "trade_realized_pnl_cash",
        "trade_reference_taken",
        "trade_passed",
    ]))
    int32_columns = {
        "segment_id",
        "bar_index_in_segment",
        "bars_remaining_in_segment",
        "account_profitable_days_so_far",
        "account_profitable_days_remaining",
        "account_days_elapsed",
        "trades_taken_today",
        "trade_slots_remaining_today",
        "win_streak",
        "loss_streak",
        "trade_reference_taken",
        "trade_passed",
    }
    excluded_columns = {"timestamp", "session_date_utc", "setup_label", "utility_best_setup", "account_stage"}
    dtype_map: Dict[str, object] = {}
    for column in usecols:
        if column in excluded_columns:
            continue
        if column == "model_sample_eligible":
            dtype_map[column] = "int8"
        elif column in int32_columns:
            dtype_map[column] = "int32"
        else:
            dtype_map[column] = "float32"
    frame = pd.read_csv(path, compression="gzip", usecols=usecols, dtype=dtype_map)
    numeric_columns = [col for col in frame.columns if col not in excluded_columns]
    for column in numeric_columns:
        if column == "model_sample_eligible":
            frame[column] = frame[column].fillna(0).astype(bool)
        elif column in int32_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(np.int32)
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(np.float32)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["session_date_utc"] = pd.to_datetime(frame["session_date_utc"]).dt.date
    frame = frame.copy()
    frame["market_session"] = frame.apply(market_session_for_row, axis=1)
    frame["session_phase"] = frame["session_progress"].map(session_phase_for_progress)
    frame = frame.sort_values(["timestamp"]).reset_index(drop=True)
    return frame


def build_masks(frame: pd.DataFrame, train_fraction: float, val_fraction: float) -> Dict[str, np.ndarray]:
    segment_order = frame[["segment_id"]].drop_duplicates().reset_index(drop=True)
    segment_ids = segment_order["segment_id"].to_numpy()
    n_segments = len(segment_ids)
    train_cut = int(n_segments * train_fraction)
    val_cut = int(n_segments * (train_fraction + val_fraction))
    train_segments = set(segment_ids[:train_cut].tolist())
    val_segments = set(segment_ids[train_cut:val_cut].tolist())
    test_segments = set(segment_ids[val_cut:].tolist())
    return {
        "train": frame["segment_id"].isin(train_segments).to_numpy(),
        "val": frame["segment_id"].isin(val_segments).to_numpy(),
        "test": frame["segment_id"].isin(test_segments).to_numpy(),
    }


def fill_and_standardize(frame: pd.DataFrame, train_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, Dict[str, float]]]:
    market = frame[MARKET_FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    account = frame[ACCOUNT_COLUMNS].replace([np.inf, -np.inf], np.nan)
    market_means = market.loc[train_mask].mean(axis=0)
    market_stds = market.loc[train_mask].std(axis=0).replace(0.0, 1.0)
    account_means = account.loc[train_mask].mean(axis=0)
    account_stds = account.loc[train_mask].std(axis=0).replace(0.0, 1.0)
    market = ((market.fillna(market_means) - market_means) / market_stds).fillna(0.0)
    account = ((account.fillna(account_means) - account_means) / account_stds).fillna(0.0)
    standardization = {
        "market_means": {col: round(float(market_means[col]), 10) for col in MARKET_FEATURE_COLUMNS},
        "market_stds": {col: round(float(market_stds[col]), 10) for col in MARKET_FEATURE_COLUMNS},
        "account_means": {col: round(float(account_means[col]), 10) for col in ACCOUNT_COLUMNS},
        "account_stds": {col: round(float(account_stds[col]), 10) for col in ACCOUNT_COLUMNS},
    }
    return market.to_numpy(np.float32), account.to_numpy(np.float32), standardization


def build_sequence_indices(frame: pd.DataFrame, candidate_mask: np.ndarray, lookback: int) -> np.ndarray:
    bar_index = frame["bar_index_in_segment"].to_numpy()
    end_indices = np.flatnonzero(candidate_mask & (bar_index >= lookback - 1))
    if len(end_indices) == 0:
        return end_indices
    segment_ids = frame["segment_id"].to_numpy()
    start_indices = end_indices - lookback + 1
    same_segment = segment_ids[start_indices] == segment_ids[end_indices]
    return end_indices[same_segment]


def cap_indices(indices: np.ndarray, max_samples: int, seed: int, randomize: bool) -> np.ndarray:
    if max_samples <= 0 or len(indices) <= max_samples:
        return indices
    if randomize:
        rng = np.random.default_rng(seed)
        sampled = rng.choice(indices, size=max_samples, replace=False)
        return np.sort(sampled)
    return indices[:max_samples]


def make_dataset(frame: pd.DataFrame, market_features: np.ndarray, account_features: np.ndarray, indices: np.ndarray, lookback: int) -> SequenceDataset:
    setup_targets = frame[LABEL_COLUMNS].fillna(0.0).to_numpy(np.float32)
    utility_targets = frame[UTILITY_TARGET_COLUMNS].fillna(0.0).to_numpy(np.float32)
    return SequenceDataset(
        market_features=market_features,
        account_features=account_features,
        setup_targets=setup_targets,
        utility_targets=utility_targets,
        end_indices=indices,
        lookback=lookback,
    )


def pairwise_ranking_loss(predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if predictions.shape[0] < 2:
        return predictions.new_tensor(0.0)
    diff_pred = predictions.unsqueeze(1) - predictions.unsqueeze(0)
    diff_target = targets.unsqueeze(1) - targets.unsqueeze(0)
    mask = diff_target.abs() > 1e-6
    if not torch.any(mask):
        return predictions.new_tensor(0.0)
    desired = torch.sign(diff_target[mask])
    return torch.mean(torch.relu(0.05 - desired * diff_pred[mask]))


def mean_average_precision(labels: np.ndarray, probs: np.ndarray) -> float:
    scores = []
    for idx in range(labels.shape[1]):
        if np.sum(labels[:, idx]) == 0:
            continue
        scores.append(average_precision_score(labels[:, idx], probs[:, idx]))
    return float(np.mean(scores)) if scores else 0.0


def mean_roc_auc(labels: np.ndarray, probs: np.ndarray) -> float:
    scores = []
    for idx in range(labels.shape[1]):
        if np.sum(labels[:, idx]) == 0 or np.sum(labels[:, idx]) == len(labels[:, idx]):
            continue
        scores.append(roc_auc_score(labels[:, idx], probs[:, idx]))
    return float(np.mean(scores)) if scores else 0.0


def train_epoch(model: FrontierUtilityModel, loader: DataLoader, optimizer: torch.optim.Optimizer, pos_weight: torch.Tensor, config: TrainConfig, device: torch.device) -> Dict[str, float]:
    model.train()
    total_loss = 0.0
    all_probs = []
    all_labels = []
    bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    huber = nn.HuberLoss()
    for market_features, account_features, setup_targets, utility_targets, _ in loader:
        market_features = market_features.to(device)
        account_features = account_features.to(device)
        setup_targets = setup_targets.to(device)
        utility_targets = utility_targets.to(device)
        outputs = model(market_features, account_features)
        setup_loss = bce(outputs["setup_logits"], setup_targets)
        utility_loss = huber(outputs["utility_outputs"][:, 0], utility_targets[:, 0])
        challenge_pass_loss = huber(outputs["utility_outputs"][:, 1:4], utility_targets[:, 1:4])
        challenge_fail_loss = huber(outputs["utility_outputs"][:, 4:6], utility_targets[:, 4:6])
        challenge_resolution_loss = huber(outputs["utility_outputs"][:, 6], utility_targets[:, 6])
        challenge_distance_loss = huber(outputs["utility_outputs"][:, 7], utility_targets[:, 7])
        challenge_budget_loss = huber(outputs["utility_outputs"][:, 8:10], utility_targets[:, 8:10])
        funded_return_loss = huber(outputs["utility_outputs"][:, 10:12], utility_targets[:, 10:12])
        funded_risk_loss = huber(outputs["utility_outputs"][:, 12:14], utility_targets[:, 12:14])
        funded_drawdown_loss = huber(outputs["utility_outputs"][:, 14], utility_targets[:, 14])
        funded_payout_loss = huber(outputs["utility_outputs"][:, 15], utility_targets[:, 15])
        ranking_loss = pairwise_ranking_loss(outputs["utility_outputs"][:, 0], utility_targets[:, 0])
        loss = (
            config.setup_loss_weight * setup_loss
            + config.utility_loss_weight * utility_loss
            + config.challenge_pass_loss_weight * challenge_pass_loss
            + config.challenge_fail_loss_weight * challenge_fail_loss
            + config.challenge_resolution_loss_weight * challenge_resolution_loss
            + config.challenge_distance_loss_weight * challenge_distance_loss
            + config.challenge_budget_loss_weight * challenge_budget_loss
            + config.funded_return_loss_weight * funded_return_loss
            + config.funded_risk_loss_weight * funded_risk_loss
            + config.funded_drawdown_loss_weight * funded_drawdown_loss
            + config.funded_payout_loss_weight * funded_payout_loss
            + config.ranking_loss_weight * ranking_loss
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += float(loss.item()) * len(market_features)
        all_probs.append(outputs["setup_probs"].detach().cpu().numpy())
        all_labels.append(setup_targets.detach().cpu().numpy())
    probs = np.concatenate(all_probs, axis=0)
    labels = np.concatenate(all_labels, axis=0)
    return {
        "loss": total_loss / len(loader.dataset),
        "mean_average_precision": mean_average_precision(labels, probs),
    }


@torch.no_grad()
def predict(model: FrontierUtilityModel, loader: DataLoader, device: torch.device) -> Dict[str, np.ndarray]:
    model.eval()
    outputs = {"setup_probs": [], "utility_outputs": [], "end_indices": []}
    labels = []
    utility_targets = []
    for market_features, account_features, batch_labels, batch_utility, end_indices in loader:
        market_features = market_features.to(device)
        account_features = account_features.to(device)
        pred = model(market_features, account_features)
        outputs["setup_probs"].append(pred["setup_probs"].cpu().numpy())
        outputs["utility_outputs"].append(pred["utility_outputs"].cpu().numpy())
        outputs["end_indices"].append(end_indices.numpy())
        labels.append(batch_labels.numpy())
        utility_targets.append(batch_utility.numpy())
    packed = {name: np.concatenate(parts, axis=0) for name, parts in outputs.items()}
    packed["labels"] = np.concatenate(labels, axis=0)
    packed["utility_targets"] = np.concatenate(utility_targets, axis=0)
    return packed


def summarize_predictions(predictions: Dict[str, np.ndarray]) -> Dict[str, float]:
    setup_probs = predictions["setup_probs"]
    setup_labels = predictions["labels"]
    utility_pred = predictions["utility_outputs"][:, 0]
    utility_target = predictions["utility_targets"][:, 0]
    utility_mae = float(np.mean(np.abs(utility_pred - utility_target)))
    pred_std = float(np.std(utility_pred))
    target_std = float(np.std(utility_target))
    if len(utility_pred) > 1 and pred_std > 1e-12 and target_std > 1e-12:
        pred_centered = utility_pred - float(np.mean(utility_pred))
        target_centered = utility_target - float(np.mean(utility_target))
        denom = float(np.sqrt(np.sum(pred_centered ** 2) * np.sum(target_centered ** 2)))
        corr = float(np.sum(pred_centered * target_centered) / denom) if denom > 1e-12 else 0.0
    else:
        corr = 0.0
    if not np.isfinite(corr):
        corr = 0.0
    return {
        "mean_average_precision": mean_average_precision(setup_labels, setup_probs),
        "mean_roc_auc": mean_roc_auc(setup_labels, setup_probs),
        "utility_mae": utility_mae,
        "utility_correlation": corr,
    }


def save_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_candidates(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with gzip.open(path, "wt", newline="") as handle:
        pd.DataFrame(rows).to_csv(handle, index=False)


def _challenge_score_from_outputs(utility_outputs: np.ndarray) -> np.ndarray:
    return (
        1.10 * utility_outputs[:, 0]
        + 1.40 * utility_outputs[:, 1]
        + 1.00 * utility_outputs[:, 2]
        + 0.60 * utility_outputs[:, 3]
        - 1.20 * utility_outputs[:, 4]
        - 0.80 * utility_outputs[:, 5]
        - 0.08 * utility_outputs[:, 6]
        + 0.25 * utility_outputs[:, 7]
        - 0.08 * utility_outputs[:, 8]
        - 0.05 * utility_outputs[:, 9]
    )


def _funded_score_from_outputs(utility_outputs: np.ndarray) -> np.ndarray:
    return (
        0.50 * utility_outputs[:, 0]
        + 0.80 * utility_outputs[:, 10]
        + 1.20 * utility_outputs[:, 11]
        - 0.90 * utility_outputs[:, 12]
        - 1.25 * utility_outputs[:, 13]
        - 0.60 * utility_outputs[:, 14]
        + 0.90 * utility_outputs[:, 15]
    )


def build_candidate_rows(frame: pd.DataFrame, predictions: Dict[str, np.ndarray], split: str) -> List[Dict[str, object]]:
    end_indices = predictions["end_indices"].astype(int)
    setup_probs = predictions["setup_probs"]
    utility_outputs = predictions["utility_outputs"]
    challenge_scores = _challenge_score_from_outputs(utility_outputs)
    funded_scores = _funded_score_from_outputs(utility_outputs)
    rows: List[Dict[str, object]] = []
    for local_idx, frame_idx in enumerate(end_indices):
        row = frame.iloc[int(frame_idx)]
        probs = setup_probs[local_idx]
        best_setup_idx = int(np.argmax(probs))
        account_stage = str(row.get("account_stage", "challenge"))
        frontier_score = funded_scores[local_idx] if account_stage == "funded" else challenge_scores[local_idx]
        rows.append(
            {
                "split": split,
                "timestamp": row["timestamp"].isoformat(),
                "session_date_utc": str(row["session_date_utc"]),
                "segment_id": int(row["segment_id"]),
                "bar_index_in_segment": int(row["bar_index_in_segment"]),
                "bars_remaining_in_segment": int(row["bars_remaining_in_segment"]),
                "close": float(row["close"]),
                "atr_14": float(row["atr_14"]),
                "market_session": row["market_session"],
                "session_phase": row["session_phase"],
                "account_stage": account_stage,
                "model_sample_eligible": bool(row["model_sample_eligible"]),
                "chosen_setup": SETUPS[best_setup_idx],
                "probability": round(float(probs[best_setup_idx]), 6),
                "predicted_trade_utility": round(float(utility_outputs[local_idx, 0]), 6),
                "predicted_challenge_pass_prob_5d": round(float(utility_outputs[local_idx, 1]), 6),
                "predicted_challenge_pass_prob_10d": round(float(utility_outputs[local_idx, 2]), 6),
                "predicted_challenge_pass_prob_20d": round(float(utility_outputs[local_idx, 3]), 6),
                "predicted_challenge_fail_prob_5d": round(float(utility_outputs[local_idx, 4]), 6),
                "predicted_challenge_fail_prob_10d": round(float(utility_outputs[local_idx, 5]), 6),
                "predicted_challenge_expected_days_to_resolution": round(float(utility_outputs[local_idx, 6]), 6),
                "predicted_challenge_distance_to_target_delta": round(float(utility_outputs[local_idx, 7]), 6),
                "predicted_challenge_daily_loss_budget_consumption": round(float(utility_outputs[local_idx, 8]), 6),
                "predicted_challenge_total_drawdown_budget_consumption": round(float(utility_outputs[local_idx, 9]), 6),
                "predicted_funded_expected_return_5d": round(float(utility_outputs[local_idx, 10]), 6),
                "predicted_funded_expected_return_20d": round(float(utility_outputs[local_idx, 11]), 6),
                "predicted_funded_breach_risk_5d": round(float(utility_outputs[local_idx, 12]), 6),
                "predicted_funded_breach_risk_20d": round(float(utility_outputs[local_idx, 13]), 6),
                "predicted_funded_expected_drawdown": round(float(utility_outputs[local_idx, 14]), 6),
                "predicted_funded_expected_payout_growth": round(float(utility_outputs[local_idx, 15]), 6),
                "predicted_frontier_score": round(float(frontier_score), 6),
                "utility_best_setup": row.get("utility_best_setup", "none"),
                "trade_challenge_utility": round(float(row["trade_challenge_utility"]), 6),
                "trade_realized_pnl_r": round(float(row["trade_realized_pnl_r"]), 6),
                "trade_realized_pnl_cash": round(float(row.get("trade_realized_pnl_cash", 0.0)), 6),
                "trade_reference_taken": int(row.get("trade_reference_taken", 0)),
                "trade_passed": int(row.get("trade_passed", 0)),
                "account_drawdown_pct": round(float(row["account_drawdown_pct"]), 6),
                "account_distance_to_target_pct": round(float(row["account_distance_to_target_pct"]), 6),
                "account_profitable_days_remaining": int(row["account_profitable_days_remaining"]),
            }
        )
    return rows


def run_train(args: argparse.Namespace) -> int:
    set_seed(args.seed)
    dataset_path = Path(args.dataset).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    config = TrainConfig(
        lookback=args.lookback,
        batch_size=args.batch_size,
        epochs=args.epochs,
        hidden_dim=args.hidden_dim,
        kernel_size=args.kernel_size,
        channels=tuple(args.channels),
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        seed=args.seed,
    )
    frame = load_dataset(dataset_path)
    masks = build_masks(frame, config.train_fraction, config.val_fraction)
    market_features, account_features, standardization = fill_and_standardize(frame, masks["train"])
    train_indices = build_sequence_indices(frame, masks["train"] & frame["model_sample_eligible"].to_numpy(), config.lookback)
    val_indices = build_sequence_indices(frame, masks["val"] & frame["model_sample_eligible"].to_numpy(), config.lookback)
    test_indices = build_sequence_indices(frame, masks["test"] & frame["model_sample_eligible"].to_numpy(), config.lookback)
    train_indices = cap_indices(train_indices, config.max_train_samples, config.seed, True)
    val_indices = cap_indices(val_indices, config.max_eval_samples, config.seed, False)
    test_indices = cap_indices(test_indices, config.max_eval_samples, config.seed, False)
    if len(train_indices) == 0 or len(val_indices) == 0 or len(test_indices) == 0:
        raise ValueError("Empty split after sequence-safe filtering.")
    train_dataset = make_dataset(frame, market_features, account_features, train_indices, config.lookback)
    val_dataset = make_dataset(frame, market_features, account_features, val_indices, config.lookback)
    test_dataset = make_dataset(frame, market_features, account_features, test_indices, config.lookback)
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
    eval_loader_kwargs = {"batch_size": config.batch_size, "shuffle": False, "drop_last": False}
    val_loader = DataLoader(val_dataset, **eval_loader_kwargs)
    test_loader = DataLoader(test_dataset, **eval_loader_kwargs)
    device = torch.device(args.device)
    model = FrontierUtilityModel(len(MARKET_FEATURE_COLUMNS), len(ACCOUNT_COLUMNS), config).to(device)
    setup_targets = frame[LABEL_COLUMNS].fillna(0.0).to_numpy(np.float32)
    label_sums = setup_targets[train_indices].sum(axis=0)
    negative_sums = len(train_indices) - label_sums
    pos_weight = torch.tensor(np.maximum(negative_sums / np.maximum(label_sums, 1.0), 1.0), dtype=torch.float32, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    history = []
    best_state = None
    best_val_score = -float("inf")
    for epoch in range(1, config.epochs + 1):
        train_metrics = train_epoch(model, train_loader, optimizer, pos_weight, config, device)
        val_predictions = predict(model, val_loader, device)
        val_metrics = summarize_predictions(val_predictions)
        history.append(
            {
                "epoch": epoch,
                "train_loss": round(train_metrics["loss"], 6),
                "train_mean_average_precision": round(train_metrics["mean_average_precision"], 6),
                "val_mean_average_precision": round(val_metrics["mean_average_precision"], 6),
                "val_mean_roc_auc": round(val_metrics["mean_roc_auc"], 6),
                "val_utility_mae": round(val_metrics["utility_mae"], 6),
                "val_utility_correlation": round(val_metrics["utility_correlation"], 6),
            }
        )
        frontier_score = val_metrics["utility_correlation"] - val_metrics["utility_mae"]
        if frontier_score > best_val_score:
            best_val_score = frontier_score
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    val_predictions = predict(model, val_loader, device)
    test_predictions = predict(model, test_loader, device)
    val_metrics = summarize_predictions(val_predictions)
    test_metrics = summarize_predictions(test_predictions)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "train_config": asdict(config),
            "market_feature_columns": MARKET_FEATURE_COLUMNS,
            "account_feature_columns": ACCOUNT_COLUMNS,
            "utility_target_columns": UTILITY_TARGET_COLUMNS,
            "label_columns": LABEL_COLUMNS,
            "standardization": standardization,
        },
        artifacts_dir / "model.pt",
    )
    training_summary = {
        "dataset": str(dataset_path),
        "artifacts_dir": str(artifacts_dir),
        "train_config": asdict(config),
        "model_reports": {
            "frontier_utility_model": {
                "feature_columns": MARKET_FEATURE_COLUMNS + ACCOUNT_COLUMNS,
            }
        },
        "dataset_rows": int(len(frame)),
        "sequence_rows": {"train": int(len(train_indices)), "val": int(len(val_indices)), "test": int(len(test_indices))},
        "history": history,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "architecture": {
            "encoder": "causal_tcn_plus_account_tower",
            "channels": list(config.channels),
            "kernel_size": config.kernel_size,
            "lookback": config.lookback,
            "utility_targets": UTILITY_TARGET_COLUMNS,
        },
        "notes": [
            "Primary model ranking uses utility correlation minus utility MAE on validation.",
            "Setup heads are auxiliary and preserved for interpretability.",
            "This training path is source-level and independent from the cached specialist wrapper.",
            "Utility outputs are the primary decision surface; setup probabilities remain auxiliary routing signals.",
        ],
    }
    save_json(artifacts_dir / "training_summary.json", training_summary)
    return 0


def run_score(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    checkpoint = torch.load(artifacts_dir / "model.pt", map_location="cpu")
    config = TrainConfig(**checkpoint["train_config"])
    frame = load_dataset(dataset_path)
    masks = build_masks(frame, config.train_fraction, config.val_fraction)
    market_features, account_features, _ = fill_and_standardize(frame, masks["train"])
    split_mask = masks[args.split] & frame["model_sample_eligible"].to_numpy()
    indices = build_sequence_indices(frame, split_mask, config.lookback)
    indices = cap_indices(indices, config.max_eval_samples, config.seed, False)
    dataset = make_dataset(frame, market_features, account_features, indices, config.lookback)
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=False, drop_last=False)
    device = torch.device(args.device)
    model = FrontierUtilityModel(len(MARKET_FEATURE_COLUMNS), len(ACCOUNT_COLUMNS), config).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    predictions = predict(model, loader, device)
    candidates = build_candidate_rows(frame, predictions, args.split)
    output_path = Path(args.output)
    save_candidates(output_path, candidates)
    candidate_frame = pd.DataFrame(candidates)
    analysis_payload = {
        "dataset": str(dataset_path),
        "artifacts_dir": str(artifacts_dir),
        "split": args.split,
        "candidates": int(len(candidates)),
        "prediction_summary": summarize_predictions(predictions),
        "frontier_score_summary": {
            "mean": round(float(candidate_frame["predicted_frontier_score"].mean()), 6) if len(candidate_frame) else 0.0,
            "median": round(float(candidate_frame["predicted_frontier_score"].median()), 6) if len(candidate_frame) else 0.0,
            "positive_rate": round(float((candidate_frame["predicted_frontier_score"] > 0.0).mean()), 6) if len(candidate_frame) else 0.0,
        },
        "account_stage_counts": candidate_frame["account_stage"].value_counts(dropna=False).to_dict() if len(candidate_frame) else {},
    }
    if args.analysis_output:
        save_json(Path(args.analysis_output), analysis_payload)
    print(output_path)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Frontier utility model training and scoring.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    train = subparsers.add_parser("train", help="Train the frontier utility model.")
    train.add_argument("--dataset", required=True)
    train.add_argument("--artifacts-dir", required=True)
    train.add_argument("--device", default="cpu")
    train.add_argument("--lookback", type=int, default=96)
    train.add_argument("--epochs", type=int, default=6)
    train.add_argument("--batch-size", type=int, default=256)
    train.add_argument("--hidden-dim", type=int, default=128)
    train.add_argument("--kernel-size", type=int, default=3)
    train.add_argument("--channels", nargs="+", type=int, default=[64, 64, 96])
    train.add_argument("--max-train-samples", type=int, default=0)
    train.add_argument("--max-eval-samples", type=int, default=0)
    train.add_argument("--seed", type=int, default=7)
    train.set_defaults(func=run_train)

    score = subparsers.add_parser("score", help="Score a dataset split into replay candidates.")
    score.add_argument("--dataset", required=True)
    score.add_argument("--artifacts-dir", required=True)
    score.add_argument("--output", required=True)
    score.add_argument("--analysis-output")
    score.add_argument("--split", default="test", choices=["train", "val", "test"])
    score.add_argument("--device", default="cpu")
    score.set_defaults(func=run_score)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
