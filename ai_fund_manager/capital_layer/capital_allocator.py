# -*- coding: utf-8 -*-
"""
资金分配器：根据总资金与权重计算各策略/标的的目标仓位。
"""
from __future__ import annotations
from typing import Dict, Union
import numpy as np


class CapitalAllocator:
    def allocate(
        self,
        capital: float,
        weights: Union[Dict[str, float], np.ndarray],
        names: list = None,
    ) -> Dict[str, float]:
        if isinstance(weights, np.ndarray):
            if names is None:
                names = [f"s{i}" for i in range(len(weights))]
            weights = dict(zip(names, weights))
        return {k: float(capital * v) for k, v in weights.items()}
