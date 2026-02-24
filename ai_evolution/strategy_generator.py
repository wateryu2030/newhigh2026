# -*- coding: utf-8 -*-
"""
策略生成器：随机生成技术策略配置（MA / RSI / MACD / 突破 / 动量）。
输出与插件策略 strategy_id + param_overrides 对应。
"""
from __future__ import annotations
import logging
import random
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 策略类型与插件 id 映射
STRATEGY_TYPES: Dict[str, str] = {
    "trend": "ma_cross",
    "momentum": "rsi",
    "macd": "macd",
    "breakout": "breakout",
}

# 各策略参数范围（与 strategies/* 一致）
PARAM_SPACES: Dict[str, Dict[str, List[Any]]] = {
    "ma_cross": {"fast": [5, 30], "slow": [15, 60]},
    "rsi": {"period": [8, 21], "oversold": [25, 35], "overbought": [65, 80]},
    "macd": {"fast": [8, 15], "slow": [20, 35], "signal": [6, 12]},
    "breakout": {"period": [10, 40]},
}


class StrategyGenerator:
    """随机生成可回测的策略配置。"""

    def __init__(self, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)
        self._param_spaces = dict(PARAM_SPACES)
        self._strategy_types = dict(STRATEGY_TYPES)

    def generate_one(self) -> Dict[str, Any]:
        """
        生成单条策略配置。
        返回格式示例: {"type": "trend", "strategy_id": "ma_cross", "params": {"fast": 10, "slow": 30}}
        或带 rsi 等: {"type": "trend", "ma_short": 10, "ma_long": 30, "rsi": 40} 风格（兼容描述）。
        """
        strategy_id = random.choice(list(self._param_spaces.keys()))
        type_label = next((t for t, s in self._strategy_types.items() if s == strategy_id), strategy_id)
        params = self._sample_params(strategy_id)
        out: Dict[str, Any] = {
            "type": type_label,
            "strategy_id": strategy_id,
            "params": params,
        }
        # 兼容示例中的 ma_short / ma_long / rsi 命名（供展示或存储）
        if strategy_id == "ma_cross":
            out["ma_short"] = params.get("fast", 10)
            out["ma_long"] = params.get("slow", 30)
        if strategy_id == "rsi":
            out["rsi"] = params.get("oversold", 30)
        logger.debug("Generated strategy: %s", out)
        return out

    def _sample_params(self, strategy_id: str) -> Dict[str, Any]:
        """在参数空间内随机采样一组参数。"""
        space = self._param_spaces.get(strategy_id, {})
        params: Dict[str, Any] = {}
        for key, bounds in space.items():
            if not bounds or len(bounds) < 2:
                continue
            low, high = bounds[0], bounds[1]
            if isinstance(low, int) and isinstance(high, int):
                params[key] = random.randint(int(low), int(high))
            else:
                params[key] = round(low + random.random() * (high - low), 4)
        return params

    def generate(self, n: int = 1) -> List[Dict[str, Any]]:
        """生成 n 条策略配置。"""
        return [self.generate_one() for _ in range(n)]

    def get_param_space(self, strategy_id: str) -> Dict[str, List[Any]]:
        """返回某策略的参数空间，供优化器使用。"""
        return dict(self._param_spaces.get(strategy_id, {}))
