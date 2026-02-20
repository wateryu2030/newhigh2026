# -*- coding: utf-8 -*-
"""股票池：从数据库或配置获取待扫描标的列表。"""
import os
from typing import List, Tuple, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_stock_list(limit: Optional[int] = None) -> List[Tuple[str, str, str]]:
    """
    从数据库获取股票列表 (order_book_id, symbol, name)。
    limit: 最多返回数量，None 表示全部。
    """
    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        return []
    try:
        import sys
        sys.path.insert(0, _root)
        from database.db_schema import StockDatabase
        db = StockDatabase(db_path)
        rows = db.get_stocks()
        if limit is not None and limit > 0:
            rows = rows[:limit]
        return rows
    except Exception:
        return []


def get_stock_symbols(limit: Optional[int] = None) -> List[str]:
    """返回 order_book_id 列表。"""
    return [r[0] for r in get_stock_list(limit)]
