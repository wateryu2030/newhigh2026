"""
A 股龙虎榜数据源：按 lhb_date 增量写入，避免全量重复。
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from .base import BaseDataSource, register_source


class AShareLonghubangSource(BaseDataSource):
    """龙虎榜明细，增量 key 为最新 lhb_date（YYYYMMDD）。"""

    @property
    def source_id(self) -> str:
        return "ashare_longhubang"

    def get_last_key(self, conn: Any) -> Optional[str]:
        try:
            row = conn.execute("SELECT max(lhb_date) AS d FROM a_stock_longhubang").fetchone()
            if row and row[0] is not None:
                d = row[0]
                if hasattr(d, "strftime"):
                    return d.strftime("%Y%m%d")
                return str(d).replace("-", "")[:8]
        except Exception:
            pass
        return None

    def fetch(
        self,
        start_key: Optional[str] = None,
        end_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        try:
            import akshare as ak
            import pandas as pd
        except ImportError:
            return None
        try:
            df = ak.stock_lhb_detail_em(symbol="近一月")
        except Exception:
            try:
                df = ak.stock_lhb_detail_em()
            except Exception:
                return None
        if df is None or df.empty:
            return None
        now = dt.datetime.now()
        df = df.copy()
        df["snapshot_time"] = now
        code_col = "代码" if "代码" in df.columns else "code"
        name_col = "名称" if "名称" in df.columns else "name"
        date_col = "成交日期" if "成交日期" in df.columns else "lhb_date"
        net_col = "净买入" if "净买入" in df.columns else "net_buy"
        df = df.rename(
            columns={code_col: "code", name_col: "name", date_col: "lhb_date", net_col: "net_buy"}
        )
        for c in ["code", "name", "lhb_date", "net_buy"]:
            if c not in df.columns:
                df[c] = "" if c in ("code", "name") else None
        df["lhb_date"] = pd.to_datetime(df["lhb_date"], errors="coerce").dt.date
        out = df[["code", "name", "lhb_date", "net_buy", "snapshot_time"]].dropna(subset=["code"])
        out = out.fillna(0)
        if start_key:
            try:
                from datetime import datetime as dt

                start_d = dt.strptime(start_key[:8], "%Y%m%d").date()
                out = out[out["lhb_date"] >= start_d]
            except Exception:
                pass
        if end_key:
            try:
                from datetime import datetime as dt

                end_d = dt.strptime(end_key[:8], "%Y%m%d").date()
                out = out[out["lhb_date"] <= end_d]
            except Exception:
                pass
        return out

    def write(self, conn: Any, data: Any) -> int:
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            return 0
        from ..storage.duckdb_manager import ensure_tables

        ensure_tables(conn)
        conn.register("tmp", data)
        conn.execute("""
            INSERT INTO a_stock_longhubang (code, name, lhb_date, net_buy, snapshot_time)
            SELECT code, name, lhb_date, net_buy, snapshot_time FROM tmp
        """)
        return int(len(data))


register_source("ashare_longhubang", AShareLonghubangSource())
