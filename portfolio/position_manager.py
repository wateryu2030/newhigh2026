# -*- coding: utf-8 -*-
"""
仓位管理：单股最大 10%、单行业最大 30%、最大持仓数 10~15；支持分批建仓。
"""
from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np


class PositionManager:
    """
    机构级仓位约束。
    - 单股最大仓位 10%
    - 单行业最大 30%
    - 最大持仓数 10~15
    - 可配置分批建仓比例
    """

    def __init__(
        self,
        max_single_pct: float = 0.10,
        max_sector_pct: float = 0.30,
        max_positions: int = 15,
        min_positions: int = 1,
        sector_map: Optional[Dict[str, str]] = None,
        batch_ratio: float = 1.0,
    ):
        self.max_single_pct = max_single_pct
        self.max_sector_pct = max_sector_pct
        self.max_positions = max(max_positions, 1)
        self.min_positions = min(min_positions, max_positions)
        self.sector_map = sector_map or {}
        self.batch_ratio = max(0.01, min(1.0, batch_ratio))

    def apply_constraints(
        self,
        positions: Dict[str, float],
        total_equity: float,
    ) -> Dict[str, float]:
        """
        对目标仓位施加约束，返回合规后的 { symbol: 金额 }。
        """
        if not positions or total_equity <= 0:
            return {}
        symbols = list(positions.keys())
        amounts = np.array([positions.get(s, 0) for s in symbols], dtype=float)
        amounts = np.maximum(amounts, 0)
        total = amounts.sum()
        if total <= 0:
            return {}
        # 按金额降序，保留前 max_positions
        idx = np.argsort(-amounts)
        keep = idx[: self.max_positions]
        out = {s: 0.0 for s in symbols}
        for i in keep:
            out[symbols[i]] = float(amounts[i])
        # 单股上限
        for s in list(out.keys()):
            cap = total_equity * self.max_single_pct
            if out[s] > cap:
                out[s] = float(cap)
        # 行业上限
        if self.sector_map:
            sector_totals: Dict[str, float] = {}
            for s, v in out.items():
                sec = self.sector_map.get(s, "OTHER")
                sector_totals[sec] = sector_totals.get(sec, 0) + v
            for sec, sec_sum in sector_totals.items():
                if sec_sum > total_equity * self.max_sector_pct:
                    scale = (total_equity * self.max_sector_pct) / sec_sum
                    for s in out:
                        if self.sector_map.get(s, "OTHER") == sec:
                            out[s] = float(out[s] * scale)
        # 归一化到总资金比例后应用 batch_ratio
        current_sum = sum(out.values())
        if current_sum > 0 and self.batch_ratio < 1.0:
            for s in out:
                out[s] = float(out[s] * self.batch_ratio)
        return {s: v for s, v in out.items() if v > 0}

    def batch_build_ratio(self, step: int = 0) -> float:
        """分批建仓：第 step 步的建仓比例（0~1）。"""
        if step <= 0:
            return self.batch_ratio
        return min(1.0, self.batch_ratio * (1 + step * 0.5))
