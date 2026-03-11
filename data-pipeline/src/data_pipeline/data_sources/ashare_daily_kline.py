"""
A 股日 K 线数据源：支持按全局最新日期增量拉取多标的。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List, Optional

from .base import BaseDataSource, register_source


class AShareDailyKlineSource(BaseDataSource):
    """A 股日 K（前复权），增量 key 为日期 YYYYMMDD。"""

    @property
    def source_id(self) -> str:
        return "ashare_daily_kline"

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
        codes: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        if not codes:
            return None
        try:
            import pandas as pd
        except ImportError:
            return None
        try:
            import akshare as ak
        except ImportError:
            return None
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
            return pd.DataFrame()
        out = []
        for code in codes:
            code = str(code).strip().split(".")[0]
            if not code or len(code) < 5:
                continue
            df = None
            if getattr(ak, "stock_zh_a_hist_em", None):
                try:
                    df = ak.stock_zh_a_hist_em(
                        symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq"
                    )
                except Exception:
                    pass
            if df is None or df.empty:
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=code, start_date=start, end_date=end, period="daily", adjust="qfq"
                    )
                except Exception:
                    continue
            if df is None or df.empty:
                continue
            col_date = "日期"
            if col_date not in df.columns:
                continue
            df = df.copy()
            df["code"] = code
            df = df.rename(columns={
                "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
                "成交量": "volume", "成交额": "amount",
            })
            df["date"] = pd.to_datetime(df[col_date]).dt.date
            df = df[["code", "date", "open", "high", "low", "close", "volume", "amount"]]
            out.append(df)
        if not out:
            return pd.DataFrame()
        return pd.concat(out, ignore_index=True)

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
            INSERT INTO a_stock_daily (code, date, open, high, low, close, volume, amount)
            SELECT code, date, open, high, low, close, volume, amount FROM tmp
            ON CONFLICT (code, date) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
            volume=EXCLUDED.volume, amount=EXCLUDED.amount
        """)
        n = len(data)
        return int(n)

    def run_incremental(
        self, conn: Any, force_full: bool = False, codes: Optional[List[str]] = None, **kwargs: Any
    ) -> int:
        """若未传 codes 则从 a_stock_daily / a_stock_basic 取。"""
        from ..storage.duckdb_manager import ensure_tables
        ensure_tables(conn)
        if codes is None:
            try:
                df = conn.execute("SELECT DISTINCT code FROM a_stock_daily LIMIT 5000").fetchdf()
                if df is not None and not df.empty:
                    codes = df["code"].astype(str).tolist()
            except Exception:
                pass
            if not codes:
                try:
                    df = conn.execute("SELECT code FROM a_stock_basic LIMIT 5000").fetchdf()
                    if df is not None and not df.empty:
                        codes = df["code"].astype(str).tolist()
                except Exception:
                    pass
        if not codes:
            return 0
        last = None if force_full else self.get_last_key(conn)
        end = kwargs.pop("end_key", self.default_end_key())
        data = self.fetch(start_key=last, end_key=end, codes=codes, **kwargs)
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        return self.write(conn, data)


register_source("ashare_daily_kline", AShareDailyKlineSource())
