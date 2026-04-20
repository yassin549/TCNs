import argparse
import gzip
import json
import math
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

from prop_firm_rules import (
    FUNDEDHIVE_POLICY,
    evaluate_propfirm_path,
    fundedhive_backtest_defaults,
    policy_metadata,
)


SETUPS = [
    "long_reversal",
    "long_continuation",
    "short_reversal",
    "short_continuation",
]
LABEL_COLUMNS = [f"label_{name}" for name in SETUPS]
LONG_SETUPS = {"long_reversal", "long_continuation"}
SHORT_SETUPS = {"short_reversal", "short_continuation"}

FEATURE_COLUMNS = [
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

CONTEXT_COLUMNS = [
    "session_progress",
    "bars_remaining_pct",
    "session_range_pos",
    "session_range_atr",
    "distance_to_session_high_atr",
    "distance_to_session_low_atr",
    "session_open_return_atr",
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


@dataclass
class TrainConfig:
    train_fraction: float = 0.70
    val_fraction: float = 0.15
    lookback: int = 96
    batch_size: int = 256
    epochs: int = 8
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    dropout: float = 0.15
    hidden_dim: int = 128
    trunk_dim: int = 128
    gate_hidden_dim: int = 64
    kernel_size: int = 3
    channels: Tuple[int, ...] = (64, 64, 96)
    top_k: int = 2
    train_negative_ratio: float = 4.0
    utility_margin: float = 0.15
    gate_alignment_weight: float = 0.40
    load_balance_weight: float = 0.02
    utility_weight: float = 0.60
    action_value_weight: float = 0.40
    specialization_weight: float = 0.30
    round_trip_cost_points: float = 1.50
    target_atr_multiple: float = 1.25
    stop_atr_multiple: float = 0.75
    session_end_buffer_bars: int = 60
    max_train_samples: int = 0
    max_eval_samples: int = 0
    seed: int = 7

    def __post_init__(self):
        self.channels = tuple(int(channel) for channel in self.channels)
        if self.lookback < 2:
            raise ValueError("lookback must be at least 2 bars.")
        if self.kernel_size < 2:
            raise ValueError("kernel_size must be at least 2.")
        if self.top_k < 1 or self.top_k > len(SETUPS):
            raise ValueError("top_k must be between 1 and the number of setups.")


@dataclass
class BacktestConfig:
    target_atr_multiple: float = 1.25
    stop_atr_multiple: float = 0.75
    horizon_bars: int = 30
    session_end_buffer_bars: int = 60
    cooldown_bars: int = 5
    max_trades_per_day: int = 6
    policy_name: str = FUNDEDHIVE_POLICY.name
    max_daily_loss_pct: float = FUNDEDHIVE_POLICY.max_daily_loss_pct
    max_total_drawdown_pct: float = FUNDEDHIVE_POLICY.max_total_drawdown_pct
    profit_target_pct: float = FUNDEDHIVE_POLICY.profit_target_pct
    min_profitable_days: int = FUNDEDHIVE_POLICY.min_profitable_days
    max_loss_per_trade_pct: float = FUNDEDHIVE_POLICY.max_loss_per_trade_pct
    drawdown_type: str = FUNDEDHIVE_POLICY.drawdown_type
    stop_loss_required: bool = FUNDEDHIVE_POLICY.stop_loss_required
    starting_balance: float = 100_000.0
    round_trip_cost_points: float = 1.50
    risk_per_trade_pct: float = 0.50
    dynamic_risk: bool = False
    min_risk_pct: float = 0.50
    max_risk_pct: float = 0.50
    utility_scale: float = 1.0
    urgency_weight: float = 0.0
    drawdown_safety_weight: float = 0.0


class SequenceDataset(Dataset):
    def __init__(
        self,
        features: np.ndarray,
        contexts: np.ndarray,
        labels: np.ndarray,
        utility_targets: np.ndarray,
        action_targets: np.ndarray,
        end_indices: np.ndarray,
        lookback: int,
    ):
        self.features = torch.from_numpy(np.ascontiguousarray(features.astype(np.float32)))
        self.contexts = torch.from_numpy(np.ascontiguousarray(contexts.astype(np.float32)))
        self.labels = torch.from_numpy(np.ascontiguousarray(labels.astype(np.float32)))
        self.utility_targets = torch.from_numpy(
            np.ascontiguousarray(utility_targets.astype(np.float32))
        )
        self.action_targets = torch.from_numpy(
            np.ascontiguousarray(action_targets.astype(np.float32))
        )
        self.end_indices = np.ascontiguousarray(end_indices.astype(np.int64))
        self.lookback = int(lookback)

    def __len__(self):
        return int(len(self.end_indices))

    def __getitem__(self, idx):
        end_idx = int(self.end_indices[idx])
        start_idx = end_idx - self.lookback + 1
        return (
            self.features[start_idx : end_idx + 1],
            self.contexts[end_idx],
            self.labels[end_idx],
            self.utility_targets[end_idx],
            self.action_targets[end_idx],
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
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ):
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size,
            padding=padding,
            dilation=dilation,
        )
        self.chomp1 = Chomp1d(padding)
        self.act1 = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(
            out_channels,
            out_channels,
            kernel_size,
            padding=padding,
            dilation=dilation,
        )
        self.chomp2 = Chomp1d(padding)
        self.act2 = nn.GELU()
        self.drop2 = nn.Dropout(dropout)
        self.residual = (
            nn.Conv1d(in_channels, out_channels, kernel_size=1)
            if in_channels != out_channels
            else nn.Identity()
        )
        self.output_act = nn.GELU()

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        residual = self.residual(tensor)
        out = self.conv1(tensor)
        out = self.chomp1(out)
        out = self.act1(out)
        out = self.drop1(out)
        out = self.conv2(out)
        out = self.chomp2(out)
        out = self.act2(out)
        out = self.drop2(out)
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
                    dilation=2**level,
                    dropout=config.dropout,
                )
            )
            in_channels = out_channels
        self.blocks = nn.ModuleList(blocks)
        self.output_norm = nn.LayerNorm(in_channels)
        self.output_dim = in_channels

    def forward(self, feature_sequences: torch.Tensor) -> torch.Tensor:
        tensor = self.input_norm(feature_sequences).transpose(1, 2)
        for block in self.blocks:
            tensor = block(tensor)
        return self.output_norm(tensor[:, :, -1])


