# -*- coding: utf-8 -*-
"""
游资策略信号：龙虎榜共振 + 资金评分 > 60。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from core.lhb_engine import get_dragon_lhb_pool, lhb_resonance, lhb_yz_score, fetch_lhb_detail


def yz_signal_for_date(
    date_ymd: str,
    symbol: Optional[str] = None,
    emotion_cycle: Optional[str] = None,
    fund_score_min: int = 60,
) -> Dict[str, Any]:
    """
    当日游资信号：龙虎榜共振 + 资金评分。
    :param date_ymd: YYYYMMDD
    :param symbol: 若指定，检查该股是否在共振池
    :param emotion_cycle: 情绪周期，仅 启动/加速 时允许
    :param fund_score_min: 资金评分下限
    :return: {"lhb_score", "fund_score", "resonance", "in_resonance", "passed"}
    """
    pool = get_dragon_lhb_pool(date_ymd=date_ymd, emotion_cycle=emotion_cycle, only_when_emotion_ok=False)
    lhb_score = pool.get("lhb_score", 0) or 0
    resonance_list = pool.get("resonance_list") or []
    # 资金评分用 lhb_score 近似（实际可接单独资金流指标）
    fund_score = min(100, max(0, int(lhb_score / 2))) if lhb_score else 0
    in_resonance = False
    if symbol:
        sym = (symbol or "").strip()
        sym6 = sym.split(".")[0] if "." in sym else sym[:6]
        for r in resonance_list:
            if (r.get("symbol") or "").strip().startswith(sym6) or sym6 in (r.get("symbol") or ""):
                in_resonance = True
                break
    passed = fund_score >= fund_score_min and (in_resonance or (lhb_score >= 40 and len(resonance_list) > 0))
    return {
        "lhb_score": round(float(lhb_score), 1),
        "fund_score": fund_score,
        "resonance_count": len(resonance_list),
        "in_resonance": in_resonance,
        "passed": passed,
    }


def yz_signal_for_symbol_date(
    date_ymd: str,
    symbol: str,
    lhb_df: Any = None,
    emotion_cycle: Optional[str] = None,
    fund_score_min: int = 60,
) -> Dict[str, Any]:
    """
    单只股票当日游资信号（可传入已抓的 lhb_df 避免重复请求）。
    """
    if lhb_df is not None:
        score, _ = lhb_yz_score(lhb_df)
        resonance = lhb_resonance(lhb_df)
        fund_score = min(100, max(0, int(score / 2)))
        sym6 = (symbol.split(".")[0] if "." in symbol else symbol)[:6]
        in_resonance = any((r.get("symbol") or "").strip().startswith(sym6) for r in resonance)
    else:
        out = yz_signal_for_date(date_ymd, symbol=symbol, emotion_cycle=emotion_cycle, fund_score_min=fund_score_min)
        return out
    passed = fund_score >= fund_score_min and in_resonance
    return {
        "lhb_score": round(float(score), 1),
        "fund_score": fund_score,
        "resonance_count": len(resonance),
        "in_resonance": in_resonance,
        "passed": passed,
    }
