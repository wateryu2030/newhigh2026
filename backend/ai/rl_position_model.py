# -*- coding: utf-8 -*-
"""
强化学习仓位模型接口：输入状态（净值、波动、持仓等），输出建议仓位比例。
可与现有 RL 模块（rl_trading）对接或独立训练。
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional

import numpy as np


class RLPositionModelBase:
    """RL 仓位模型基类：state → position_pct [0, 1]。"""

    def predict(self, state: Dict[str, Any]) -> float:
        """state: { equity_curve?, volatility?, positions?, ... }。返回建议仓位比例。"""
        raise NotImplementedError


class RuleBasedPosition(RLPositionModelBase):
    """规则仓位：按回撤/波动缩仓，无 RL。"""

    def __init__(self, max_drawdown_scale: float = 0.15, target_vol: float = 0.15):
        self.max_dd = max_drawdown_scale
        self.target_vol = target_vol

    def predict(self, state: Dict[str, Any]) -> float:
        equity = state.get("equity_curve") or state.get("equity_curve_list")
        if equity and len(equity) >= 2:
            peak = max(equity)
            current = equity[-1]
            if peak > 0:
                dd = (peak - current) / peak
                if dd >= self.max_dd:
                    return 0.3
                scale = 1.0 - (dd / self.max_dd) * 0.5
                return max(0.3, min(1.0, scale))
        vol = state.get("volatility") or state.get("vol")
        if vol is not None and vol > 0 and self.target_vol > 0:
            scale = self.target_vol / vol
            return max(0.2, min(1.0, scale))
        return 0.7


def load_rl_position_model(model_path: Optional[str] = None) -> Optional[RLPositionModelBase]:
    """
    加载 RL 仓位模型（占位）。实际实现时：
    - 与 rl_trading 训练好的 policy 对接
    - 或加载 SB3/自定义 model，forward(state_vec) → action → 映射为 [0,1] 仓位
    """
    if not model_path or not os.path.isfile(model_path):
        return None
    # TODO: 加载 rl_trading 或 SB3 模型
    return None


def get_rl_position_model(use_rl: bool = False, model_path: Optional[str] = None) -> RLPositionModelBase:
    """工厂：use_rl=True 且 model_path 有效时加载 RL 模型，否则规则仓位。"""
    if use_rl:
        m = load_rl_position_model(model_path)
        if m is not None:
            return m
    return RuleBasedPosition()
