"""
AI 层模块

提供 AI 模型、策略生成、优化功能。

架构:
    lib/           ← 基础设施
    core/          ← 核心服务
    data/          ← 数据层
    ai/            ← AI 层 (本模块)
    scanner/       ← 扫描器
    strategy/      ← 策略引擎
"""

__version__ = "1.0.0"

# 导出主要类
from .emotion_cycle_model import EmotionCycleModel
from .hotmoney_detector import HotMoneyAnalyzer
from .sector_rotation_ai import SectorRotationAI
from .lstm_price_predictor import LSTMPricePredictor, PredictionResult

__all__ = [
    "EmotionCycleModel",
    "HotMoneyAnalyzer",
    "SectorRotationAI",
    "LSTMPricePredictor",
    "PredictionResult",
]
