# -*- coding: utf-8 -*-
"""
风险预算：风险平价思路，按波动率倒数分配权重（风险贡献相等）。
"""
from __future__ import annotations
from typing import Union
import numpy as np


class RiskBudget:
    def allocate(self, vols: Union[list, np.ndarray]) -> np.ndarray:
        vols = np.asarray(vols, dtype=float)
        inv_vol = 1.0 / (vols + 1e-6)
        weights = inv_vol / inv_vol.sum()
        return weights
