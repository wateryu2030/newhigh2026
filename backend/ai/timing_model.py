# -*- coding: utf-8 -*-
"""
AI 择时模型接口：LSTM / Transformer 骨架，输出择时信号或 regime 增强。
实际训练与推理可接 PyTorch/TF 或 ONNX；此处为接口与规则 fallback。
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

import numpy as np


class TimingModelBase:
    """择时模型基类：输入特征序列，输出 regime 或 position_pct。"""

    def predict_regime(self, features: np.ndarray) -> str:
        """features: (T, F)。返回 bull | bear | sideways。"""
        raise NotImplementedError

    def predict_position_pct(self, features: np.ndarray) -> float:
        """返回建议仓位比例 [0, 1]。"""
        raise NotImplementedError


class RuleBasedTiming(TimingModelBase):
    """规则择时：用均线/动量等规则，不依赖深度学习。可与 LSTM 输出融合。"""

    def __init__(self, short: int = 20, long: int = 60):
        self.short = short
        self.long = long

    def predict_regime(self, features: np.ndarray) -> str:
        if features is None or len(features) < self.long:
            return "sideways"
        # 假设最后一列为 close
        close = features[:, -1] if features.ndim > 1 else features
        ma_short = np.mean(close[-self.short:])
        ma_long = np.mean(close[-self.long:])
        if ma_short > ma_long:
            return "bull"
        if ma_short < ma_long * 0.98:
            return "bear"
        return "sideways"

    def predict_position_pct(self, features: np.ndarray) -> float:
        r = self.predict_regime(features)
        return {"bull": 1.0, "bear": 0.3, "sideways": 0.7}.get(r, 0.7)


def load_lstm_timing(model_path: Optional[str] = None) -> Optional[TimingModelBase]:
    """
    加载 LSTM 择时模型（占位）。实际实现时：
    - model_path 指向 .pt / .onnx
    - 前向得到 logits 或 regime id → 映射为 bull/bear/sideways
    """
    if not model_path or not os.path.isfile(model_path):
        return None
    # TODO: torch.load / onnxruntime 推理
    return None


def load_transformer_timing(model_path: Optional[str] = None) -> Optional[TimingModelBase]:
    """
    加载 Transformer 择时模型（占位）。同上，序列输入 → 回归/分类。
    """
    if not model_path or not os.path.isfile(model_path):
        return None
    return None


def get_timing_model(kind: str = "rule", model_path: Optional[str] = None) -> TimingModelBase:
    """工厂：rule | lstm | transformer。"""
    if kind == "lstm":
        m = load_lstm_timing(model_path)
        if m is not None:
            return m
    if kind == "transformer":
        m = load_transformer_timing(model_path)
        if m is not None:
            return m
    return RuleBasedTiming()
