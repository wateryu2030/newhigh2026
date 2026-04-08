"""
A 股日 K 线数据源：支持按全局最新日期增量拉取多标的。
"""

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseDataSource, register_source


def _pop_proxy_env_vars() -> Dict[str, str]:
    """
    临时移除所有与代理相关的环境变量（含 ALL_PROXY / all_proxy 等）。
    env -u HTTPS_PROXY 往往不够；requests/urllib 仍会走坏掉的代理。
    """
    saved: Dict[str, str] = {}
    for k in list(os.environ.keys()):
        if "proxy" in k.lower():
            saved[k] = os.environ.pop(k)
    return saved


def _restore_env(saved: Dict[str, str]) -> None:
    if saved:
        os.environ.update(saved)


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

    @staticmethod
    def _hist_df_to_standard(df: Any, code: str) -> Any:
        """将 akshare 日 K DataFrame 规范为 code/date/open/high/low/close/volume/amount；无法识别列则返回 None。"""
        import pandas as pd

        if df is None or (hasattr(df, "empty") and df.empty):
            return None
        if not isinstance(df, pd.DataFrame):
            return None
        lower = {str(c).strip().lower(): c for c in df.columns}

        def _col(*cands: str) -> Optional[str]:
            for raw in cands:
                k = raw.strip().lower()
                if k in lower:
                    return lower[k]
                if raw in df.columns:
                    return raw
            return None

        c_date = _col("日期", "date", "trade_date")
        c_open = _col("开盘", "open")
        c_high = _col("最高", "high")
        c_low = _col("最低", "low")
        c_close = _col("收盘", "close", "latest")
        c_vol = _col("成交量", "volume", "vol")
        c_amt = _col("成交额", "amount", "turnover", "amt")
        if not c_date or not c_open or not c_high or not c_low or not c_close:
            return None
        out = df[[c_date, c_open, c_high, c_low, c_close]].copy()
        out.columns = ["_d", "open", "high", "low", "close"]
        if c_vol:
            out["volume"] = pd.to_numeric(df[c_vol], errors="coerce")
        else:
            out["volume"] = float("nan")
        if c_amt:
            out["amount"] = pd.to_numeric(df[c_amt], errors="coerce")
        else:
            out["amount"] = float("nan")
        for c in ("open", "high", "low", "close"):
            out[c] = pd.to_numeric(out[c], errors="coerce")
        out["date"] = pd.to_datetime(out["_d"], errors="coerce").dt.date
        out["code"] = code
        out = out.dropna(subset=["date"])
        out = out[["code", "date", "open", "high", "low", "close", "volume", "amount"]]
        if out.empty:
            return None
        return out

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
        strip_proxy_env = bool(kwargs.get("strip_proxy_env", False))
        saved_proxy = _pop_proxy_env_vars() if strip_proxy_env else {}
        try:
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
            # 勿用 pop：run_incremental 会对多批重复传入同一 kwargs
            request_sleep_sec = float(kwargs.get("request_sleep_sec") or 0)
            out = []
            for code in codes:
                code = str(code).strip().split(".", maxsplit=1)[0]
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
                std = self._hist_df_to_standard(df, code)
                if std is None:
                    continue
                out.append(std)
                if request_sleep_sec > 0:
                    time.sleep(request_sleep_sec)
            if not out:
                return pd.DataFrame()
            return pd.concat(out, ignore_index=True)
        finally:
            _restore_env(saved_proxy)

    def _diagnose_one_code(
        self,
        code: str,
        start_key: Optional[str],
        end_key: str,
        *,
        strip_proxy_env: bool = False,
    ) -> str:
        """抽样说明单标的拉取失败原因（网络/代理/空表/列名）。"""
        saved_proxy = _pop_proxy_env_vars() if strip_proxy_env else {}
        try:
            try:
                import akshare as ak
            except ImportError as e:
                return f"未安装 akshare: {e}"
            end = end_key or self.default_end_key()
            if not start_key:
                start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            else:
                try:
                    from_d = datetime.strptime(start_key[:8], "%Y%m%d") + timedelta(days=1)
                    start = from_d.strftime("%Y%m%d")
                except Exception:
                    start = end
            parts: List[str] = []
            df_em = None
            if getattr(ak, "stock_zh_a_hist_em", None):
                try:
                    df_em = ak.stock_zh_a_hist_em(
                        symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq"
                    )
                except Exception as e:
                    parts.append(f"东财 stock_zh_a_hist_em 异常: {e!r}")
            df_alt = None
            if df_em is None or df_em.empty:
                try:
                    df_alt = ak.stock_zh_a_hist(
                        symbol=code, start_date=start, end_date=end, period="daily", adjust="qfq"
                    )
                except Exception as e:
                    parts.append(f"备用 stock_zh_a_hist 异常: {e!r}")
            raw = df_em if df_em is not None and not df_em.empty else df_alt
            if raw is None or raw.empty:
                parts.append(f"接口返回空表（区间 {start}~{end}）")
            elif self._hist_df_to_standard(raw, code) is None:
                parts.append(f"列无法识别，实际列: {list(raw.columns)[:12]}…")
            return "；".join(parts) if parts else "未知"
        finally:
            _restore_env(saved_proxy)

    def write(self, conn: Any, data: Any) -> int:
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        import uuid

        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            return 0
        from ..storage.duckdb_manager import ensure_tables

        ensure_tables(conn)
        tmp = f"_tmp_adk_{uuid.uuid4().hex}"
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
        n = len(data)
        return int(n)

    def run_incremental(
        self,
        conn: Any,
        force_full: bool = False,
        codes: Optional[List[str]] = None,
        codes_limit: Optional[int] = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> int:
        """
        未传 codes 时从 **a_stock_basic** 取列表（全市场回填入口），不再优先用 a_stock_daily
        （否则只会反复更新已有 K 线的少数股票，无法扩量）。

        非 force_full 时：尚无日线的 code 约一年历史回填；已有数据者按**各 code 自身** MAX(date) 分组续拉
        （避免全局 MAX(date) 被少数「多一天」标的抬高导致 start>end、整批 0 行）。

        verbose=True 时每完成一批（默认 250 只）打印进度到 stderr。
        """
        from ..storage.duckdb_manager import ensure_tables

        def _log(msg: str) -> None:
            if verbose:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] [ashare_daily_kline] {msg}", file=sys.stderr, flush=True)

        ensure_tables(conn)
        if codes is None:
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
        if not codes:
            return 0

        end = kwargs.pop("end_key", self.default_end_key())
        chunk_size = 250
        total_written = 0
        strip_proxy_env = bool(kwargs.get("strip_proxy_env", False))

        def _write_chunk(start_key: Optional[str], chunk: List[str]) -> int:
            if not chunk:
                return 0
            data = self.fetch(start_key=start_key, end_key=end, codes=chunk, **kwargs)
            if data is None or (hasattr(data, "empty") and data.empty):
                return 0
            return self.write(conn, data)

        def _run_batches(
            label: str,
            start_key: Optional[str],
            code_list: List[str],
            batch_num_start: int,
            total_batches: int,
        ) -> None:
            nonlocal total_written
            b = batch_num_start
            empty_diag_left = 3
            for i in range(0, len(code_list), chunk_size):
                chunk = code_list[i : i + chunk_size]
                n = _write_chunk(start_key, chunk)
                total_written += n
                if verbose:
                    lo, hi = chunk[0], chunk[-1]
                    _log(
                        f"批次 {b}/{total_batches} [{label}] 标的×{len(chunk)} "
                        f"({lo}…{hi}) → +{n} 行，累计 {total_written} 行"
                    )
                    if n == 0 and chunk and empty_diag_left > 0:
                        _log(
                            f"  抽样诊断 {chunk[0]}: "
                            f"{self._diagnose_one_code(chunk[0], start_key, end, strip_proxy_env=strip_proxy_env)}"
                        )
                        empty_diag_left -= 1
                b += 1

        if force_full:
            nb = (len(codes) + chunk_size - 1) // chunk_size
            _log(f"开始 force_full：共 {len(codes)} 只，分 {nb} 批（每批最多 {chunk_size} 只）")
            _run_batches("全量重拉", None, codes, 1, nb)
            _log(f"完成，本 run 共写入 {total_written} 行")
            return total_written

        global_last = self.get_last_key(conn)
        if not global_last:
            nb = (len(codes) + chunk_size - 1) // chunk_size
            _log(f"开始（无全局最新日）：共 {len(codes)} 只，分 {nb} 批")
            _run_batches("历史回填", None, codes, 1, nb)
            _log(f"完成，本 run 共写入 {total_written} 行")
            return total_written

        def _date_to_yyyymmdd(d: Any) -> str:
            if d is None:
                return ""
            if hasattr(d, "strftime"):
                return d.strftime("%Y%m%d")
            s = str(d).replace("-", "")[:8]
            return s if len(s) >= 8 and s.isdigit() else ""

        need_full: List[str] = []
        incr_by_last: dict[str, List[str]] = defaultdict(list)
        for c in codes:
            try:
                row = conn.execute(
                    "SELECT MAX(date) AS d FROM a_stock_daily WHERE code = ?",
                    [c],
                ).fetchone()
                if not row or row[0] is None:
                    need_full.append(c)
                else:
                    lk = _date_to_yyyymmdd(row[0])
                    if lk:
                        incr_by_last[lk].append(c)
                    else:
                        need_full.append(c)
            except Exception:
                need_full.append(c)

        nf = (len(need_full) + chunk_size - 1) // chunk_size
        ni_total = sum(
            (len(lst) + chunk_size - 1) // chunk_size for lst in incr_by_last.values()
        )
        total_batches = max(1, nf + ni_total)
        n_incr_codes = sum(len(lst) for lst in incr_by_last.values())
        _log(
            f"开始增量：候选 {len(codes)} 只 → 需历史回填 {len(need_full)} 只（{nf} 批）"
            f"，需续拉 {n_incr_codes} 只（末日分 {len(incr_by_last)} 组，约 {ni_total} 批）；全局最新日 {global_last}"
        )
        _run_batches("历史回填", None, need_full, 1, total_batches)
        bnum = nf + 1
        for last_k in sorted(incr_by_last.keys()):
            lst = incr_by_last[last_k]
            _run_batches(f"增量(末{last_k})", last_k, lst, bnum, total_batches)
            bnum += (len(lst) + chunk_size - 1) // chunk_size
        _log(f"完成，本 run 共写入 {total_written} 行")
        return total_written


register_source("ashare_daily_kline", AShareDailyKlineSource())
