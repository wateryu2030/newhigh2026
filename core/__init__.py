# -*- coding: utf-8 -*-
"""核心模块：信号生成、趋势预测"""

from .signals import generate_signals
from .prediction import predict_trend

__all__ = ["generate_signals", "predict_trend"]
