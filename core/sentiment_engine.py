# -*- coding: utf-8 -*-
"""
AI 情绪周期识别引擎（生产级）。
A 股情绪五阶段：冰点 → 启动 → 加速 → 高潮 → 退潮/极致高潮。
每日收盘后基于涨停家数、连板高度、炸板率、市场成交额等量化计算。
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 情绪周期：与仓位纪律一致
EMOTION_CYCLES = ("冰点", "启动", "加速", "高潮", "极致高潮", "退潮")

# 仓位建议（与文档一致）
POSITION_BY_CYCLE = {
    "冰点": 0.2,
    "启动": 0.4,
    "加速": 0.6,
    "高潮": 0.5,
    "极致高潮": 0.3,
    "退潮": 0.1,
}


def fetch_zt_pool_data(date_ymd: str) -> Dict[str, Any]:
    """
    从 AKShare 拉取当日涨停池数据，用于计算涨停家数、连板高度、炸板率等。
    :param date_ymd: YYYYMMDD
    :return: {"limit_up_count", "max_board_height", "break_count", "break_rate", "total_volume", "raw_df_rows"}
    """
    out = {
        "limit_up_count": 0,
        "max_board_height": 0,
        "break_count": 0,
        "break_rate": 0.0,
        "total_volume": 0.0,
        "raw_df_rows": 0,
    }
    try:
        import akshare as ak
        # 涨停池：优先带日期的接口
        df = None
        for name in ("stock_zt_pool_em", "stock_zt_pool_previous_em"):
            func = getattr(ak, name, None)
            if not func:
                continue
            try:
                if "date" in (func.__doc__ or ""):
                    df = func(date=date_ymd)
                else:
                    df = func()
                if df is not None and len(df) > 0:
                    break
            except Exception as e:
                logger.debug("akshare %s(%s) failed: %s", name, date_ymd, e)
        if df is None or len(df) == 0:
            return out
        out["raw_df_rows"] = len(df)
        out["limit_up_count"] = len(df)
        # 连板高度：列名可能为 "连板数" / "连续涨停" / "连板天数"
        board_col = None
        for c in ("连板数", "连续涨停", "连板天数", "连板"):
            if c in df.columns:
                board_col = c
                break
        if board_col:
            try:
                heights = pd_to_numeric_series(df[board_col])
                if heights is not None and len(heights) > 0:
                    out["max_board_height"] = int(max(heights))
            except Exception:
                pass
        # 炸板：若接口返回炸板池或含“炸板”列则统计
        try:
            df_break = getattr(ak, "stock_zt_pool_dtgc_em", None)
            if df_break and callable(df_break):
                try:
                    br = df_break(date=date_ymd) if "date" in (df_break.__doc__ or "") else df_break()
                    if br is not None and hasattr(br, "__len__"):
                        out["break_count"] = len(br)
                except Exception:
                    pass
        except Exception:
            pass
        if out["limit_up_count"] > 0 and out["break_count"] >= 0:
            out["break_rate"] = round(out["break_count"] / (out["limit_up_count"] + out["break_count"] or 1), 4)
    except ImportError:
        logger.warning("akshare not installed, emotion data will use fallback")
    except Exception as e:
        logger.debug("fetch_zt_pool_data %s: %s", date_ymd, e)
    return out


def pd_to_numeric_series(s) -> Optional[List[float]]:
    """将 pandas 列转为数值列表，忽略无效值。"""
    try:
        import pandas as pd
        v = pd.to_numeric(s, errors="coerce").dropna()
        return v.astype(float).tolist()
    except Exception:
        return None


def fetch_market_volume(date_ymd: str) -> float:
    """沪深两市总成交额（亿）。AKShare 可取自 行情总貌 或 两市成交额。"""
    try:
        import akshare as ak
        for name in ("stock_zh_a_spot_em", "stock_szse_summary"):
            func = getattr(ak, name, None)
            if not func or not callable(func):
                continue
            try:
                df = func()
                if df is None or len(df) == 0:
                    continue
                # 常见列名：成交额、总成交额、金额
                for col in ("成交额", "总成交额", "金额"):
                    if col in df.columns:
                        total = pd_to_numeric_series(df[col])
                        if total:
                            return sum(total) / 1e8
            except Exception:
                continue
    except Exception:
        pass
    return 0.0


def calculate_emotion_score(data: Dict[str, Any]) -> float:
    """
    情绪评分模型（可执行）。
    emotion_score = limit_up_score + board_height_score + turnover_score + volume_score + break_fail_score
    """
    limit_up = int(data.get("limit_up_count") or 0)
    board_height = int(data.get("max_board_height") or 0)
    break_rate = float(data.get("break_rate") or 0)
    market_volume = float(data.get("total_volume") or 0)
    if not market_volume and "total_volume_billion" in data:
        market_volume = float(data["total_volume_billion"]) * 1e8

    score = 0.0
    # 涨停家数
    if limit_up > 80:
        score += 30
    elif limit_up > 40:
        score += 20
    else:
        score += 5
    # 连板高度
    if board_height >= 5:
        score += 25
    elif board_height >= 3:
        score += 15
    else:
        score += 5
    # 炸板率（低更好）
    if break_rate < 0.2:
        score += 20
    elif break_rate < 0.4:
        score += 10
    else:
        score -= 10
    # 成交额（万亿为 1e12）
    if market_volume > 1e12:
        score += 15
    elif market_volume > 5e11:
        score += 8
    return max(0, min(100, score))


def classify_emotion(score: float) -> str:
    """周期判断规则。"""
    if score < 30:
        return "冰点"
    if score < 50:
        return "启动"
    if score < 70:
        return "加速"
    if score < 85:
        return "高潮"
    return "极致高潮"


def compute_emotion_cycle(
    market_data: Optional[Dict[str, Any]] = None,
    date_ymd: Optional[str] = None,
    fallback: str = "启动",
) -> str:
    """
    根据市场数据或当日 AKShare 数据计算当前情绪周期。
    :return: 冰点 | 启动 | 加速 | 高潮 | 极致高潮 | 退潮
    """
    if date_ymd is None:
        date_ymd = datetime.now().strftime("%Y%m%d")
    data = dict(market_data or {})
    if not data.get("limit_up_count") and not data.get("emotion_score"):
        raw = fetch_zt_pool_data(date_ymd)
        data.update(raw)
        vol = fetch_market_volume(date_ymd)
        data["total_volume"] = vol * 1e8 if vol else 0
    score = data.get("emotion_score")
    if score is None:
        score = calculate_emotion_score(data)
    return classify_emotion(score)


def get_emotion_state(
    market_data: Optional[Dict[str, Any]] = None,
    date_ymd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    返回完整情绪状态，供前端仪表盘与仓位逻辑使用。
    :return: emotion_cycle, suggested_position_pct, description, emotion_score, limit_up_count, max_board_height, break_rate
    """
    if date_ymd is None:
        date_ymd = datetime.now().strftime("%Y%m%d")
    data = dict(market_data or {})
    raw = fetch_zt_pool_data(date_ymd)
    data.update(raw)
    if not data.get("total_volume"):
        data["total_volume"] = fetch_market_volume(date_ymd) * 1e8
    score = calculate_emotion_score(data)
    cycle = classify_emotion(score)
    suggested_pct = POSITION_BY_CYCLE.get(cycle, 0.4)
    desc_map = {
        "冰点": "情绪冰点，建议仓位 ≤20%，观望为主",
        "启动": "情绪启动，建议仓位 30–50%，可抓首板",
        "加速": "情绪加速，建议仓位约 60%，做龙头",
        "高潮": "情绪高潮，建议减仓、止盈",
        "极致高潮": "极致高潮，建议降至 30% 以下",
        "退潮": "退潮期，建议清仓或极轻仓",
    }
    return {
        "emotion_cycle": cycle,
        "suggested_position_pct": suggested_pct,
        "description": desc_map.get(cycle, "—"),
        "emotion_score": round(score, 1),
        "limit_up_count": data.get("limit_up_count", 0),
        "max_board_height": data.get("max_board_height", 0),
        "break_rate": round(float(data.get("break_rate") or 0), 4),
        "date": date_ymd[:4] + "-" + date_ymd[4:6] + "-" + date_ymd[6:8],
    }


def save_daily_emotion_json(state: Optional[Dict[str, Any]] = None, path: Optional[str] = None) -> str:
    """将当日情绪状态写入 daily_emotion.json，供 OpenClaw/调度 读取。"""
    if path is None:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_root, "data", "daily_emotion.json")
    state = state or get_emotion_state()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return path
