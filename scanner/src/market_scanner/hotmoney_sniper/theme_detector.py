"""题材爆发识别：当日涨停集中板块 → hot_themes。"""

from __future__ import annotations

import pandas as pd


class ThemeDetector:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        from lib.database import get_connection, ensure_core_tables

        c = get_connection(read_only=False)
        if c:
            ensure_core_tables(c)
        return c

    def detect_hot_themes(self) -> pd.DataFrame:
        """识别涨停集中板块：按 sector 汇总涨停数并排序。sector 来自 a_stock_basic。"""
        conn = self._get_conn()
        try:
            df = conn.execute("""
                SELECT
                    COALESCE(b.sector, '未分类') AS sector,
                    COUNT(*) AS limitups
                FROM a_stock_limitup l
                LEFT JOIN a_stock_basic b ON l.code = b.code
                GROUP BY COALESCE(b.sector, '未分类')
                ORDER BY limitups DESC
            """).fetchdf()
        except Exception:
            df = conn.execute("""
                SELECT '全市场' AS sector, COUNT(*) AS limitups FROM a_stock_limitup
            """).fetchdf()
        if df is None or df.empty:
            return pd.DataFrame(columns=["sector", "limitups", "rank"])
        df["rank"] = df["limitups"].rank(ascending=False).astype(int)
        return df
