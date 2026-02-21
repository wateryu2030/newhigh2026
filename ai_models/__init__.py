# -*- coding: utf-8 -*-
"""
AI 选股与信号评分：因子工程、XGBoost 训练/预测、信号排序、模型管理。
"""
from .feature_engineering import build_features_for_symbol, build_features_multi
from .dataset_builder import build_dataset, build_dataset_from_market_data, get_feature_columns
from .model_trainer import ModelTrainer
from .model_predictor import ModelPredictor
from .signal_ranker import rank_signals, top_n_symbols
from .model_manager import ModelManager

try:
    from .lstm_model import LSTMModel
except Exception:
    LSTMModel = None  # type: ignore

__all__ = [
    "build_features_for_symbol",
    "build_features_multi",
    "build_dataset",
    "build_dataset_from_market_data",
    "get_feature_columns",
    "ModelTrainer",
    "ModelPredictor",
    "rank_signals",
    "top_n_symbols",
    "ModelManager",
    "LSTMModel",
]
