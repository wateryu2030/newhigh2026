# -*- coding: utf-8 -*-
"""
历史情绪标签生成：利用 sentiment_engine 为过去 N 年每日生成 emotion_state，缓存到 emotion_history.csv。
"""
from __future__ import annotations
import csv
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE_PATH = os.path.join(_ROOT, "data", "emotion_history.csv")


def _trading_days(start: datetime, end: datetime) -> List[datetime]:
    """生成 [start, end] 内的交易日（简单排除周末）。"""
    out = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def load_cached_emotion(cache_path: str = DEFAULT_CACHE_PATH) -> Dict[str, str]:
    """加载已缓存日期 -> emotion_state。"""
    result = {}
    if not os.path.exists(cache_path):
        return result
    with open(cache_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            date_key = row.get("date", "").strip()
            state = row.get("emotion_state", "").strip()
            if date_key:
                result[date_key] = state
    return result


def save_emotion_cache(
    records: List[Dict[str, Any]],
    cache_path: str = DEFAULT_CACHE_PATH,
) -> None:
    """将 (date, emotion_state, ...) 写入 CSV。"""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if not records:
        return
    keys = list(records[0].keys())
    with open(cache_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(records)


def generate_emotion_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    years: int = 2,
    cache_path: str = DEFAULT_CACHE_PATH,
) -> str:
    """
    为 [start_date, end_date] 生成情绪标签并缓存；缺失日期用 sentiment_engine 计算。
    :param start_date: YYYY-MM-DD，缺省为 years 年前
    :param end_date: YYYY-MM-DD，缺省为昨日
    :param years: 当 start_date 未给时，从 end_date 往前推 years 年
    :return: cache_path
    """
    from core.sentiment_engine import get_emotion_state

    if end_date is None:
        end_d = datetime.now() - timedelta(days=1)
        end_date = end_d.strftime("%Y-%m-%d")
    if start_date is None:
        end_d = datetime.strptime(end_date[:10], "%Y-%m-%d")
        start_d = end_d - timedelta(days=years * 365)
        start_date = start_d.strftime("%Y-%m-%d")

    start_d = datetime.strptime(start_date[:10], "%Y-%m-%d")
    end_d = datetime.strptime(end_date[:10], "%Y-%m-%d")
    days = _trading_days(start_d, end_d)

    cached = load_cached_emotion(cache_path)
    for d in days:
        key = d.strftime("%Y-%m-%d")
        if key in cached:
            continue
        ymd = d.strftime("%Y%m%d")
        state = get_emotion_state(date_ymd=ymd)
        cycle = state.get("emotion_cycle", "启动")
        cached[key] = cycle
    records = [{"date": k, "emotion_state": cached[k]} for k in sorted(cached.keys())]
    save_emotion_cache(records, cache_path)
    return cache_path
