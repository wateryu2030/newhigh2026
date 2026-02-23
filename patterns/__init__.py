# -*- coding: utf-8 -*-
"""
技术形态识别引擎：趋势类、反转类、量价类形态。
"""
from .pattern_engine import PatternEngine
from .trend_patterns import (
    detect_multi_ma_bull,
    detect_uptrend_channel,
    detect_breakout_platform,
    detect_new_high_breakout,
    detect_ma_converge_divergence,
)
from .reversal_patterns import (
    detect_double_bottom,
    detect_v_reversal,
    detect_oversold_bounce,
)
from .volume_patterns import (
    detect_volume_breakout,
    detect_volume_pullback,
    detect_volume_accumulation,
)

__all__ = [
    "PatternEngine",
    "detect_multi_ma_bull",
    "detect_uptrend_channel",
    "detect_breakout_platform",
    "detect_new_high_breakout",
    "detect_ma_converge_divergence",
    "detect_double_bottom",
    "detect_v_reversal",
    "detect_oversold_bounce",
    "detect_volume_breakout",
    "detect_volume_pullback",
    "detect_volume_accumulation",
]
