# -*- coding: utf-8 -*-
"""
AI 预测服务：按标的拉取日线、构建特征、调用模型返回买/卖概率与评分、目标价/风险价。
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd

from .feature_engineering import build_features
from .ai_model import load_model, FEATURE_COLS


def _get_db():
    """使用项目已有 DuckDB/SQLite 数据源。"""
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        if getattr(db, "db_path", None) and os.path.exists(getattr(db, "db_path", "")):
            return db
    except Exception:
        pass
    return None


def _normalize_symbol(symbol: str) -> str:
    """若仅为 6 位代码，尝试补全交易所后缀。"""
    s = (symbol or "").strip()
    if not s or "." in s:
        return s
    if len(s) == 6 and s.isdigit():
        return s + ".XSHE"  # 默认深圳，可按需先查库
    return s


def predict_stock(symbol: str) -> Dict[str, Any]:
    """
    对单只股票做 AI 买卖点预测与评分。
    返回: buy_prob, sell_prob, score, target_price, risk_price
    """
    result = {
        "buy_prob": 0.5,
        "sell_prob": 0.5,
        "score": 50,
        "target_price": None,
        "risk_price": None,
    }
    symbol = _normalize_symbol(symbol)
    if not symbol:
        return result

    db = _get_db()
    if db is None:
        return result

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    df = db.get_daily_bars(symbol, start_date, end_date)
    if df is None or len(df) < 60:
        return result

    feature_df = build_features(df)
    if feature_df is None or len(feature_df) == 0:
        return result

    # 预测用最近一行（无未来收益），去掉目标列即可
    pred_df = feature_df.drop(columns=["forward_return_5d"], errors="ignore").tail(1)
    if len(pred_df) == 0:
        return result
    available = [c for c in FEATURE_COLS if c in pred_df.columns]
    if not available:
        return result

    model = load_model()
    if model is None:
        # 无模型时基于规则给一个简单分数
        last = feature_df.iloc[-1]
        rsi = last.get("RSI", 50)
        if rsi is not None and not (isinstance(rsi, float) and (rsi != rsi)):
            result["score"] = min(100, max(0, int(100 - abs(rsi - 50) * 0.5)))
        close = float(df["close"].iloc[-1])
        result["target_price"] = round(close * 1.03, 2)
        result["risk_price"] = round(close * 0.97, 2)
        return result

    X = pred_df[available].replace([float("inf"), float("-inf")], 0).fillna(0)
    try:
        proba = model.predict_proba(X)
        if proba is not None and len(proba) > 0:
            # 二分类：0 = 不涨超3%, 1 = 涨超3%
            if proba.shape[1] == 2:
                result["sell_prob"] = round(float(proba[0, 0]), 4)
                result["buy_prob"] = round(float(proba[0, 1]), 4)
            else:
                result["buy_prob"] = round(float(proba[0, -1]), 4)
                result["sell_prob"] = round(1 - result["buy_prob"], 4)
            result["score"] = min(100, max(0, int(result["buy_prob"] * 100)))
    except Exception:
        pass

    close = float(df["close"].iloc[-1])
    atr = feature_df["ATR"].iloc[-1] if "ATR" in feature_df.columns else close * 0.02
    result["target_price"] = round(close * 1.03, 2)
    result["risk_price"] = round(close - 2 * float(atr), 2)
    if result["risk_price"] <= 0:
        result["risk_price"] = round(close * 0.97, 2)
    return result
