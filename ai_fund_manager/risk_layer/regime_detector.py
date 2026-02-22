# -*- coding: utf-8 -*-
"""
市场状态识别：牛市/熊市/震荡、高波动/低波动。
"""
from __future__ import annotations
from typing import Union
import numpy as np


class RegimeDetector:
    def detect(self, returns: Union[list, np.ndarray]) -> str:
        returns = np.asarray(returns, dtype=float)
        if returns.size < 2:
            return "sideways"
        vol = float(np.std(returns))
        trend = float(np.mean(returns))
        if trend > 0.001 and vol < 0.02:
            return "bull"
        if trend < -0.001 and vol > 0.03:
            return "bear"
        if vol > 0.025:
            return "high_vol"
        if vol < 0.01:
            return "low_vol"
        return "sideways"
