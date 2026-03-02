# -*- coding: utf-8 -*-
"""
龙虎榜游资席位识别引擎（机构级）。
数据来源：AKShare stock_lhb_detail_em；席位库 + 净买入 + 多席位共振判断。
仅在情绪为 启动 或 加速 时允许交易龙虎榜共振股。
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 知名游资席位库（可扩展）
YZZ_SEATS = [
    "章盟主",
    "赵老哥",
    "方新侠",
    "溧阳路",
    "小鳄鱼",
    "炒股养家",
    "作手新一",
    "宁波解放南",
    "上海溧阳路",
    "深圳益田路",
    "国泰君安南京太平南",
    "华泰证券深圳益田路",
    "中信证券杭州延安路",
]

# 共振净买阈值（万）
RESONANCE_NET_BUY_MIN_WAN = 5000


def fetch_lhb_detail(date_ymd: str) -> Optional[Any]:
    """
    龙虎榜明细。AKShare: stock_lhb_detail_em(date="YYYYMMDD")。
    """
    try:
        import akshare as ak
        func = getattr(ak, "stock_lhb_detail_em", None)
        if not func:
            return None
        try:
            df = func(date=date_ymd)
        except TypeError:
            df = func()
        return df
    except Exception as e:
        logger.debug("fetch_lhb_detail %s: %s", date_ymd, e)
        return None


def _net_buy_value(row: Any, df_columns: List[str]) -> float:
    """从一行中解析净买额（万或元）。"""
    for col in ("净买额", "净买入", "净买", "买入", "成交额"):
        if col in df_columns:
            try:
                v = row[col] if col in getattr(row, "index", []) else row.get(col, 0)
                if v is None:
                    continue
                v = float(v)
                if v > 1e6:
                    return v / 1e4
                return v
            except (TypeError, ValueError, KeyError):
                continue
    return 0.0


def _seat_name(row: Any, df_columns: List[str]) -> str:
    """营业部名称列。"""
    for col in ("营业部名称", "席位名称", "机构名称", "名称"):
        if col in df_columns:
            try:
                v = row[col] if col in getattr(row, "index", []) else row.get(col, "")
                return str(v).strip() if v is not None else ""
            except (KeyError, TypeError):
                continue
    return ""


def _row_val(row: Any, df_columns: List[str], *keys: str) -> Any:
    """从行中取第一个存在的列的值。"""
    for k in keys:
        if k in df_columns:
            try:
                return row[k] if k in getattr(row, "index", []) else row.get(k)
            except (KeyError, TypeError):
                continue
    return None


def lhb_yz_score(lhb_df: Any, seat_list: Optional[List[str]] = None) -> Tuple[float, List[Dict[str, Any]]]:
    """
    龙虎榜游资打分：知名席位净买加分、净卖减分。
    :return: (score, list of {"seat", "net_buy_wan", "symbol", "side"})
    """
    seats = seat_list or YZZ_SEATS
    score = 0.0
    details: List[Dict[str, Any]] = []
    if lhb_df is None or (hasattr(lhb_df, "__len__") and len(lhb_df) == 0):
        return score, details
    try:
        import pandas as pd
        df = lhb_df if isinstance(lhb_df, pd.DataFrame) else pd.DataFrame(lhb_df)
        cols = list(df.columns)
        for _, row in df.iterrows():
            seat = _seat_name(row, cols)
            net_buy_wan = _net_buy_value(row, cols)
            symbol = str(_row_val(row, cols, "代码", "symbol") or "").strip()
            for yz in seats:
                if yz in seat:
                    side = "buy" if net_buy_wan > 0 else "sell"
                    details.append({"seat": yz, "net_buy_wan": net_buy_wan, "symbol": symbol, "side": side})
                    if net_buy_wan > 0:
                        score += 20
                    else:
                        score -= 10
                    break
    except Exception as e:
        logger.debug("lhb_yz_score: %s", e)
    return score, details


def lhb_resonance(
    lhb_df: Any,
    seat_list: Optional[List[str]] = None,
    net_buy_min_wan: float = RESONANCE_NET_BUY_MIN_WAN,
) -> List[Dict[str, Any]]:
    """
    多席位共振识别：同一只股票 2 个以上知名席位同时净买入且金额 > net_buy_min_wan 万，
    标记为「游资共振龙头」。
    """
    seats = seat_list or YZZ_SEATS
    if lhb_df is None or (hasattr(lhb_df, "__len__") and len(lhb_df) == 0):
        return []
    try:
        import pandas as pd
        df = lhb_df if isinstance(lhb_df, pd.DataFrame) else pd.DataFrame(lhb_df)
        cols = list(df.columns)
        # symbol -> [(seat, net_buy_wan), ...]
        by_symbol: Dict[str, List[Tuple[str, float]]] = {}
        for _, row in df.iterrows():
            seat = _seat_name(row, cols)
            net_buy_wan = _net_buy_value(row, cols)
            if net_buy_wan <= 0:
                continue
            symbol = str(_row_val(row, cols, "代码", "symbol") or "").strip()
            if not symbol:
                continue
            for yz in seats:
                if yz in seat:
                    by_symbol.setdefault(symbol, []).append((yz, net_buy_wan))
                    break
        out = []
        for symbol, seat_nets in by_symbol.items():
            if len(seat_nets) < 2:
                continue
            total_wan = sum(n for _, n in seat_nets)
            if total_wan < net_buy_min_wan:
                continue
            out.append({
                "symbol": symbol,
                "seat_count": len(seat_nets),
                "seats": [s for s, _ in seat_nets],
                "total_net_buy_wan": round(total_wan, 2),
                "label": "游资共振龙头",
            })
        return out
    except Exception as e:
        logger.debug("lhb_resonance: %s", e)
        return []


def get_dragon_lhb_pool(
    date_ymd: Optional[str] = None,
    emotion_cycle: Optional[str] = None,
    only_when_emotion_ok: bool = True,
) -> Dict[str, Any]:
    """
    龙虎榜龙头池：游资打分 + 共振列表。
    若 only_when_emotion_ok=True 且 emotion_cycle 不在 (启动, 加速)，则 resonance 为空并标注原因。
    """
    if date_ymd is None:
        date_ymd = datetime.now().strftime("%Y%m%d")
    lhb_df = fetch_lhb_detail(date_ymd)
    score, details = lhb_yz_score(lhb_df)
    resonance = lhb_resonance(lhb_df)
    emotion_ok = emotion_cycle in ("启动", "加速")
    if only_when_emotion_ok and not emotion_ok:
        resonance = []
        reason = "当前情绪阶段为「{}」，仅启动/加速期允许交易龙虎榜共振股。".format(emotion_cycle or "—")
    else:
        reason = ""
    return {
        "date": date_ymd[:4] + "-" + date_ymd[4:6] + "-" + date_ymd[6:8],
        "lhb_score": round(score, 1),
        "resonance_list": resonance,
        "resonance_count": len(resonance),
        "seat_details_count": len(details),
        "emotion_ok": emotion_ok,
        "reason": reason,
    }


def save_dragon_lhb_pool_json(pool: Optional[Dict[str, Any]] = None, path: Optional[str] = None) -> str:
    """将龙虎榜龙头池写入 dragon_lhb_pool.json。"""
    if path is None:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_root, "data", "dragon_lhb_pool.json")
    if pool is None:
        from core.sentiment_engine import get_emotion_state
        state = get_emotion_state()
        pool = get_dragon_lhb_pool(emotion_cycle=state.get("emotion_cycle"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    return path
