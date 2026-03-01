# -*- coding: utf-8 -*-
"""
股票显示名称解析：供 /api/stocks、多智能体扫描等统一使用。
从 CSV 与数据库解析 order_book_id/symbol -> 中文名称。
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional

# 常见标的显示名（列表/扫描常用，CSV 未覆盖时使用）
_SYMBOL_NAME_FALLBACK: Dict[str, str] = {
    "002230": "科大讯飞",
    "000938": "紫光股份",
    "000977": "浪潮信息",
    "600519": "贵州茅台",
    "000001": "平安银行",
    "002701": "奥瑞金",
    "600745": "闻泰科技",
    "000014": "沙河股份",
    "000016": "深康佳A",
    "000017": "深中华A",
    "000019": "深深宝A",
    "000020": "深华发A",
    "000021": "深科技",
    "000025": "特力A",
    "000026": "飞亚达",
    "000027": "深圳能源",
    "000028": "国药一致",
    "300212": "易华录",
}


def load_stock_name_overrides(root: Optional[str] = None) -> Dict[str, str]:
    """从 data/*.csv 加载 order_book_id -> 名称，与 web_platform 逻辑一致。"""
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    overrides: Dict[str, str] = {}
    for path in (
        os.path.join(root, "data", "tech_leader_stocks.csv"),
        os.path.join(root, "data", "consume_leader_stocks.csv"),
    ):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.readline()  # skip header
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        name = parts[1].strip()
                        if code and name and name != code:
                            overrides[code] = name
        except Exception:
            continue
    overrides["600745.XSHG"] = "闻泰科技"
    return overrides


def get_display_name(
    symbol: str,
    db: Any = None,
    root: Optional[str] = None,
) -> str:
    """
    根据 symbol（6 位代码）返回显示名称。
    查找顺序：CSV overrides( order_book_id ) -> DB (order_book_id, symbol, name) -> 6 位 fallback -> symbol。
    """
    symbol = (symbol or "").strip().split(".")[0]
    if len(symbol) < 5:
        return symbol
    symbol_6 = symbol.zfill(6)
    overrides = load_stock_name_overrides(root)

    # 1) CSV: order_book_id 形式
    for suffix in (".XSHE", ".XSHG"):
        key = symbol_6 + suffix
        if key in overrides:
            return overrides[key]
    if symbol_6 in overrides:
        return overrides[symbol_6]

    # 2) 内置常见标的
    if symbol_6 in _SYMBOL_NAME_FALLBACK:
        return _SYMBOL_NAME_FALLBACK[symbol_6]

    # 3) DB
    if db is not None and hasattr(db, "get_stocks"):
        try:
            for order_book_id, sym, name in db.get_stocks():
                if (sym or "").strip().zfill(6) == symbol_6:
                    return overrides.get(order_book_id, name or sym or symbol_6)
        except Exception:
            pass

    return symbol_6
