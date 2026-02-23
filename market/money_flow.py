# -*- coding: utf-8 -*-
"""
资金流向：个股/板块主力净流入、大单等。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd


def get_stock_money_flow(
    symbol: str,
    days: int = 5,
) -> Dict[str, Any]:
    """
    个股资金流向（近期主力净流入等）。
    :param symbol: 6 位代码，如 600519
    :return: {"net_main", "net_super", "net_big", "net_medium", "net_small", "score"}
    """
    try:
        import akshare as ak
        code = symbol.split(".")[0] if "." in symbol else symbol
        try:
            df = ak.stock_individual_fund_flow(stock=code, market="000")
        except Exception:
            try:
                df = ak.stock_fund_flow_individual(symbol=code)
            except Exception:
                df = None
        if df is None or len(df) < 1:
            try:
                df = ak.stock_individual_fund_flow(stock=code, market="001")
            except Exception:
                df = None
        if df is None or len(df) == 0:
            return {"net_main": 0, "score": 0}
        df = df.head(days)
        # 列名可能：主力净流入、主力净流入-净额 等
        main_col = None
        for c in df.columns:
            if "主力" in str(c) and "净" in str(c):
                main_col = c
                break
        if main_col is None:
            main_col = df.columns[2] if len(df.columns) > 2 else df.columns[0]
        net_main = pd.to_numeric(df[main_col], errors="coerce").sum()
        if pd.isna(net_main):
            net_main = 0
        # 简单评分：净流入正为加分
        score = min(100, max(0, 50 + (net_main / 1e7)))  # 每千万约 1 分
        return {"net_main": float(net_main), "score": round(score, 2)}
    except Exception:
        return {"net_main": 0, "score": 0}


def get_sector_fund_flow_rank(
    indicator: str = "今日",
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    板块资金流向排名。
    :param indicator: 今日 / 3日 / 5日 等
    :return: [{"sector", "net_inflow", "rank"}, ...]
    """
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator=indicator)
        if df is None or len(df) == 0:
            return []
        name_col = "名称" if "名称" in df.columns else df.columns[0]
        flow_col = None
        for c in df.columns:
            if "主力" in str(c) or "净流入" in str(c) or "流入" in str(c):
                flow_col = c
                break
        if flow_col is None:
            flow_col = df.columns[1] if len(df.columns) > 1 else None
        out = []
        for i, row in df.head(top_n).iterrows():
            name = row.get(name_col, "")
            flow = row.get(flow_col, 0)
            try:
                flow = float(flow)
            except (TypeError, ValueError):
                flow = 0
            out.append({"sector": str(name), "net_inflow": flow, "rank": i + 1})
        return out
    except Exception:
        return []
