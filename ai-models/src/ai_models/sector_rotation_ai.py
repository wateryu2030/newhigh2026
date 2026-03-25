"""
主线题材识别AI系统：板块资金/成交额排名 → 主线题材。
决定买什么。
"""

from __future__ import annotations

import pandas as pd


class SectorRotationAI:
    def __init__(self, conn=None):
        self._connection = conn

    def _get_connection(self):
        if self._connection is not None:
            return self._connection
        from lib.database import get_connection, ensure_core_tables  # pylint: disable=import-error
        conn = get_connection(read_only=False)
        if conn:
            ensure_core_tables(conn)
        return conn

    def sector_strength(self) -> pd.DataFrame:
        """按板块（sector）汇总成交额并排名。sector 来自 a_stock_basic.sector。"""
        conn = self._get_connection()
        if not conn:
            return pd.DataFrame(columns=["sector", "total_volume", "rank"])
        try:
            df = conn.execute("""
                SELECT
                    COALESCE(b.sector, '未分类') AS sector,
                    SUM(COALESCE(d.amount, 0)) AS total_volume
                FROM a_stock_daily d
                LEFT JOIN a_stock_basic b ON d.code = b.code
                GROUP BY COALESCE(b.sector, '未分类')
            """).fetchdf()
        except Exception:
            df = conn.execute("""
                SELECT '全市场' AS sector, SUM(COALESCE(amount, 0)) AS total_volume
                FROM a_stock_daily
            """).fetchdf()
        if df is None or df.empty:
            df = pd.DataFrame(columns=["sector", "total_volume", "rank"])
            return df
        df["rank"] = df["total_volume"].rank(ascending=False).astype(int)
        return df

    def detect_main_theme(self, top_n: int = 5) -> pd.DataFrame:
        """取成交额排名前 top_n 的板块作为主线题材。"""
        df = self.sector_strength()
        if df is None or df.empty:
            return pd.DataFrame(columns=["sector", "total_volume", "rank"])
        main = df[df["rank"] <= top_n].copy()
        return main.sort_values("rank")

    def save_sector_strength(self, df: pd.DataFrame = None) -> int:
        """写入 sector_strength 表（兼容旧表）。"""
        if df is None:
            df = self.sector_strength()
        if df is None or df.empty:
            return 0
        from ._storage import write_sector_strength

        rows = [
            (r["sector"], float(r.get("total_volume", 0)), int(r.get("rank", 0)))
            for _, r in df.iterrows()
        ]
        write_sector_strength(rows)
        return len(rows)

    def save_main_themes(self, df: pd.DataFrame = None) -> int:
        """写入 main_themes 表。"""
        if df is None:
            df = self.detect_main_theme()
        if df is None or df.empty:
            return 0
        conn = self._get_connection()
        try:
            from data_pipeline.storage.duckdb_manager import ensure_tables  # pylint: disable=import-error
            ensure_tables(conn)
        except Exception:
            pass
        conn.execute("DELETE FROM main_themes")
        conn.register("tmp", df[["sector", "total_volume", "rank"]])
        conn.execute("""
            INSERT INTO main_themes (sector, total_volume, rank)
            SELECT sector, total_volume, rank FROM tmp
        """)
        return len(df)


def run_sector_rotation_ai() -> int:
    """兼容入口：计算板块强度与主线题材并写入表。"""
    ai = SectorRotationAI()
    strength = ai.sector_strength()
    if strength is not None and not strength.empty:
        ai.save_sector_strength(strength)
    main = ai.detect_main_theme()
    if main is not None and not main.empty:
        ai.save_main_themes(main)
        return len(main)
    from ._storage import write_sector_strength

    write_sector_strength([("全市场", 50.0, 1)])
    return 1
