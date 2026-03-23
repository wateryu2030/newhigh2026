"""
Tushare A 股日 K 数据源：需 TUSHARE_TOKEN，拉取后写入 a_stock_daily。
走 api.tushare.pro，通常不受东财 push2his.eastmoney.com 的代理问题影响（可与 akshare 互为备份）。
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, List, Optional

from .ashare_daily_kline import _pop_proxy_env_vars, _restore_env
from .base import BaseDataSource, register_source


def _tushare_token_from_env() -> str:
    """读取 Tushare Token：主键 TUSHARE_TOKEN，兼容 .env 里常见别名。"""
    for key in ("TUSHARE_TOKEN", "TUSHARE_API_KEY", "TS_TOKEN"):
        v = os.environ.get(key, "").strip()
        if v:
            return v
    return ""


class TushareDailySource(BaseDataSource):
    """Tushare 日 K（需 tushare 包与 TUSHARE_TOKEN）。"""

    @property
    def source_id(self) -> str:
        return "tushare_daily"

    @staticmethod
    def code_to_ts_code(raw: str) -> Optional[str]:
        """6 位 A 股/北交所代码 → Tushare ts_code。"""
        c = str(raw).strip().split(".", maxsplit=1)[0]
        if not c:
            return None
        if c.startswith("6"):
            return f"{c}.SH"
        if c.startswith(("0", "3")):
            return f"{c}.SZ"
        # 北交所等（与 collectors/tushare_daily 规则一致）
        if c.startswith(("4", "8", "9")) or len(c) == 8:
            return f"{c}.BSE"
        return None

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

    @staticmethod
    def _normalize_pro_daily_df(df: Any, pd: Any) -> Any:
        if df is None or (hasattr(df, "empty") and df.empty):
            return None
        # Tushare 报错时可能只有 msg 等列
        if "ts_code" not in df.columns:
            if "msg" in df.columns:
                return None
            return None
        out = df.copy()
        out["code"] = out["ts_code"].astype(str).str.split(".").str[0]
        td = out["trade_date"]
        # float 会变成 "20250323.0"，format 解析失败 → 全被 dropna
        td_str = td.astype(str).str.replace(r"\.0$", "", regex=True).str.replace("-", "", regex=False)
        td_str = td_str.str.slice(0, 8)
        out["date"] = pd.to_datetime(td_str, format="%Y%m%d", errors="coerce").dt.date
        mask_bad = out["date"].isna()
        if mask_bad.any():
            alt = pd.to_datetime(td, errors="coerce").dt.date
            out.loc[mask_bad, "date"] = alt[mask_bad]
        if "vol" in out.columns:
            out = out.rename(columns={"vol": "volume"})
        cols = ["code", "date", "open", "high", "low", "close", "volume", "amount"]
        for c in cols:
            if c not in out.columns:
                out[c] = None
        out = out[cols].dropna(subset=["date"])
        if out.empty:
            return None
        return out

    def _diagnose_tushare(self, end_key: str, strip_proxy: bool) -> str:
        """抽样 000001.SZ，说明 token/积分/解析 问题。"""
        import pandas as pd

        token = _tushare_token_from_env()
        if len(token) < 32:
            return (
                f"TUSHARE_TOKEN 长度过短({len(token)})，疑似占位符或未粘贴完整；"
                "文档里的「你的token」需换成 tushare.pro 个人中心的真实 token"
            )
        saved = _pop_proxy_env_vars() if strip_proxy else {}
        try:
            try:
                import tushare as ts
            except ImportError:
                return "未安装 Python 包 tushare，请执行: pip install tushare（仓库 requirements.txt 已列出）"

            ts.set_token(token)
            pro = ts.pro_api()
            start_probe = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            end = end_key or self.default_end_key()
            try:
                df = pro.daily(ts_code="000001.SZ", start_date=start_probe, end_date=end)
            except Exception as e:
                return f"pro.daily 调用异常: {e!r}"
            if df is None or df.empty:
                return (
                    "pro.daily(000001.SZ) 空返回：请检查 token 是否正确、"
                    "账号积分是否足够调用 daily；或该区间无交易日"
                )
            if "msg" in df.columns and "ts_code" not in df.columns:
                return f"Tushare 业务错误: {df.to_dict()}"
            norm = self._normalize_pro_daily_df(df, pd)
            if norm is None or norm.empty:
                return (
                    f"有返回但规范化后为空；trade_date 样例 {df['trade_date'].head(3).tolist()}，列={list(df.columns)}"
                )
            return f"单只探测成功（{len(norm)} 行），若批量仍 0 行可尝试减小批量或看接口限流"
        finally:
            _restore_env(saved)

    def fetch(
        self,
        start_key: Optional[str] = None,
        end_key: Optional[str] = None,
        ts_codes: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        import pandas as pd

        token = _tushare_token_from_env()
        if not token:
            return None
        strip_proxy = bool(kwargs.get("strip_proxy_env", False))
        saved_proxy = _pop_proxy_env_vars() if strip_proxy else {}
        try:
            try:
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
                return pd.DataFrame()
            codes = [str(x).strip() for x in (ts_codes or []) if str(x).strip()]
            if not codes:
                return pd.DataFrame()
            sleep_sec = float(kwargs.get("request_sleep_sec") or 0)

            def _pull_batch(ts_list: List[str]) -> Any:
                try:
                    big = pro.daily(ts_code=",".join(ts_list), start_date=start, end_date=end)
                    norm = self._normalize_pro_daily_df(big, pd)
                    if norm is not None and not norm.empty:
                        return norm
                except Exception:
                    pass
                parts = []
                for tc in ts_list:
                    try:
                        one = pro.daily(ts_code=tc, start_date=start, end_date=end)
                        norm = self._normalize_pro_daily_df(one, pd)
                        if norm is not None and not norm.empty:
                            parts.append(norm)
                    except Exception:
                        continue
                    if sleep_sec > 0:
                        time.sleep(sleep_sec)
                if not parts:
                    return pd.DataFrame()
                return pd.concat(parts, ignore_index=True)

            return _pull_batch(codes)
        finally:
            _restore_env(saved_proxy)

    def write(self, conn: Any, data: Any) -> int:
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            return 0
        from ..storage.duckdb_manager import ensure_tables

        ensure_tables(conn)
        tmp = f"_tmp_ts_{uuid.uuid4().hex}"
        conn.register(tmp, data)
        try:
            conn.execute(
                f"""
                INSERT INTO a_stock_daily (code, date, open, high, low, close, volume, amount)
                SELECT code, date, open, high, low, close, volume, amount FROM {tmp}
                ON CONFLICT (code, date) DO UPDATE SET
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
                volume=EXCLUDED.volume, amount=EXCLUDED.amount
            """
            )
        finally:
            try:
                conn.unregister(tmp)
            except Exception:
                pass
        return int(len(data))

    def run_incremental(
        self,
        conn: Any,
        force_full: bool = False,
        ts_codes: Optional[List[str]] = None,
        codes: Optional[List[str]] = None,
        codes_limit: Optional[int] = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> int:
        """
        未传 ts_codes / codes 时从 a_stock_basic 取全市场（与 ashare_daily_kline 一致），
        按批调用 pro.daily（批量逗号拼接，失败则逐只）。

        支持：codes_limit、verbose、strip_proxy_env（kwargs）、request_sleep_sec（kwargs）。
        """
        from ..storage.duckdb_manager import ensure_tables

        def _log(msg: str) -> None:
            if verbose:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] [tushare_daily] {msg}", file=sys.stderr, flush=True)

        if not _tushare_token_from_env():
            _log("未设置 TUSHARE_TOKEN（或别名 TUSHARE_API_KEY / TS_TOKEN），跳过")
            return 0

        try:
            import tushare  # noqa: F401
        except ImportError:
            _log("未安装 tushare，请运行: pip install tushare")
            return 0

        ensure_tables(conn)
        if ts_codes is None and codes is None:
            lim = 8000
            if codes_limit is not None:
                try:
                    lim = max(1, min(int(codes_limit), 8000))
                except (TypeError, ValueError):
                    pass
            try:
                df = conn.execute(
                    """
                    SELECT code FROM a_stock_basic
                    WHERE code IS NOT NULL AND LENGTH(TRIM(CAST(code AS VARCHAR))) >= 4
                    ORDER BY code
                    LIMIT ?
                    """,
                    [lim],
                ).fetchdf()
                if df is not None and not df.empty:
                    codes = df["code"].astype(str).str.strip().tolist()
            except Exception:
                codes = []
        if ts_codes is None and codes is not None:
            ts_codes = []
            for c in codes:
                tc = self.code_to_ts_code(c)
                if tc:
                    ts_codes.append(tc)
        if not ts_codes:
            return 0

        end = kwargs.pop("end_key", self.default_end_key())
        # Tushare pro.daily 单次返回约最多 6000 行；一年≈244 交易日 → 每批股票数不宜超过 ~24，否则历史被截断
        try:
            chunk_size = int(kwargs.get("tushare_chunk_size") or 22)
        except (TypeError, ValueError):
            chunk_size = 22
        chunk_size = max(1, min(chunk_size, 40))
        total_written = 0
        strip_proxy_env = bool(kwargs.get("strip_proxy_env", False))
        sleep_between_batch = float(
            kwargs.get("tushare_batch_sleep_sec") or kwargs.get("request_sleep_sec") or 0.25
        )

        if verbose:
            _log(f"每批最多 {chunk_size} 只 ts_code（Tushare 单次约 6000 行，过大易截断历史）")

        def _write_chunk(start_key: Optional[str], chunk: List[str]) -> int:
            if not chunk:
                return 0
            data = self.fetch(start_key=start_key, end_key=end, ts_codes=chunk, **kwargs)
            if data is None or (hasattr(data, "empty") and data.empty):
                return 0
            return self.write(conn, data)

        def _run_batches(
            label: str,
            start_key: Optional[str],
            tlist: List[str],
            batch_num_start: int,
            total_batches: int,
        ) -> None:
            nonlocal total_written
            b = batch_num_start
            empty_diag_left = 3
            for i in range(0, len(tlist), chunk_size):
                chunk = tlist[i : i + chunk_size]
                n = _write_chunk(start_key, chunk)
                total_written += n
                if verbose:
                    c0 = chunk[0].split(".")[0]
                    c1 = chunk[-1].split(".")[0]
                    _log(
                        f"批次 {b}/{total_batches} [{label}] ts×{len(chunk)} "
                        f"({c0}…{c1}) → +{n} 行，累计 {total_written} 行"
                    )
                    if n == 0 and chunk and empty_diag_left > 0:
                        if "增量" in label:
                            _log("  本批增量 0 行：多为全局最新日后尚无新交易日，一般属正常")
                        else:
                            _log(f"  抽样诊断: {self._diagnose_tushare(end, strip_proxy_env)}")
                        empty_diag_left -= 1
                b += 1
                if sleep_between_batch > 0:
                    time.sleep(sleep_between_batch)

        if force_full:
            nb = (len(ts_codes) + chunk_size - 1) // chunk_size
            _log(f"开始 force_full：共 {len(ts_codes)} 个 ts_code，{nb} 批")
            _run_batches("全量", None, ts_codes, 1, nb)
            _log(f"完成，共写入 {total_written} 行")
            return total_written

        global_last = self.get_last_key(conn)
        if not global_last:
            nb = (len(ts_codes) + chunk_size - 1) // chunk_size
            _log(f"开始（库内无日线最新日）：共 {len(ts_codes)} 个 ts_code，{nb} 批")
            _run_batches("历史", None, ts_codes, 1, nb)
            _log(f"完成，共写入 {total_written} 行")
            return total_written

        need_full_ts: List[str] = []
        need_incr_ts: List[str] = []
        for tc in ts_codes:
            pure = tc.split(".")[0]
            try:
                row = conn.execute(
                    "SELECT MAX(date) AS d FROM a_stock_daily WHERE code = ?",
                    [pure],
                ).fetchone()
                if not row or row[0] is None:
                    need_full_ts.append(tc)
                else:
                    need_incr_ts.append(tc)
            except Exception:
                need_full_ts.append(tc)

        nf = (len(need_full_ts) + chunk_size - 1) // chunk_size
        ni = (len(need_incr_ts) + chunk_size - 1) // chunk_size
        total_batches = max(1, nf + ni)
        _log(
            f"开始增量：ts {len(ts_codes)} → 历史 {len(need_full_ts)}（{nf} 批）"
            f"，续拉 {len(need_incr_ts)}（{ni} 批）；全局最新日 {global_last}"
        )
        _run_batches("历史回填", None, need_full_ts, 1, total_batches)
        _run_batches("增量续拉", global_last, need_incr_ts, nf + 1, total_batches)
        _log(f"完成，共写入 {total_written} 行")
        return total_written


register_source("tushare_daily", TushareDailySource())