class ExpertHead(nn.Module):
    def __init__(self, trunk_dim: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.body = nn.Sequential(
            nn.Linear(trunk_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.logit = nn.Linear(hidden_dim, 1)
        self.utility = nn.Linear(hidden_dim, 1)

    def forward(self, trunk_state: torch.Tensor):
        hidden = self.body(trunk_state)
        return self.logit(hidden).squeeze(-1), self.utility(hidden).squeeze(-1)


class LearnedMoE(nn.Module):
    def __init__(self, feature_dim: int, context_dim: int, config: TrainConfig):
        super().__init__()
        self.top_k = config.top_k
        self.encoder = TemporalEncoder(feature_dim, config)
        self.trunk = nn.Sequential(
            nn.Linear(self.encoder.output_dim, config.trunk_dim),
            nn.GELU(),
            nn.Dropout(config.dropout),
        )
        self.gate = nn.Sequential(
            nn.LayerNorm(config.trunk_dim + context_dim),
            nn.Linear(config.trunk_dim + context_dim, config.gate_hidden_dim),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.gate_hidden_dim, len(SETUPS)),
        )
        self.experts = nn.ModuleList(
            [ExpertHead(config.trunk_dim, config.hidden_dim, config.dropout) for _ in SETUPS]
        )

    def _topk_gate(self, gate_logits: torch.Tensor) -> torch.Tensor:
        topk_values, topk_idx = torch.topk(gate_logits, k=self.top_k, dim=1)
        sparse_weights = torch.softmax(topk_values, dim=1)
        gate_weights = torch.zeros_like(gate_logits)
        gate_weights.scatter_(1, topk_idx, sparse_weights)
        return gate_weights

    def forward(self, feature_sequences: torch.Tensor, contexts: torch.Tensor) -> Dict[str, torch.Tensor]:
        encoded_state = self.encoder(feature_sequences)
        trunk_state = self.trunk(encoded_state)
        gate_logits = self.gate(torch.cat([trunk_state, contexts], dim=1))
        gate_weights = self._topk_gate(gate_logits)

        expert_logits = []
        expert_utilities = []
        for expert in self.experts:
            logit, utility = expert(trunk_state)
            expert_logits.append(logit)
            expert_utilities.append(utility)

        expert_logits = torch.stack(expert_logits, dim=1)
        expert_probs = torch.sigmoid(expert_logits)
        expert_utilities = torch.stack(expert_utilities, dim=1)
        routed_utilities = gate_weights * expert_utilities
        action_value = torch.max(routed_utilities, dim=1).values
        return {
            "gate_logits": gate_logits,
            "gate_weights": gate_weights,
            "expert_logits": expert_logits,
            "expert_probs": expert_probs,
            "expert_utilities": expert_utilities,
            "routed_utilities": routed_utilities,
            "action_value": action_value,
        }


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def build_masks(
    frame: pd.DataFrame,
    train_fraction: float,
    val_fraction: float,
) -> Dict[str, np.ndarray]:
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


def market_session_for_row(row: pd.Series) -> str:
    if row["is_asia_session"] >= 0.5:
        return "asia"
    if row["is_europe_session"] >= 0.5:
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
    usecols = BASE_COLUMNS + FEATURE_COLUMNS + CONTEXT_COLUMNS + LABEL_COLUMNS + [
        "setup_label",
        "model_sample_eligible",
        "is_asia_session",
        "is_europe_session",
        "is_us_session",
        "session_progress",
    ]
    usecols = list(dict.fromkeys(usecols))
    frame = pd.read_csv(path, compression="gzip", usecols=usecols)
    numeric_columns = [
        column
        for column in frame.columns
        if column not in {"timestamp", "session_date_utc", "setup_label"}
    ]
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    frame[LABEL_COLUMNS] = frame[LABEL_COLUMNS].astype(bool)
    frame["model_sample_eligible"] = frame["model_sample_eligible"].astype(bool)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["market_session"] = frame.apply(market_session_for_row, axis=1)
    frame["session_phase"] = frame["session_progress"].map(session_phase_for_progress)
    frame = frame.sort_values(["timestamp"]).reset_index(drop=True)
    return frame


def fill_and_standardize(
    frame: pd.DataFrame,
    train_mask: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Dict[str, float]]]:
    feature_frame = frame[FEATURE_COLUMNS].copy()
    feature_frame = feature_frame.replace([np.inf, -np.inf], np.nan)
    feature_means = feature_frame.loc[train_mask].mean(axis=0)
    feature_stds = feature_frame.loc[train_mask].std(axis=0).replace(0.0, 1.0)
    feature_frame = feature_frame.fillna(feature_means)
    feature_frame = (feature_frame - feature_means) / feature_stds
    feature_frame = feature_frame.fillna(0.0)

    context_frame = frame[CONTEXT_COLUMNS].copy()
    context_frame = context_frame.replace([np.inf, -np.inf], np.nan)
    context_means = context_frame.loc[train_mask].mean(axis=0)
    context_frame = context_frame.fillna(context_means).fillna(0.0)

    standardization = {
        "feature_means": {
            column: round(float(feature_means[column]), 10) for column in FEATURE_COLUMNS
        },
        "feature_stds": {
            column: round(float(feature_stds[column]), 10) for column in FEATURE_COLUMNS
        },
        "context_means": {
            column: round(float(context_means[column]), 10) for column in CONTEXT_COLUMNS
        },
    }
    return (
        feature_frame.to_numpy(np.float32),
        context_frame.to_numpy(np.float32),
        standardization,
    )


def build_sequence_indices(
    frame: pd.DataFrame,
    candidate_mask: np.ndarray,
    lookback: int,
) -> np.ndarray:
    bar_index = frame["bar_index_in_segment"].to_numpy()
    end_indices = np.flatnonzero(candidate_mask & (bar_index >= lookback - 1))
    if len(end_indices) == 0:
        return end_indices
    segment_ids = frame["segment_id"].to_numpy()
    start_indices = end_indices - lookback + 1
    same_segment = segment_ids[start_indices] == segment_ids[end_indices]
    return end_indices[same_segment]


def cap_indices(
    indices: np.ndarray,
    max_samples: int,
    seed: int,
    *,
    randomize: bool,
) -> np.ndarray:
    if max_samples <= 0 or len(indices) <= max_samples:
        return indices
    if randomize:
        rng = np.random.default_rng(seed)
        sampled = rng.choice(indices, size=max_samples, replace=False)
        return np.sort(sampled)
    return indices[:max_samples]


def build_utility_targets(
    frame: pd.DataFrame,
    config: TrainConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    atr = np.nan_to_num(
        frame["atr_14"].to_numpy(np.float32),
        nan=1.0,
        posinf=1.0,
        neginf=1.0,
    )
    stop_distance = np.maximum(config.stop_atr_multiple * atr, 0.25)
    cost_r = config.round_trip_cost_points / stop_distance
    win_r = (config.target_atr_multiple / config.stop_atr_multiple) - cost_r
    loss_r = -1.0 - cost_r

    labels = frame[LABEL_COLUMNS].to_numpy(np.float32)
    utility_targets = np.where(labels > 0.5, win_r[:, None], loss_r[:, None]).astype(np.float32)
    action_targets = np.maximum(np.max(utility_targets * labels, axis=1), 0.0).astype(np.float32)
    return utility_targets, action_targets


def subsample_train_indices(
    frame: pd.DataFrame,
    train_mask: np.ndarray,
    config: TrainConfig,
) -> np.ndarray:
    eligible_mask = train_mask & frame["model_sample_eligible"].to_numpy()
    eligible_indices = build_sequence_indices(frame, eligible_mask, config.lookback)
    labels = frame[LABEL_COLUMNS].to_numpy(bool)
    positive_indices = eligible_indices[labels[eligible_indices].any(axis=1)]
    negative_indices = eligible_indices[~labels[eligible_indices].any(axis=1)]
    max_negative = int(len(positive_indices) * config.train_negative_ratio)
    rng = np.random.default_rng(config.seed)
    if len(negative_indices) > max_negative > 0:
        negative_indices = rng.choice(negative_indices, size=max_negative, replace=False)
    return np.sort(np.concatenate([positive_indices, negative_indices]))


def make_dataset_slices(
    features: np.ndarray,
    contexts: np.ndarray,
    labels: np.ndarray,
    utility_targets: np.ndarray,
    action_targets: np.ndarray,
    indices: np.ndarray,
    lookback: int,
) -> SequenceDataset:
    return SequenceDataset(
        features=features,
        contexts=contexts,
        labels=labels,
        utility_targets=utility_targets,
        action_targets=action_targets,
        end_indices=indices,
        lookback=lookback,
    )


def batch_load_balance_loss(gate_weights: torch.Tensor) -> torch.Tensor:
    avg_weights = gate_weights.mean(dim=0)
    uniform = torch.full_like(avg_weights, 1.0 / gate_weights.shape[1])
    return torch.mean((avg_weights - uniform) ** 2)


def batch_specialization_loss(
    expert_utilities: torch.Tensor,
    labels: torch.Tensor,
    margin: float,
) -> torch.Tensor:
    positive_rows = labels.sum(dim=1) > 0
    if not torch.any(positive_rows):
        return expert_utilities.new_tensor(0.0)
    pos_utilities = expert_utilities[positive_rows]
    pos_labels = labels[positive_rows]
    positive_scores = (pos_utilities * pos_labels).sum(dim=1)
    negative_scores = torch.max(
        pos_utilities.masked_fill(pos_labels > 0.5, float("-inf")),
        dim=1,
    ).values
    negative_scores = torch.where(torch.isfinite(negative_scores), negative_scores, 0.0)
    return torch.relu(margin - (positive_scores - negative_scores)).mean()


def gate_alignment_loss(gate_logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    positive_rows = labels.sum(dim=1) > 0
    if not torch.any(positive_rows):
        return gate_logits.new_tensor(0.0)
    targets = torch.argmax(labels[positive_rows], dim=1)
    return nn.functional.cross_entropy(gate_logits[positive_rows], targets)


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


def train_epoch(
    model: LearnedMoE,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    pos_weight: torch.Tensor,
    config: TrainConfig,
    device: torch.device,
) -> Dict[str, float]:
    model.train()
    total_loss = 0.0
    all_probs = []
    all_labels = []
    bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    huber = nn.HuberLoss()

    for feature_sequences, contexts, labels, utility_targets, action_targets in loader:
        feature_sequences = feature_sequences.to(device)
        contexts = contexts.to(device)
        labels = labels.to(device)
        utility_targets = utility_targets.to(device)
        action_targets = action_targets.to(device)

        outputs = model(feature_sequences, contexts)
        expert_loss = bce(outputs["expert_logits"], labels)
        utility_loss = huber(outputs["expert_utilities"], utility_targets)
        action_loss = huber(outputs["action_value"], action_targets)
        gate_loss = gate_alignment_loss(outputs["gate_logits"], labels)
        balance_loss = batch_load_balance_loss(outputs["gate_weights"])
        specialization_loss = batch_specialization_loss(
            outputs["expert_utilities"],
            labels,
            config.utility_margin,
        )
        loss = (
            expert_loss
            + config.utility_weight * utility_loss
            + config.action_value_weight * action_loss
            + config.gate_alignment_weight * gate_loss
            + config.load_balance_weight * balance_loss
            + config.specialization_weight * specialization_loss
        )

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += float(loss.item()) * len(feature_sequences)
        all_probs.append(outputs["expert_probs"].detach().cpu().numpy())
        all_labels.append(labels.detach().cpu().numpy())

    probs = np.concatenate(all_probs, axis=0)
    labels = np.concatenate(all_labels, axis=0)
    return {
        "loss": total_loss / len(loader.dataset),
        "mean_average_precision": mean_average_precision(labels, probs),
    }


@torch.no_grad()
def predict(
    model: LearnedMoE,
    loader: DataLoader,
    device: torch.device,
) -> Dict[str, np.ndarray]:
    model.eval()
    outputs = {
        "expert_probs": [],
        "expert_utilities": [],
        "gate_weights": [],
        "action_value": [],
    }
    labels = []
    for feature_sequences, contexts, batch_labels, utility_targets, action_targets in loader:
        feature_sequences = feature_sequences.to(device)
        contexts = contexts.to(device)
        pred = model(feature_sequences, contexts)
        outputs["expert_probs"].append(pred["expert_probs"].cpu().numpy())
        outputs["expert_utilities"].append(pred["expert_utilities"].cpu().numpy())
        outputs["gate_weights"].append(pred["gate_weights"].cpu().numpy())
        outputs["action_value"].append(pred["action_value"].cpu().numpy())
        labels.append(batch_labels.numpy())

    packed = {name: np.concatenate(parts, axis=0) for name, parts in outputs.items()}
    packed["labels"] = np.concatenate(labels, axis=0)
    return packed


def summarize_predictions(predictions: Dict[str, np.ndarray]) -> Dict[str, float]:
    labels = predictions["labels"]
    probs = predictions["expert_probs"]
    return {
        "mean_average_precision": mean_average_precision(labels, probs),
        "mean_roc_auc": mean_roc_auc(labels, probs),
    }


def simulate_trade(
    frame: pd.DataFrame,
    index: int,
    setup: str,
    config: BacktestConfig,
) -> Dict[str, object]:
    entry_price = float(frame.at[index, "close"])
    atr = float(frame.at[index, "atr_14"])
    if not math.isfinite(atr) or atr <= 0:
        return {}
    stop_distance = config.stop_atr_multiple * atr
    target_distance = config.target_atr_multiple * atr
    if setup in LONG_SETUPS:
        stop_price = entry_price - stop_distance
        target_price = entry_price + target_distance
        is_long = True
    else:
        stop_price = entry_price + stop_distance
        target_price = entry_price - target_distance
        is_long = False

    segment_id = int(frame.at[index, "segment_id"])
    last_index = min(index + config.horizon_bars, len(frame) - 1)
    for next_index in range(index + 1, last_index + 1):
        if int(frame.at[next_index, "segment_id"]) != segment_id:
            break
        high = float(frame.at[next_index, "high"])
        low = float(frame.at[next_index, "low"])
        if is_long:
            hit_target = high >= target_price
            hit_stop = low <= stop_price
        else:
            hit_target = low <= target_price
            hit_stop = high >= stop_price
        if hit_target and hit_stop:
            return {
                "exit_index": next_index,
                "exit_price": stop_price,
                "exit_reason": "ambiguous_stop_bar",
                "pnl_r": -1.0,
            }
        if hit_target:
            return {
                "exit_index": next_index,
                "exit_price": target_price,
                "exit_reason": "target",
                "pnl_r": config.target_atr_multiple / config.stop_atr_multiple,
            }
        if hit_stop:
            return {
                "exit_index": next_index,
                "exit_price": stop_price,
                "exit_reason": "stop",
                "pnl_r": -1.0,
            }

    exit_index = min(last_index, len(frame) - 1)
    exit_price = float(frame.at[exit_index, "close"])
    if is_long:
        pnl_r = safe_div(exit_price - entry_price, stop_distance)
    else:
        pnl_r = safe_div(entry_price - exit_price, stop_distance)
    return {
        "exit_index": exit_index,
        "exit_price": exit_price,
        "exit_reason": "time",
        "pnl_r": pnl_r,
    }


def effective_risk_pct(
    action_value: float,
    balance: float,
    daily_pnl_pct: float,
    config: BacktestConfig,
) -> float:
    if not config.dynamic_risk:
        return config.risk_per_trade_pct
    normalized_edge = max(action_value, 0.0)
    signal_strength = 1.0 - math.exp(
        -max(normalized_edge, 0.0) / max(config.utility_scale, 1e-6)
    )
    risk_pct = config.min_risk_pct + (config.max_risk_pct - config.min_risk_pct) * signal_strength
    remaining_to_target_pct = max(
        config.profit_target_pct - ((balance / config.starting_balance) - 1.0) * 100.0,
        0.0,
    )
    urgency_multiplier = 1.0 + config.urgency_weight * (
        remaining_to_target_pct / max(config.profit_target_pct, 1e-6)
    )
    daily_buffer = max(config.max_daily_loss_pct + daily_pnl_pct, 0.0)
    drawdown_multiplier = min(
        daily_buffer / max(config.max_daily_loss_pct, 1e-6),
        1.0,
    )
    safety_multiplier = (1.0 - config.drawdown_safety_weight) + (
        config.drawdown_safety_weight * drawdown_multiplier
    )
    return max(
        config.min_risk_pct,
        min(config.max_risk_pct, risk_pct * urgency_multiplier * safety_multiplier),
    )


def apply_risk_budgets(
    desired_risk_pct: float,
    balance: float,
    trade_cost_r: float,
    daily_pnl_pct: float,
    config: BacktestConfig,
) -> Tuple[float, str | None]:
    desired_risk_pct = max(desired_risk_pct, 0.0)
    capped_risk_pct = min(desired_risk_pct, config.max_loss_per_trade_pct)
    if capped_risk_pct <= 0.0 or balance <= 0.0:
        return 0.0, "per_trade_risk_limit"

    worst_case_loss_multiple = 1.0 + max(trade_cost_r, 0.0)
    remaining_daily_loss_cash = max(
        config.max_daily_loss_pct + daily_pnl_pct,
        0.0,
    ) / 100.0 * config.starting_balance
    floor_balance = config.starting_balance * (
        1.0 - config.max_total_drawdown_pct / 100.0
    )
    remaining_total_buffer_cash = max(balance - floor_balance, 0.0)

    max_risk_cash = balance * (capped_risk_pct / 100.0)
    max_risk_cash = min(
        max_risk_cash,
        remaining_daily_loss_cash / worst_case_loss_multiple
        if remaining_daily_loss_cash > 0.0
        else 0.0,
        remaining_total_buffer_cash / worst_case_loss_multiple
        if remaining_total_buffer_cash > 0.0
        else 0.0,
    )
    if max_risk_cash <= 0.0:
        if remaining_daily_loss_cash <= 0.0:
            return 0.0, "daily_risk_budget"
        if remaining_total_buffer_cash <= 0.0:
            return 0.0, "total_drawdown_budget"
        return 0.0, "per_trade_risk_limit"

    return (max_risk_cash / balance) * 100.0, None


def backtest_predictions(
    frame: pd.DataFrame,
    indices: np.ndarray,
    predictions: Dict[str, np.ndarray],
    config: BacktestConfig,
) -> Dict[str, object]:
    atr = np.nan_to_num(
        frame.loc[indices, "atr_14"].to_numpy(np.float32),
        nan=1.0,
        posinf=1.0,
        neginf=1.0,
    )
    stop_distance = np.maximum(config.stop_atr_multiple * atr, 0.25)
    cost_r = config.round_trip_cost_points / stop_distance
    win_r = (config.target_atr_multiple / config.stop_atr_multiple) - cost_r
    loss_r = -1.0 - cost_r
    expected_utilities = (
        predictions["expert_probs"] * win_r[:, None]
        + (1.0 - predictions["expert_probs"]) * loss_r[:, None]
    )
    action_values = np.max(expected_utilities, axis=1)
    routed_utilities = predictions["gate_weights"] * expected_utilities
    chosen_setup_idx = np.argmax(routed_utilities, axis=1)
    chosen_action_value = np.max(routed_utilities, axis=1)

    balance = config.starting_balance
    skip_counts = {
        "non_positive_utility": 0,
        "cooldown": 0,
        "session_end_buffer": 0,
        "daily_trade_cap": 0,
        "daily_loss_lock": 0,
        "total_drawdown_lock": 0,
        "daily_risk_budget": 0,
        "total_drawdown_budget": 0,
    }
    trade_rows = []
    cooldown_until = -1
    day_trade_count: Dict[str, int] = {}
    day_realized_pnl_pct: Dict[str, float] = {}
    day_end_balance: Dict[str, float] = {}
    target_balance = config.starting_balance * (1.0 + config.profit_target_pct / 100.0)
    reached_profit_target = False
    days_to_target = None

    for local_pos, row_index in enumerate(indices):
        row = frame.iloc[row_index]
        trade_day = str(row["session_date_utc"])
        day_trade_count.setdefault(trade_day, 0)
        day_realized_pnl_pct.setdefault(trade_day, 0.0)

        if chosen_action_value[local_pos] <= 0.0:
            skip_counts["non_positive_utility"] += 1
            continue
        if row_index <= cooldown_until:
            skip_counts["cooldown"] += 1
            continue
        if int(row["bars_remaining_in_segment"]) <= config.session_end_buffer_bars:
            skip_counts["session_end_buffer"] += 1
            continue
        if day_trade_count[trade_day] >= config.max_trades_per_day:
            skip_counts["daily_trade_cap"] += 1
            continue
        if day_realized_pnl_pct[trade_day] <= -config.max_daily_loss_pct:
            skip_counts["daily_loss_lock"] += 1
            continue
        if balance <= config.starting_balance * (
            1.0 - config.max_total_drawdown_pct / 100.0
        ):
            skip_counts["total_drawdown_lock"] += 1
            continue

        setup = SETUPS[int(chosen_setup_idx[local_pos])]
        trade_cost_r = float(cost_r[local_pos])
        desired_risk_pct = effective_risk_pct(
            action_value=float(chosen_action_value[local_pos]),
            balance=balance,
            daily_pnl_pct=day_realized_pnl_pct[trade_day],
            config=config,
        )
        risk_pct, blocked_reason = apply_risk_budgets(
            desired_risk_pct=desired_risk_pct,
            balance=balance,
            trade_cost_r=trade_cost_r,
            daily_pnl_pct=day_realized_pnl_pct[trade_day],
            config=config,
        )
        if blocked_reason is not None:
            skip_counts[blocked_reason] += 1
            continue
        trade_result = simulate_trade(frame, row_index, setup, config)
        if not trade_result:
            continue

        risk_cash = balance * (risk_pct / 100.0)
        pnl_r = float(trade_result["pnl_r"]) - trade_cost_r
        pnl_cash = risk_cash * pnl_r
        balance_before = balance
        balance = balance + pnl_cash
        day_trade_count[trade_day] += 1
        day_realized_pnl_pct[trade_day] += (pnl_cash / config.starting_balance) * 100.0
        day_end_balance[trade_day] = balance
        cooldown_until = int(trade_result["exit_index"]) + config.cooldown_bars

        trade_rows.append(
            {
                "setup": setup,
                "gate_weight": float(
                    predictions["gate_weights"][local_pos, chosen_setup_idx[local_pos]]
                ),
                "predicted_utility": float(chosen_action_value[local_pos]),
                "action_value": float(action_values[local_pos]),
                "transaction_cost_r": trade_cost_r,
                "session_date_utc": trade_day,
                "market_session": row["market_session"],
                "session_phase": row["session_phase"],
                "balance_before": round(balance_before, 2),
                "balance_after": round(balance, 2),
                "desired_risk_pct": round(desired_risk_pct, 4),
                "risk_pct": round(risk_pct, 4),
                "risk_cash": round(risk_cash, 2),
                "pnl_cash": round(pnl_cash, 2),
                "pnl_r": pnl_r,
                "entry_index": int(row_index),
                "exit_index": int(trade_result["exit_index"]),
                "entry_timestamp": row["timestamp"].isoformat(),
                "exit_timestamp": frame.at[int(trade_result["exit_index"]), "timestamp"].isoformat(),
                "entry_price": float(row["close"]),
                "exit_price": float(trade_result["exit_price"]),
                "exit_reason": trade_result["exit_reason"],
                "bars_held": int(trade_result["exit_index"]) - int(row_index),
            }
        )

        if not reached_profit_target and balance >= target_balance:
            reached_profit_target = True
            days_to_target = len(day_end_balance)

    daily_returns = []
    day_balances = []
    for day in sorted(day_end_balance):
        day_balances.append(day_end_balance[day])
    running_peak = config.starting_balance
    max_drawdown_pct = 0.0
    previous_balance = config.starting_balance
    for balance_value in day_balances:
        day_return_pct = (balance_value / previous_balance - 1.0) * 100.0
        daily_returns.append(day_return_pct)
        running_peak = max(running_peak, balance_value)
        max_drawdown_pct = min(
            max_drawdown_pct,
            (balance_value / running_peak - 1.0) * 100.0,
        )
        previous_balance = balance_value

    evaluation = evaluate_propfirm_path(
        daily_returns_pct=daily_returns,
        starting_balance=config.starting_balance,
        profit_target_pct=config.profit_target_pct,
        max_total_drawdown_pct=config.max_total_drawdown_pct,
        min_profitable_days=config.min_profitable_days,
    )

    wins = [row["pnl_r"] for row in trade_rows if row["pnl_r"] > 0]
    losses = [row["pnl_r"] for row in trade_rows if row["pnl_r"] < 0]
    total_r = sum(row["pnl_r"] for row in trade_rows)
    profit_factor = safe_div(sum(wins), -sum(losses))
    return {
        "summary": {
            "trades": len(trade_rows),
            "trading_days": len(day_end_balance),
            "win_rate": round(safe_div(len(wins), len(trade_rows)), 6),
            "expectancy_r": round(safe_div(total_r, len(trade_rows)), 6),
            "total_r": round(total_r, 6),
            "profit_factor": round(profit_factor, 6),
            "average_hold_bars": round(
                safe_div(sum(row["bars_held"] for row in trade_rows), len(trade_rows)),
                6,
            ),
            "ending_balance": round(balance, 2),
            "total_return_pct": round(
                (balance / config.starting_balance - 1.0) * 100.0,
                4,
            ),
            "max_drawdown_pct": round(abs(max_drawdown_pct), 4),
            "reached_profit_target": reached_profit_target,
            "days_to_target": days_to_target,
            "profitable_days": int(evaluation["profitable_days"]),
            "min_profitable_days_required": config.min_profitable_days,
            "passed_evaluation": bool(evaluation["passed"]),
            "days_to_pass": evaluation["days_to_pass"],
            "breached_total_drawdown": bool(evaluation["breached_total_drawdown"]),
            "skip_counts": skip_counts,
        },
        "daily_returns_pct": daily_returns,
        "trades": trade_rows,
    }


def bootstrap_pass_probability(
    daily_returns_pct: List[float],
    config: BacktestConfig,
    simulations: int = 2000,
    max_days: int = 60,
    seed: int = 7,
) -> Dict[str, float]:
    if not daily_returns_pct:
        return {
            "pass_probability": 0.0,
            "median_days_to_pass": None,
            "median_days_to_target": None,
        }
    rng = np.random.default_rng(seed)
    pass_days = []
    for _ in range(simulations):
        sampled_returns = []
        for day in range(1, max_days + 1):
            day_return_pct = float(rng.choice(daily_returns_pct))
            sampled_returns.append(day_return_pct)
            evaluation = evaluate_propfirm_path(
                daily_returns_pct=sampled_returns,
                starting_balance=config.starting_balance,
                profit_target_pct=config.profit_target_pct,
                max_total_drawdown_pct=config.max_total_drawdown_pct,
                min_profitable_days=config.min_profitable_days,
            )
            if evaluation["passed"]:
                pass_days.append(day)
                break
            if evaluation["breached_total_drawdown"]:
                break
    if not pass_days:
        return {
            "pass_probability": 0.0,
            "median_days_to_pass": None,
            "median_days_to_target": None,
        }
    return {
        "pass_probability": round(len(pass_days) / simulations, 6),
        "median_days_to_pass": int(np.median(pass_days)),
        "median_days_to_target": int(np.median(pass_days)),
    }


def utility_by_setup(predictions: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
    out = {}
    labels = predictions["labels"]
    probs = predictions["expert_probs"]
    utilities = predictions["expert_utilities"]
    gates = predictions["gate_weights"]
    for setup_idx, setup in enumerate(SETUPS):
        setup_probs = probs[:, setup_idx]
        top_decile = max(int(len(setup_probs) * 0.1), 1)
        ranked = np.argsort(setup_probs)[-top_decile:]
        positive_count = int(np.sum(labels[:, setup_idx]))
        unique_values = np.unique(labels[:, setup_idx]).size
        out[setup] = {
            "average_precision": round(
                float(average_precision_score(labels[:, setup_idx], setup_probs))
                if positive_count > 0
                else 0.0,
                6,
            ),
            "roc_auc": round(
                float(roc_auc_score(labels[:, setup_idx], setup_probs))
                if unique_values > 1
                else 0.0,
                6,
            ),
            "mean_predicted_utility": round(float(np.mean(utilities[:, setup_idx])), 6),
            "mean_gate_weight": round(float(np.mean(gates[:, setup_idx])), 6),
            "top_decile_precision": round(float(np.mean(labels[ranked, setup_idx])), 6),
        }
    return out


def save_json(path: Path, payload: Dict[str, object]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_trades_csv(path: Path, trades: List[Dict[str, object]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not trades:
        return
    with gzip.open(path, "wt", newline="") as handle:
        pd.DataFrame(trades).to_csv(handle, index=False)


def tune_prop_policy(
    frame: pd.DataFrame,
    val_indices: np.ndarray,
    val_predictions: Dict[str, np.ndarray],
    base_config: BacktestConfig,
    seed: int,
) -> Dict[str, object]:
    candidate_configs = []
    for min_risk in (0.35, 0.50, 0.75, 1.00):
        for max_risk in (0.75, 1.00, 1.50, 2.00, 2.50, 3.00):
            if max_risk < min_risk:
                continue
            for utility_scale in (0.20, 0.35, 0.50):
                for max_trades in (6, 8):
                    for cooldown in (3, 5):
                        config = BacktestConfig(
                            **{
                                **asdict(base_config),
                                "dynamic_risk": True,
                                "min_risk_pct": min_risk,
                                "max_risk_pct": max_risk,
                                "utility_scale": utility_scale,
                                "max_trades_per_day": max_trades,
                                "cooldown_bars": cooldown,
                                "urgency_weight": 0.50,
                                "drawdown_safety_weight": 0.60,
                            }
                        )
                        backtest = backtest_predictions(frame, val_indices, val_predictions, config)
                        bootstrap = bootstrap_pass_probability(
                            backtest["daily_returns_pct"],
                            config,
                            seed=seed,
                        )
                        summary = backtest["summary"]
                        pass_prob = bootstrap["pass_probability"]
                        median_days = bootstrap["median_days_to_pass"] or 999
                        score = (
                            pass_prob * 1000.0
                            + summary["total_return_pct"] * 10.0
                            - summary["max_drawdown_pct"] * 4.0
                            + (50.0 if summary["passed_evaluation"] else 0.0)
                            - median_days
                        )
                        candidate_configs.append(
                            {
                                "score": round(score, 6),
                                "bootstrap": bootstrap,
                                "summary": summary,
                                "config": asdict(config),
                            }
                        )
    candidate_configs.sort(key=lambda item: item["score"], reverse=True)
    return candidate_configs[0]


def run_train(args) -> int:
    set_seed(args.seed)
    dataset_path = Path(args.dataset).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    train_config = TrainConfig(
        lookback=args.lookback,
        batch_size=args.batch_size,
        epochs=args.epochs,
        hidden_dim=args.hidden_dim,
        trunk_dim=args.trunk_dim,
        gate_hidden_dim=args.gate_hidden_dim,
        kernel_size=args.kernel_size,
        channels=tuple(args.channels),
        train_negative_ratio=args.train_negative_ratio,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        seed=args.seed,
    )
    frame = load_dataset(dataset_path)
    masks = build_masks(frame, train_config.train_fraction, train_config.val_fraction)
    feature_matrix, context_matrix, standardization = fill_and_standardize(frame, masks["train"])
    utility_targets, action_targets = build_utility_targets(frame, train_config)
    labels = frame[LABEL_COLUMNS].to_numpy(np.float32)

    train_indices = subsample_train_indices(frame, masks["train"], train_config)
    val_indices = build_sequence_indices(
        frame,
        masks["val"] & frame["model_sample_eligible"].to_numpy(),
        train_config.lookback,
    )
    test_indices = build_sequence_indices(
        frame,
        masks["test"] & frame["model_sample_eligible"].to_numpy(),
        train_config.lookback,
    )

    train_indices = cap_indices(
        train_indices,
        train_config.max_train_samples,
        train_config.seed,
        randomize=True,
    )
    val_indices = cap_indices(
        val_indices,
        train_config.max_eval_samples,
        train_config.seed,
        randomize=False,
    )
    test_indices = cap_indices(
        test_indices,
        train_config.max_eval_samples,
        train_config.seed,
        randomize=False,
    )

    if len(train_indices) == 0 or len(val_indices) == 0 or len(test_indices) == 0:
        raise ValueError("The sequence-safe splits are empty. Check lookback and dataset eligibility.")

    train_dataset = make_dataset_slices(
        feature_matrix,
        context_matrix,
        labels,
        utility_targets,
        action_targets,
        train_indices,
        train_config.lookback,
    )
    val_dataset = make_dataset_slices(
        feature_matrix,
        context_matrix,
        labels,
        utility_targets,
        action_targets,
        val_indices,
        train_config.lookback,
    )
    test_dataset = make_dataset_slices(
        feature_matrix,
        context_matrix,
        labels,
        utility_targets,
        action_targets,
        test_indices,
        train_config.lookback,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=train_config.batch_size,
        shuffle=True,
        drop_last=False,
    )
    eval_loader_kwargs = {
        "batch_size": train_config.batch_size,
        "shuffle": False,
        "drop_last": False,
    }
    val_loader = DataLoader(val_dataset, **eval_loader_kwargs)
    test_loader = DataLoader(test_dataset, **eval_loader_kwargs)

    device = torch.device(args.device)
    model = LearnedMoE(len(FEATURE_COLUMNS), len(CONTEXT_COLUMNS), train_config).to(device)
    label_sums = labels[train_indices].sum(axis=0)
    negative_sums = len(train_indices) - label_sums
    pos_weight = torch.tensor(
        np.maximum(negative_sums / np.maximum(label_sums, 1.0), 1.0),
        dtype=torch.float32,
        device=device,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_config.learning_rate,
        weight_decay=train_config.weight_decay,
    )

    history = []
    best_state = None
    best_val_ap = -float("inf")
    for epoch in range(1, train_config.epochs + 1):
        train_metrics = train_epoch(model, train_loader, optimizer, pos_weight, train_config, device)
        val_predictions = predict(model, val_loader, device)
        val_metrics = summarize_predictions(val_predictions)
        history.append(
            {
                "epoch": epoch,
                "train_loss": round(train_metrics["loss"], 6),
                "train_mean_average_precision": round(
                    train_metrics["mean_average_precision"],
                    6,
                ),
                "val_mean_average_precision": round(
                    val_metrics["mean_average_precision"],
                    6,
                ),
                "val_mean_roc_auc": round(val_metrics["mean_roc_auc"], 6),
            }
        )
        if val_metrics["mean_average_precision"] > best_val_ap:
            best_val_ap = val_metrics["mean_average_precision"]
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    val_predictions = predict(model, val_loader, device)
    test_predictions = predict(model, test_loader, device)
    val_metrics = summarize_predictions(val_predictions)
    test_metrics = summarize_predictions(test_predictions)

    fixed_risk_config = BacktestConfig(
        **fundedhive_backtest_defaults(),
        session_end_buffer_bars=train_config.session_end_buffer_bars,
        target_atr_multiple=train_config.target_atr_multiple,
        stop_atr_multiple=train_config.stop_atr_multiple,
        round_trip_cost_points=train_config.round_trip_cost_points,
        risk_per_trade_pct=0.50,
        min_risk_pct=0.50,
        max_risk_pct=0.50,
    )
    fixed_val_backtest = backtest_predictions(frame, val_indices, val_predictions, fixed_risk_config)
    fixed_test_backtest = backtest_predictions(frame, test_indices, test_predictions, fixed_risk_config)

    tuned_policy = tune_prop_policy(
        frame,
        val_indices,
        val_predictions,
        fixed_risk_config,
        train_config.seed,
    )
    prop_config = BacktestConfig(**tuned_policy["config"])
    prop_test_backtest = backtest_predictions(frame, test_indices, test_predictions, prop_config)
    prop_test_bootstrap = bootstrap_pass_probability(
        prop_test_backtest["daily_returns_pct"],
        prop_config,
        seed=train_config.seed,
    )

    torch.save(
        {
            "state_dict": model.state_dict(),
            "train_config": asdict(train_config),
            "feature_columns": FEATURE_COLUMNS,
            "context_columns": CONTEXT_COLUMNS,
            "standardization": standardization,
        },
        artifacts_dir / "model.pt",
    )
    save_trades_csv(
        artifacts_dir / "fixed_risk_backtest_trades.csv.gz",
        fixed_test_backtest["trades"],
    )
    save_trades_csv(
        artifacts_dir / "prop_backtest_trades.csv.gz",
        prop_test_backtest["trades"],
    )

    training_summary = {
        "dataset": str(dataset_path),
        "artifacts_dir": str(artifacts_dir),
        "prop_firm_policy": policy_metadata(),
        "train_config": asdict(train_config),
        "dataset_rows": int(len(frame)),
        "sequence_rows": {
            "train": int(len(train_indices)),
            "val": int(len(val_indices)),
            "test": int(len(test_indices)),
        },
        "history": history,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "expert_metrics": utility_by_setup(test_predictions),
        "standardization": standardization,
        "architecture": {
            "encoder": "causal_tcn",
            "channels": list(train_config.channels),
            "kernel_size": train_config.kernel_size,
            "lookback": train_config.lookback,
            "top_k": train_config.top_k,
        },
    }
    fixed_backtest_summary = {
        "policy": "fundedhive_fixed_risk_baseline",
        "prop_firm_policy": policy_metadata(),
        "config": asdict(fixed_risk_config),
        "validation": fixed_val_backtest["summary"],
        "test": fixed_test_backtest["summary"],
    }
    prop_backtest_summary = {
        "policy": "validation_tuned_dynamic_fundedhive_policy",
        "prop_firm_policy": policy_metadata(),
        "selected_from_validation": tuned_policy,
        "test": prop_test_backtest["summary"],
        "test_bootstrap_pass_probability": prop_test_bootstrap,
    }

    save_json(artifacts_dir / "training_summary.json", training_summary)
    save_json(artifacts_dir / "fixed_risk_backtest_summary.json", fixed_backtest_summary)
    save_json(artifacts_dir / "prop_backtest_summary.json", prop_backtest_summary)
    return 0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train"])
    parser.add_argument(
        "--dataset",
        default="data/features/us100_specialist_tcn_dataset_session_refined.csv.gz",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/learned_moe/us100_session_refined_tcn",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--lookback", type=int, default=96)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--trunk-dim", type=int, default=128)
    parser.add_argument("--gate-hidden-dim", type=int, default=64)
    parser.add_argument("--kernel-size", type=int, default=3)
    parser.add_argument("--channels", nargs="+", type=int, default=[64, 64, 96])
    parser.add_argument("--train-negative-ratio", type=float, default=4.0)
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--max-eval-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "train":
        return run_train(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
