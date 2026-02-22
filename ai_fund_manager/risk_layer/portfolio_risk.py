# -*- coding: utf-8 -*-
"""
组合风险监控：VaR、波动率等。
"""
from __future__ import annotations
from typing import Union
import numpy as np


class PortfolioRisk:
    def calc_var(self, returns: Union[list, np.ndarray], percentile: float = 5.0) -> float:
        returns = np.asarray(returns, dtype=float)
        if returns.size == 0:
            return 0.0
        return float(np.percentile(returns, percentile))

    def calc_vol(self, returns: Union[list, np.ndarray]) -> float:
        returns = np.asarray(returns, dtype=float)
        return float(np.std(returns)) if returns.size > 0 else 0.0
