# -*- coding: utf-8 -*-
"""
信号引擎：根据行情数据生成买卖信号及置信度。
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd


def generate_signals(market_data: Any) -> List[Dict[str, Any]]:
    """
    根据市场数据生成交易信号列表。
    market_data: 可为 dict(symbols -> DataFrame 日线)、或 list of symbol、或 DataFrame（多标的合并）。
    返回: [{"symbol": "000001", "action": "BUY", "confidence": 0.82}, ...]
    """
    result: List[Dict[str, Any]] = []
    try:
        from strategies import get_plugin_strategy
        from core.timeframe import resample_kline, normalize_timeframe
    except ImportError:
        return result

    strategy = get_plugin_strategy("ma_cross") or get_plugin_strategy("rsi") or get_plugin_strategy("macd")
    if strategy is None:
        return result

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

    if isinstance(market_data, dict):
        symbols_items = list(market_data.items())
    elif isinstance(market_data, list):
        symbols_items = [(s, None) for s in market_data]
    else:
        return result

    import os
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        has_db = getattr(db, "db_path", None) and os.path.exists(getattr(db, "db_path", ""))
    except Exception:
        has_db = False
        db = None

    for key, df in symbols_items:
        symbol = key if isinstance(key, str) else str(key)
        order_book_id = symbol if "." in symbol else (symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE")
        if df is None or (isinstance(df, pd.DataFrame) and len(df) < 20):
            if has_db and db is not None:
                df = db.get_daily_bars(order_book_id, start_date, end_date)
            else:
                continue
        if df is None or len(df) < 20:
            continue
        df = df.copy()
        df = resample_kline(df, normalize_timeframe("D"))
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        signals = strategy.generate_signals(df)
        if not signals:
            continue
        last = signals[-1]
        last_bar_date = str(df["date"].iloc[-1])[:10]
        if last.get("date") != last_bar_date:
            continue
        action = (last.get("type") or "BUY").upper()
        if action not in ("BUY", "SELL"):
            continue
        confidence = 0.75
        try:
            from backend.ai.predict_service import predict_stock
            pred = predict_stock(order_book_id)
            if action == "BUY":
                confidence = pred.get("buy_prob", 0.75)
            else:
                confidence = pred.get("sell_prob", 0.75)
        except Exception:
            pass
        result.append({
            "symbol": symbol.split(".")[0] if "." in symbol else symbol,
            "action": action,
            "confidence": round(float(confidence), 4),
        })
    return result
