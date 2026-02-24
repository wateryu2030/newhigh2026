# -*- coding: utf-8 -*-
"""
选股 Agent：基于因子与技术指标对股票评分。
输入：股票因子/技术指标（可从 DuckDB 与 data_loader 获取）
输出：[{code, score}, ...]，支持未来接入 AI 模型。
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_db():
    """获取数据库后端。"""
    try:
        from database.duckdb_backend import get_db_backend
        return get_db_backend()
    except Exception:
        return None


def _load_kline(symbol: str, days: int = 120, use_akshare_fallback: bool = True) -> Optional[Any]:
    """加载单只股票 K 线；数据库无数据时可选从 akshare 拉取（演示用）。"""
    try:
        from data.data_loader import load_kline
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = load_kline(symbol, start, end, source="database")
        if df is not None and len(df) >= 20:
            return df
        if use_akshare_fallback:
            df = load_kline(symbol, start, end, source="akshare")
            if df is not None and len(df) >= 20:
                return df
    except Exception:
        pass
    return None


def _close_series(df: Any):
    if df is None or len(df) == 0:
        return None
    if hasattr(df, "columns"):
        if "close" in df.columns:
            return df["close"].astype(float)
        if "收盘" in df.columns:
            return df["收盘"].astype(float)
    return None


def _volume_series(df: Any):
    if df is None or len(df) == 0:
        return None
    if hasattr(df, "columns"):
        if "volume" in df.columns:
            return df["volume"].astype(float)
        if "成交量" in df.columns:
            return df["成交量"].astype(float)
    return None


def _compute_rsi(close: Any, period: int = 14) -> float:
    """RSI 强弱指标，返回 0-100。"""
    if close is None or len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean().iloc[-1] if len(gain) else 0.0
    avg_loss = loss.rolling(period).mean().iloc[-1] if len(loss) else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _score_one(symbol: str, df: Any) -> float:
    """
    单只股票评分：动量、均线趋势、成交量、波动率、RSI。
    返回 0-1 综合得分，支持未来替换为 AI 模型输出。
    """
    close = _close_series(df)
    volume = _volume_series(df)
    if close is None or len(close) < 20:
        return 0.0
    scores = []
    # 动量：20 日收益率，归一化到 0-1（假设 -0.2~0.2 映射 0~1）
    ret_20 = (close.iloc[-1] / close.iloc[-20] - 1.0) if close.iloc[-20] else 0.0
    momentum_score = (ret_20 + 0.2) / 0.4
    scores.append(max(0.0, min(1.0, momentum_score)))

    # 均线趋势：价格在 MA20 上方为正
    ma20 = close.rolling(20, min_periods=20).mean()
    if len(ma20.dropna()) > 0:
        above_ma = 1.0 if close.iloc[-1] >= ma20.iloc[-1] else 0.3
        scores.append(above_ma)

    # 成交量：近期放量加分（简化：近5日/前5日比）
    if volume is not None and len(volume) >= 10:
        v_recent = volume.iloc[-5:].mean()
        v_prev = volume.iloc[-10:-5].mean()
        if v_prev and v_prev > 0:
            vol_ratio = v_recent / v_prev
            vol_score = min(1.0, (vol_ratio - 0.5) / 1.0) if vol_ratio > 0.5 else 0.5
            scores.append(max(0.0, vol_score))
        else:
            scores.append(0.5)
    else:
        scores.append(0.5)

    # 波动率：低波动略加分（稳定性）
    ret = close.pct_change().dropna()
    if len(ret) >= 20:
        vol = ret.iloc[-20:].std()
        vol_score = 1.0 - min(1.0, vol * 20)  # 粗略
        scores.append(max(0.0, vol_score))
    else:
        scores.append(0.5)

    # RSI：30-70 区间加分，极端超买超卖减分
    rsi = _compute_rsi(close, 14)
    if rsi >= 30 and rsi <= 70:
        rsi_score = 0.9
    elif rsi < 25 or rsi > 75:
        rsi_score = 0.4
    else:
        rsi_score = 0.7
    scores.append(rsi_score)

    return float(sum(scores) / len(scores)) if scores else 0.0


class StockAgent:
    """
    选股 Agent。根据动量、均线、成交量、波动率、RSI 对股票评分。
    可扩展：接入 AI 模型替代 _score_one。
    """

    def __init__(
        self,
        lookback_days: int = 120,
        max_stocks: int = 100,
    ) -> None:
        self.lookback_days = lookback_days
        self.max_stocks = max_stocks

    def run(
        self,
        symbols: Optional[List[str]] = None,
        stock_limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        对股票列表评分。
        :param symbols: 候选代码列表；None 时从数据库取前 N 只。
        :param stock_limit: 最多评分数量。
        :return: [{"code": "600519", "score": 0.82}, ...]，按 score 降序。
        """
        limit = stock_limit or self.max_stocks
        try:
            if symbols is None:
                symbols = self._get_candidate_symbols(limit)
            if not symbols:
                logger.warning("StockAgent: no candidate symbols")
                return []

            results: List[Dict[str, Any]] = []
            for code in symbols[: limit * 2]:  # 多取一些，过滤后可能不足
                try:
                    df = _load_kline(code, self.lookback_days, use_akshare_fallback=getattr(self, "use_akshare_fallback", True))
                    score = _score_one(code, df)
                    results.append({"code": str(code).zfill(6), "score": round(score, 4)})
                except Exception as e:
                    logger.debug("StockAgent score skip %s: %s", code, e)
                    continue
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.exception("StockAgent run error: %s", e)
            return []

    def _get_candidate_symbols(self, limit: int) -> List[str]:
        """从数据库获取候选股票代码；若库为空则从 akshare 拉取列表。"""
        try:
            from data.stock_pool import get_a_share_symbols
            fallback = get_a_share_symbols(exclude_delisted=True)
        except Exception:
            fallback = []
        db = _get_db()
        if db is None or not os.path.exists(getattr(db, "db_path", "")):
            return fallback[:limit]
        try:
            rows = db.get_stocks()
            symbols = []
            for r in rows:
                sym = (r[1] if len(r) > 1 else r[0].split(".")[0])
                if sym and str(sym).isdigit():
                    symbols.append(str(sym).zfill(6))
            if symbols:
                return symbols[:limit]
            return fallback[:limit]
        except Exception:
            return fallback[:limit]
