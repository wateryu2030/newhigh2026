# -*- coding: utf-8 -*-
"""
多策略组合：按权重合并多策略净值与信号，输出与单策略回测一致的数据结构。
"""
import os
import sys
from typing import List, Dict, Any, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def _normalize_weights(weights: List[float]) -> List[float]:
    """归一化权重为和 1。"""
    s = sum(weights)
    if s <= 0:
        return [1.0 / len(weights)] * len(weights)
    return [w / s for w in weights]


def aggregate_curves(
    curves: List[List[Dict[str, Any]]],
    weights: List[float],
) -> List[Dict[str, Any]]:
    """
    按权重合并多条净值曲线（每条为 [{ date, value }, ...]）。
    日期取所有曲线的并集，缺失日期用前值前向填充；组合净值 = 各曲线当日净值 * 权重 之和。
    """
    if not curves or not weights:
        return []
    weights = _normalize_weights(weights[:len(curves)])
    if len(curves) != len(weights):
        weights = _normalize_weights(weights + [1.0] * (len(curves) - len(weights)))

    # 日期并集、按日期排序
    all_dates = set()
    for c in curves:
        for p in c:
            d = p.get("date")
            if d:
                all_dates.add(str(d)[:10])
    sorted_dates = sorted(all_dates)

    # 每条曲线按日期建 map，前向填充
    def curve_to_map(c: List[Dict[str, Any]]) -> Dict[str, float]:
        m = {}
        last = 1.0
        for p in c:
            d = str(p.get("date", ""))[:10]
            v = p.get("value")
            if v is not None and v == v:
                last = float(v)
            m[d] = last
        return m

    maps = [curve_to_map(c) for c in curves]
    combined = []
    for d in sorted_dates:
        val = 0.0
        for i, m in enumerate(maps):
            v = m.get(d)
            if v is None and combined:
                v = maps[i].get(combined[-1]["date"], 1.0)
            if v is None:
                v = 1.0
            val += weights[i] * v
        combined.append({"date": d, "value": round(val, 6)})
    return combined


def run_portfolio_backtest(
    strategies: List[Dict[str, Any]],
    stock_code: str,
    start_date: str,
    end_date: str,
    timeframe: str = "D",
) -> Dict[str, Any]:
    """
    多策略组合回测。

    :param strategies: [
          {"strategy_id": "ma_cross", "weight": 0.5, "symbol": null},
          {"strategy_id": "rsi", "weight": 0.5, "symbol": null}
        ]，symbol 为 None 时使用 stock_code
    :param stock_code: 默认标的
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param timeframe: D / W / M
    :return: 与 run_plugin_backtest 同构的 result（curve 为组合曲线，kline 取第一策略，signals/markers 合并）
    """
    from run_backtest_plugins import run_plugin_backtest

    if not strategies:
        return {"error": "策略列表为空", "curve": [], "holdCurve": [], "kline": []}

    weights = _normalize_weights([s.get("weight", 1.0) for s in strategies])
    curves = []
    all_signals = []
    all_markers = []
    kline = []
    hold_curve = []
    strategy_names = []

    for i, cfg in enumerate(strategies):
        sid = cfg.get("strategy_id")
        sym = cfg.get("symbol") or stock_code
        w = weights[i] if i < len(weights) else 1.0 / len(strategies)
        if not sid:
            continue
        result = run_plugin_backtest(sid, sym, start_date, end_date, timeframe=timeframe)
        if result.get("error"):
            continue
        curves.append(result.get("curve") or [])
        strategy_names.append(result.get("strategy_name") or sid)
        if not kline and result.get("kline"):
            kline = result.get("kline", [])
        if not hold_curve and result.get("holdCurve"):
            hold_curve = result.get("holdCurve", [])
        for sig in result.get("signals") or []:
            all_signals.append({**sig, "strategy_id": sid})
        for m in result.get("markers") or []:
            all_markers.append({**m, "strategy_id": sid})

    if not curves:
        return {"error": "无有效策略结果", "curve": [], "holdCurve": [], "kline": []}

    combined_curve = aggregate_curves(curves, weights)
    # 组合净值统计
    final_nav = combined_curve[-1]["value"] if combined_curve else 1.0
    total_return = final_nav - 1.0
    peak = 1.0
    max_dd = 0.0
    for p in combined_curve:
        v = p["value"]
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

    out = {
        "summary": {"total_returns": total_return, "return_rate": total_return, "max_drawdown": max_dd},
        "curve": combined_curve,
        "holdCurve": hold_curve or combined_curve,
        "kline": kline,
        "signals": all_signals,
        "markers": all_markers,
        "stats": {
            "tradeCount": len(all_signals),
            "winRate": None,
            "maxDrawdown": max_dd,
            "return": total_return,
        },
        "prediction": {"trend": "SIDEWAYS", "score": 0.0},
        "buyZones": [],
        "sellZones": [],
        "futureProbability": {"up": None, "sideways": None, "down": None},
        "futurePriceRange": {"low": None, "high": None, "horizonDays": 5},
        "strategy_name": "组合(" + "+".join(strategy_names[:3]) + (")" if len(strategy_names) <= 3 else "...)"),
        "timeframe": timeframe,
        "portfolio_weights": [{"strategy_id": s.get("strategy_id"), "weight": weights[i]} for i, s in enumerate(strategies) if i < len(weights)],
    }

    try:
        from core.scoring import score_strategy
        sc, gr = score_strategy(out["stats"])
        out["strategy_score"] = sc
        out["strategy_grade"] = gr
    except Exception:
        out["strategy_score"] = None
        out["strategy_grade"] = None

    return out
