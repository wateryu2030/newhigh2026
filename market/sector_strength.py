# -*- coding: utf-8 -*-
"""
板块强度：板块涨幅、涨停数量等，用于热点过滤。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd


def get_sector_strength(
    top_n: int = 30,
) -> List[Dict[str, Any]]:
    """
    获取板块强度排名（涨幅、涨跌家数等）。
    数据来源：akshare 东方财富板块。
    :return: [{"name", "change_pct", "up_count", "down_count", "strength"}, ...]
    """
    try:
        import akshare as ak
        # 行业板块
        df = ak.stock_board_industry_name_em()
        if df is None or len(df) == 0:
            return []
        # 列名可能：板块名称、涨跌幅、上涨家数、下跌家数 等
        name_col = "板块名称" if "板块名称" in df.columns else df.columns[0]
        change_col = None
        for c in ("涨跌幅", "涨幅", "change_pct", "涨跌"):
            if c in df.columns:
                change_col = c
                break
        if change_col is None:
            change_col = df.columns[1] if len(df.columns) > 1 else None
        out = []
        for _, row in df.head(top_n).iterrows():
            name = row.get(name_col, "")
            ch = row.get(change_col, 0)
            try:
                ch = float(ch)
            except (TypeError, ValueError):
                ch = 0
            out.append({
                "name": str(name),
                "change_pct": round(ch, 2),
                "strength": min(100, max(0, 50 + ch)),  # 简单强度 0~100
            })
        return out
    except Exception:
        return []


def get_sector_list() -> List[str]:
    """获取板块名称列表，供资金流等接口使用。"""
    rows = get_sector_strength(top_n=50)
    return [r["name"] for r in rows if r.get("name")]
