"""
Tushare A 股日 K 数据源：需 TUSHARE_TOKEN，拉取后写入 a_stock_daily。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, List, Optional

from .base import BaseDataSource, register_source


class TushareDailySource(BaseDataSource):
    """Tushare 日 K（需 tushare 包与 TUSHARE_TOKEN）。"""

    @property
    def source_id(self) -> str:
        return "tushare_daily"

    def get_last_key(self, conn: Any) -> Optional[str]:
        try:
            row = conn.execute("SELECT max(date) AS d FROM a_stock_daily").fetchone()
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
        ts_codes: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        token = os.environ.get("TUSHARE_TOKEN", "").strip()
        if not token:
            return None
        try:
            import pandas as pd
            import tushare as ts
        except ImportError:
            return None
        ts.set_token(token)
        pro = ts.pro_api()
        end = end_key or self.default_end_key()
        if not start_key:
            start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        else:
            try:
                from_d = datetime.strptime(start_key[:8], "%Y%m%d") + timedelta(days=1)
                start = from_d.strftime("%Y%m%d")
            except Exception:
                start = end
        if start > end:
            return __import__("pandas").DataFrame()
        codes = ts_codes or []
        if not codes:
            return __import__("pandas").DataFrame()
        out = []
        for tc in codes:
            tc = str(tc).strip()
            if not tc or len(tc) < 6:
                continue
            try:
                df = pro.daily(ts_code=tc, start_date=start, end_date=end)
            except Exception:
                continue
            if df is None or df.empty:
                continue
            df = df.copy()
            code = tc.split(".")[0] if "." in tc else tc
            df["code"] = code
            df = df.rename(columns={
                "trade_date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "vol": "volume",
                "amount": "amount",
            })
            if "date" not in df.columns and "trade_date" in df.columns:
                df["date"] = pd.to_datetime(df["trade_date"]).dt.date
            cols = ["code", "date", "open", "high", "low", "close", "volume", "amount"]
            for c in cols:
                if c not in df.columns:
                    df[c] = None
            df = df[cols]
            out.append(df)
        if not out:
            return __import__("pandas").DataFrame()
        return pd.concat(out, ignore_index=True)

    def write(self, conn: Any, data: Any) -> int:
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        import pandas as pd
        if not isinstance(data, pd.DataFrame):
            return 0
        from ..storage.duckdb_manager import ensure_tables
        ensure_tables(conn)
        conn.register("tmp_ts", data)
        conn.execute("""
            INSERT INTO a_stock_daily (code, date, open, high, low, close, volume, amount)
            SELECT code, date, open, high, low, close, volume, amount FROM tmp_ts
            ON CONFLICT (code, date) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
            volume=EXCLUDED.volume, amount=EXCLUDED.amount
        """)
        return int(len(data))

    def run_incremental(
        self, conn: Any, force_full: bool = False, ts_codes: Optional[List[str]] = None, **kwargs: Any
    ) -> int:
        from ..storage.duckdb_manager import ensure_tables
        ensure_tables(conn)
        if ts_codes is None:
            try:
                df = conn.execute("SELECT DISTINCT code FROM a_stock_daily LIMIT 3000").fetchdf()
                if df is not None and not df.empty:
                    ts_codes = [str(c) + ".SZ" if str(c).startswith(("0", "3")) else str(c) + ".SH" for c in df["code"]]
            except Exception:
                pass
        if not ts_codes:
            return 0
        last = None if force_full else self.get_last_key(conn)
        end = kwargs.pop("end_key", self.default_end_key())
        data = self.fetch(start_key=last, end_key=end, ts_codes=ts_codes, **kwargs)
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        return self.write(conn, data)


register_source("tushare_daily", TushareDailySource())
