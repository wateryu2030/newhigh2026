# -*- coding: utf-8 -*-
"""
市场 Agent：基于指数数据判断市场趋势与建议仓位。
输入：市场指数数据（DuckDB）
输出：market_trend, risk_level, recommended_position
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 默认使用沪深300指数；DuckDB 中可能为 000300.XSHG 或 510300
DEFAULT_INDEX_IDS = ["000300.XSHG", "000300", "510300.XSHG", "510300"]


def _get_db():
    """获取数据库后端（DuckDB 优先），不破坏现有交易代码。"""
    try:
        from database.duckdb_backend import get_db_backend
        return get_db_backend()
    except Exception as e:
        logger.warning("DuckDB backend not available: %s", e)
    return None


def _load_index_from_akshare(days: int = 120) -> Optional[Any]:
    """DuckDB 无指数时从 akshare 拉取：先试沪深300指数接口，再试 510300 ETF。"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_dt = datetime.now() - timedelta(days=days)
    start_date = start_dt.strftime("%Y-%m-%d")
    try:
        import akshare as ak
        # 沪深300 指数需用指数日线接口，symbol 为 sh000300
        if hasattr(ak, "stock_zh_index_daily"):
            df = ak.stock_zh_index_daily(symbol="sh000300")
            if df is not None and len(df) >= 60:
                df = df.copy()
                if "date" not in df.columns and "日期" in df.columns:
                    df["date"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
                elif "date" not in df.columns and hasattr(df, "index"):
                    df["date"] = pd.to_datetime(df.index).astype(str).str[:10]
                elif "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                if "close" not in df.columns and "收盘" in df.columns:
                    df["close"] = df["收盘"].astype(float)
                if "volume" not in df.columns and "成交量" in df.columns:
                    df["volume"] = df["成交量"].astype(float)
                if "date" in df.columns:
                    df = df[df["date"] >= start_date]
                    df = df[df["date"] <= end_date].tail(days + 10)
                if len(df) >= 60:
                    logger.info("Index data loaded from akshare: 000300 (%d bars)", len(df))
                    return df
    except Exception as e:
        logger.debug("akshare index 000300 failed: %s", e)
    try:
        from data.data_loader import load_kline
        for sym in ["510300", "000300"]:
            df = load_kline(sym, start_date, end_date, source="akshare")
            if df is not None and len(df) >= 60:
                if "date" not in df.columns and df.index is not None:
                    df = df.copy()
                    df["date"] = df.index.astype(str).str[:10]
                logger.info("Index data loaded from akshare: %s (%d bars)", sym, len(df))
                return df
    except Exception as e:
        logger.debug("Index akshare ETF fallback failed: %s", e)
    return None


def _load_index_data(days: int = 120, use_akshare_fallback: bool = True) -> Optional[Any]:
    """从 DuckDB 加载指数 K 线；无数据时可选从 akshare 拉取。"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    db = _get_db()
    if db is not None and getattr(db, "db_path", None) and os.path.exists(getattr(db, "db_path", "")):
        for oid in DEFAULT_INDEX_IDS:
            try:
                df = db.get_daily_bars(oid, start_date, end_date)
                if df is not None and len(df) >= 60:
                    return df
            except Exception:
                continue
    if use_akshare_fallback:
        return _load_index_from_akshare(days)
    return None


def _series(df: Any, col: str):
    """从 DataFrame 取列，支持 index 为日期。"""
    if hasattr(df, "columns") and col in df.columns:
        return df[col].astype(float)
    if col == "close" and hasattr(df, "close"):
        return df.close.astype(float)
    return None


class MarketAgent:
    """
    市场判断 Agent。
    计算指数 MA 趋势、波动率、成交量变化、动量，返回市场状态与建议仓位。
    """

    def __init__(
        self,
        index_days: int = 120,
        ma_short: int = 20,
        ma_long: int = 60,
    ) -> None:
        self.index_days = index_days
        self.ma_short = ma_short
        self.ma_long = ma_long

    def run(self, index_df: Optional[Any] = None) -> Dict[str, Any]:
        """
        执行市场判断。
        :param index_df: 可选，指数 K 线（含 close, volume）；None 则从 DuckDB 加载。
        :return: {"market_trend": "bullish"|"bearish"|"neutral", "risk_level": 0-1, "recommended_position": 0-1}
        """
        out: Dict[str, Any] = {
            "market_trend": "neutral",
            "risk_level": 0.5,
            "recommended_position": 0.5,
        }
        try:
            if index_df is None:
                index_df = _load_index_data(self.index_days, use_akshare_fallback=True)
            if index_df is None or len(index_df) < self.ma_long:
                logger.warning("Insufficient index data for market agent")
                return out

            close = _series(index_df, "close")
            volume = _series(index_df, "volume")
            if close is None or len(close) < self.ma_long:
                return out

            # MA 趋势
            ma_short = close.rolling(self.ma_short, min_periods=self.ma_short).mean()
            ma_long = close.rolling(self.ma_long, min_periods=self.ma_long).mean()
            last = close.iloc[-1]
            last_ma_s = ma_short.iloc[-1] if len(ma_short.dropna()) else last
            last_ma_l = ma_long.iloc[-1] if len(ma_long.dropna()) else last
            if last > last_ma_s and last > last_ma_l:
                out["market_trend"] = "bullish"
            elif last < last_ma_s and last < last_ma_l:
                out["market_trend"] = "bearish"
            else:
                out["market_trend"] = "neutral"

            # 波动率：20 日收益年化波动率
            ret = close.pct_change().dropna()
            if len(ret) >= 20:
                vol_20 = ret.iloc[-20:].std() * (252 ** 0.5)
                out["risk_level"] = float(np.clip(vol_20 * 3, 0.0, 1.0))  # 粗略映射到 0-1
            else:
                out["risk_level"] = 0.5

            # 成交量变化：近期 vs 前期
            if volume is not None and len(volume) >= 20:
                vol_recent = volume.iloc[-5:].mean()
                vol_prev = volume.iloc[-20:-5].mean()
                if vol_prev and vol_prev > 0:
                    vol_ratio = vol_recent / vol_prev
                    if vol_ratio > 1.2 and out["market_trend"] == "bullish":
                        out["risk_level"] = min(1.0, out["risk_level"] * 0.9)
                    elif vol_ratio > 1.2 and out["market_trend"] == "bearish":
                        out["risk_level"] = min(1.0, out["risk_level"] * 1.1)

            # 动量：20 日收益率
            if len(close) >= 20:
                momentum = (close.iloc[-1] / close.iloc[-20] - 1.0) if close.iloc[-20] else 0.0
                if momentum > 0.03:
                    out["market_trend"] = "bullish" if out["market_trend"] == "neutral" else out["market_trend"]
                elif momentum < -0.03:
                    out["market_trend"] = "bearish" if out["market_trend"] == "neutral" else out["market_trend"]

            # 建议仓位：牛高、熊低、中性中
            if out["market_trend"] == "bullish":
                out["recommended_position"] = float(np.clip(0.7 - out["risk_level"] * 0.2, 0.3, 0.9))
            elif out["market_trend"] == "bearish":
                out["recommended_position"] = float(np.clip(0.2 - out["risk_level"] * 0.1, 0.05, 0.4))
            else:
                out["recommended_position"] = float(np.clip(0.5 - out["risk_level"] * 0.2, 0.2, 0.7))

        except Exception as e:
            logger.exception("MarketAgent run error: %s", e)
        return out
