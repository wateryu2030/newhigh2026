# -*- coding: utf-8 -*-
"""
Alpha 因子库：动量、波动率、量价、趋势、偏度峰度等，供选股与模型特征使用。
"""
from .alpha_factors import add_alpha_factors
from .factor_engine import build_factor_matrix

__all__ = ["add_alpha_factors", "build_factor_matrix"]
