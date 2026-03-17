"""题材爆发识别：当日涨停集中板块 → hot_themes。"""

from __future__ import annotations

import pandas as pd


class ThemeDetector:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        try:
            from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

            c = get_conn(read_only=False)
            ensure_tables(c)
            return c
        except Exception:
            import os
            import duckdb

            # Go up 5 levels: hotmoney_sniper → market_scanner → market-scanner → src → newhigh
            root = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))
                        )
                    )
                )
            )
            path = (
                os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "")
                or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "")
                or os.path.join(root, "data", "quant_system.duckdb")
            )
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            return duckdb.connect(path)

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
