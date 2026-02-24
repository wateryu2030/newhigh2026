# -*- coding: utf-8 -*-
"""
A 股股票池数据接口。
支持从数据库、CSV 加载标的列表，统一为 (order_book_id, symbol, name) 结构，可扩展更多数据源。
"""
import os
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field

# 项目根目录（data 包所在目录的上级）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class StockUniverse:
    """
    股票池统一结构。
    items: [(order_book_id, symbol, name), ...]
    source: 数据来源标识，如 "database" / "csv"
    """

    items: List[Tuple[str, str, str]] = field(default_factory=list)
    source: str = ""

    def symbols(self, limit: Optional[int] = None) -> List[str]:
        """返回 order_book_id 列表。"""
        if limit is None or limit <= 0:
            return [x[0] for x in self.items]
        return [x[0] for x in self.items[:limit]]

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """转为 [{"order_book_id", "symbol", "name"}, ...]，便于 JSON 与前端。"""
        return [
            {"order_book_id": o, "symbol": s, "name": n}
            for o, s, n in self.items
        ]

    def __len__(self) -> int:
        return len(self.items)


def load_universe_from_database(
    db_path: Optional[str] = None,
    limit: Optional[int] = None,
) -> StockUniverse:
    """
    从 DuckDB 加载股票池（stocks 表）。
    :param db_path: 忽略，统一使用 data/quant.duckdb
    :param limit: 最多返回数量，None 表示全部
    """
    try:
        import sys
        sys.path.insert(0, _ROOT)
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        path = getattr(db, "db_path", os.path.join(_ROOT, "data", "quant.duckdb"))
        if not os.path.exists(path):
            return StockUniverse(source="database")
        rows = db.get_stocks() or []
        if limit is not None and limit > 0:
            rows = rows[:limit]
        return StockUniverse(items=rows, source="database")
    except Exception:
        return StockUniverse(source="database")


def load_universe_from_csv(
    csv_path: str,
    code_col: str = "代码",
    name_col: Optional[str] = "名称",
) -> StockUniverse:
    """
    从 CSV 加载股票池。要求至少一列为股票代码（如 000001 或 000001.XSHE）。
    :param csv_path: CSV 文件路径（可相对项目根）
    :param code_col: 代码列名
    :param name_col: 名称列名，可选
    """
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(_ROOT, csv_path)
    if not os.path.exists(csv_path):
        return StockUniverse(source="csv")
    try:
        import pandas as pd
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if code_col not in df.columns:
            return StockUniverse(source="csv")
        items = []
        for _, row in df.iterrows():
            code = str(row[code_col]).strip()
            if not code or code == "nan":
                continue
            if "." not in code:
                code_full = code + (".XSHG" if code.startswith("6") else ".XSHE")
            else:
                code_full = code
            name = str(row.get(name_col, "")).strip() if name_col and name_col in df.columns else ""
            items.append((code_full, code, name or code))
        return StockUniverse(items=items, source="csv")
    except Exception:
        return StockUniverse(source="csv")


def get_universe(
    source: str = "database",
    db_path: Optional[str] = None,
    csv_path: Optional[str] = None,
    limit: Optional[int] = None,
) -> StockUniverse:
    """
    统一入口：按来源获取股票池。
    :param source: "database" | "csv"
    :param db_path: 数据库路径（source=database 时有效）
    :param csv_path: CSV 路径（source=csv 时有效）
    :param limit: 数量上限
    """
    if source == "csv" and csv_path:
        return load_universe_from_csv(csv_path)
    return load_universe_from_database(db_path=db_path, limit=limit)
