# -*- coding: utf-8 -*-
"""
TradingView 级 K 线图数据结构支持。
统一：单根 K 线、系列、指标叠加、与回测 result.kline 的转换，便于专业图表组件消费。
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class TvKlineBar:
    """
    单根 K 线（TradingView 兼容）。
    time: 时间，建议 ISO 日期字符串 "YYYY-MM-DD" 或 Unix 秒
    open, high, low, close: 价格
    volume: 成交量，可选
    """

    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def to_list(self) -> List[Any]:
        """转为 [time, o, h, l, c] 或 [time, o, h, l, c, v]，供 lightweight-charts 等。"""
        return [self.time, self.open, self.high, self.low, self.close, self.volume]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TvKlineSeries:
    """
    K 线序列 + 可选指标线，TradingView 图表可直接使用。
    """

    bars: List[TvKlineBar] = field(default_factory=list)
    indicators: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    """指标名 -> [{ time, value }, ...]"""
    markers: List[Dict[str, Any]] = field(default_factory=list)
    """标注点：{ time, position, shape, color, text }"""

    def to_chart_payload(self) -> Dict[str, Any]:
        """
        导出为前端图表库通用结构（如 ECharts / lightweight-charts 可再转换）。
        """
        return {
            "bars": [b.to_dict() for b in self.bars],
            "bars_array": [b.to_list() for b in self.bars],
            "indicators": self.indicators,
            "markers": self.markers,
        }


def from_backtest_kline(kline: List[Dict[str, Any]]) -> List[TvKlineBar]:
    """
    将回测 result.kline（[{ date, open, high, low, close, volume? }]）转为 TvKlineBar 列表。
    """
    out: List[TvKlineBar] = []
    for k in kline or []:
        t = str(k.get("date", ""))[:10]
        o = float(k.get("open", 0))
        h = float(k.get("high", 0))
        l = float(k.get("low", 0))
        c = float(k.get("close", 0))
        v = float(k.get("volume", 0))
        out.append(TvKlineBar(time=t, open=o, high=h, low=l, close=c, volume=v))
    return out


def from_backtest_result(
    result: Dict[str, Any],
    include_markers: bool = True,
) -> TvKlineSeries:
    """
    从回测结果构建 TradingView 级 K 线序列（含买卖点标注）。
    :param result: run_backtest 返回的 result（含 kline, markers）
    :param include_markers: 是否把 markers 转为图表标注
    """
    bars = from_backtest_kline(result.get("kline") or [])
    indicators: Dict[str, List[Dict[str, Any]]] = {}
    markers: List[Dict[str, Any]] = []

    if include_markers and result.get("markers"):
        for m in result["markers"]:
            coord = m.get("coord")
            if not coord or len(coord) < 2:
                continue
            t = str(coord[0])[:10]
            is_buy = (m.get("name") or "").upper() == "BUY"
            markers.append({
                "time": t,
                "position": "belowBar" if is_buy else "aboveBar",
                "shape": "arrowUp" if is_buy else "arrowDown",
                "color": "#00d68f" if is_buy else "#ff6b6b",
                "text": m.get("reason") or (m.get("name") or ""),
            })

    return TvKlineSeries(bars=bars, indicators=indicators, markers=markers)


def to_tv_series_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷接口：回测 result 直接转为前端可用的 TradingView 数据结构。
    """
    series = from_backtest_result(result, include_markers=True)
    return series.to_chart_payload()


def convert_to_tv(
    df: Any,
    date_col: str = "date",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    markers: Optional[List[Dict[str, Any]]] = None,
    indicators: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    将 DataFrame 转为 TradingView / Lightweight Charts 兼容格式。
    :param df: 行情 DataFrame，需含 date/open/high/low/close/volume（或自定义列名）
    :param date_col, open_col, ...: 列名映射
    :param markers: 可选标注 [{ time, position, shape, color, text }, ...]
    :param indicators: 可选指标 { "ma5": [{ time, value }, ...], ... }
    :return: { "candles": [], "markers": [], "indicators": {} }
    """
    import pandas as pd
    candles = []
    if df is not None and hasattr(df, "iterrows"):
        for _, row in df.iterrows():
            t = str(row.get(date_col, ""))[:10]
            o = float(row.get(open_col, 0))
            h = float(row.get(high_col, 0))
            l_ = float(row.get(low_col, 0))
            c = float(row.get(close_col, 0))
            v = float(row.get(volume_col, 0))
            candles.append({
                "time": t,
                "open": o,
                "high": h,
                "low": l_,
                "close": c,
                "volume": v,
            })
    return {
        "candles": candles,
        "markers": list(markers) if markers else [],
        "indicators": dict(indicators) if indicators else {},
    }
