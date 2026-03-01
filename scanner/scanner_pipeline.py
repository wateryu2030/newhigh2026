# -*- coding: utf-8 -*-
"""
专业级扫描流水线：全市场扫描 → 技术形态过滤 → 热点过滤 → 风险过滤 → AI评分排序。
输出：股票、买点概率、风险等级、建议仓位、策略类型。
"""
from __future__ import annotations
import os
import sys
from typing import Any, Callable, Dict, List, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def run_professional_scan(
    strategy_ids: Optional[List[str]] = None,
    use_pattern_filter: bool = True,
    use_hot_filter: bool = True,
    use_risk_budget: bool = True,
    use_ai_rank: bool = True,
    capital: float = 1_000_000,
    risk_pct: float = 0.01,
    stop_loss_pct: float = 0.05,
    top_n: int = 50,
    stock_limit: int = 500,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> List[Dict[str, Any]]:
    """
    专业级扫描流水线。仅使用本地 DuckDB K 线，不触发 AKShare 网络下载，保证速度。
    :param strategy_ids: 参与的策略 id 列表；None 则用 ma_cross, rsi, macd, breakout
    :param use_pattern_filter: 是否用形态引擎过滤（pattern_score>=1）
    :param use_hot_filter: 是否用热点强度过滤（可选）
    :param use_risk_budget: 是否计算建议仓位（风险预算）
    :param use_ai_rank: 是否用 AI 评分参与排序
    :param capital: 总资金（用于建议仓位）
    :param risk_pct: 单笔风险比例
    :param stop_loss_pct: 止损幅度
    :param top_n: 返回前 N 只
    :param stock_limit: 扫描股票数量上限
    :return: [{"symbol", "name", "signal", "price", "buy_prob", "risk_level", "suggest_position_pct", "strategy_type", "pattern_tags", "hot_strength"}, ...]
    """
    from datetime import datetime, timedelta
    from scanner import scan_market, scan_market_portfolio
    from patterns import PatternEngine
    from market import get_hot_strength
    from risk import position_size

    def _progress(phase: str, current: int, total: int, message: str) -> None:
        if progress_callback:
            progress_callback(phase, current, total, message)

    if strategy_ids is None:
        strategy_ids = ["ma_cross", "rsi", "macd", "breakout"]
    strategies = [{"strategy_id": s, "weight": 1.0} for s in strategy_ids]
    _progress("scan", 0, 1, "正在扫描市场（约 %d 只）…" % stock_limit)
    raw = scan_market_portfolio(strategies=strategies, timeframe="D", limit=stock_limit)
    _progress("scan", 1, 1, "扫描完成，共 %d 只" % (len(raw) or 0))
    if not raw:
        _progress("done", 0, 0, "无信号标的")
        return []

    pattern_engine = PatternEngine()
    results = []
    total_raw = len(raw)
    for i, r in enumerate(raw):
        symbol = (r.get("symbol") or "").split(".")[0]
        if not symbol:
            continue
        # 形态过滤（仅用本地数据库 K 线，不触发网络下载）
        pattern_score = 0
        pattern_tags = ""
        hot_strength = 50.0
        try:
            from data.data_loader import load_kline
            end = datetime.now().date()
            start = (end - timedelta(days=120)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            df = load_kline(symbol, start, end_str, source="database")
            if df is not None and len(df) >= 60:
                pat = pattern_engine.get_latest_patterns(df)
                pattern_score = pat.get("score", 0)
                pattern_tags = ",".join(pat.get("tags", []))
                if use_pattern_filter and pattern_score < 1:
                    continue
            elif use_pattern_filter:
                continue  # 本地无足够数据则跳过，不拉取 akshare
            if use_hot_filter:
                try:
                    hot_strength = get_hot_strength(symbol)
                except Exception:
                    hot_strength = 50.0
        except Exception:
            if use_pattern_filter:
                continue
            pass

        # 风险等级：简单用波动/止损推断
        risk_level = "NORMAL"
        suggest_pct = 0.0
        if use_risk_budget and stop_loss_pct > 0:
            _, ratio = position_size(capital, risk_pct, stop_loss_pct)
            suggest_pct = ratio * 100
            if suggest_pct > 15:
                risk_level = "LOW"
            elif suggest_pct < 5:
                risk_level = "HIGH"

        if (i + 1) % 50 == 0 or i == total_raw - 1:
            _progress("pattern", i + 1, total_raw, "形态/热点过滤 %d/%d" % (i + 1, total_raw))
        buy_prob = min(99, 50 + pattern_score * 5 + (hot_strength - 50) * 0.2)
        results.append({
            "symbol": r.get("symbol", symbol),
            "name": r.get("name", symbol),
            "signal": r.get("signal", "BUY"),
            "price": r.get("price"),
            "date": r.get("date"),
            "reason": r.get("reason", ""),
            "buy_prob": round(buy_prob, 1),
            "risk_level": risk_level,
            "suggest_position_pct": round(suggest_pct, 2),
            "strategy_type": "多策略共振",
            "pattern_tags": pattern_tags,
            "pattern_score": pattern_score,
            "hot_strength": round(hot_strength, 1),
        })

    # AI 排序（可选，仅用本地数据库，不触发网络下载）
    if use_ai_rank and results:
        try:
            _progress("ai", 0, min(200, len(results)), "AI 排序准备…")
            from ai_models.model_manager import ModelManager
            from data.data_loader import load_kline
            market_data = {}
            end = datetime.now().date()
            start = (end - timedelta(days=250)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            to_load = results[:200]
            for ai_i, r in enumerate(to_load):
                sym = (r.get("symbol") or "").split(".")[0]
                if not sym:
                    continue
                df = load_kline(sym, start, end_str, source="database")
                if df is not None and len(df) >= 60:
                    key = sym + ".XSHG" if sym.startswith("6") else sym + ".XSHE"
                    market_data[key] = df
                if (ai_i + 1) % 30 == 0 or ai_i == len(to_load) - 1:
                    _progress("ai", ai_i + 1, len(to_load), "AI 加载数据 %d/%d" % (ai_i + 1, len(to_load)))
            _progress("ai", len(to_load), len(to_load), "AI 评分中…")
            if market_data:
                mm = ModelManager()
                ai_scores = mm.predict(market_data)
                if ai_scores is not None and not ai_scores.empty and "symbol" in ai_scores.columns:
                    score_map = {}
                    for _, row in ai_scores.iterrows():
                        score_map[str(row["symbol"])] = float(row.get("score", 0.5))
                    for r in results:
                        s = r.get("symbol", "")
                        r["ai_score"] = round(score_map.get(s, 0.5), 4)
                        r["buy_prob"] = round(min(99, r["buy_prob"] * 0.6 + score_map.get(s, 0.5) * 100 * 0.4), 1)
        except Exception:
            pass

    # 按买点概率降序
    results.sort(key=lambda x: (x.get("buy_prob", 0), x.get("pattern_score", 0)), reverse=True)
    out = results[:top_n]
    _progress("done", len(out), len(out), "完成，共 %d 只" % len(out))
    return out
