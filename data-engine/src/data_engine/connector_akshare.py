"""A 股数据连接器：通过 akshare 拉取 A 股/北交所日线/分钟线，归一化为 core.OHLCV。"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from core import OHLCV

try:
    import akshare as ak
except ImportError:
    ak = None


def _normalize_symbol(code: str) -> str:
    """A 股/北交所代码转为带交易所后缀：600519->600519.SH, 000001->000001.SZ, 830799->830799.BSE。"""
    code = str(code).strip().split(".", maxsplit=1)[0]
    if not code:
        return code
    # 北交所：4/8/9 开头或 8 位
    if code.startswith(("4", "8", "9")) or len(code) == 8:
        return f"{code}.BSE"
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def _to_utc(dt_obj: dt.datetime) -> dt.datetime:
    """若为 naive 则视为本地时间并转为 UTC（A 股 15:00 收盘）。"""
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
    return dt_obj


def _fetch_hist_df(code: str, start_date: str, end_date: str, period: str, adjust: str):
    """拉取日/周/月 K 线 DataFrame，优先东方财富接口（支持沪深京/北交所）。"""
    # 优先东方财富（沪深京含北交所）
    # pylint: disable=no-member
    if getattr(ak, "stock_zh_a_hist_em", None) is not None:
        try:
            return ak.stock_zh_a_hist_em(
                symbol=code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except Exception:
            pass
    try:
        return ak.stock_zh_a_hist(
            symbol=code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust=adjust,
        )
    except Exception:
        return None


def fetch_klines_akshare(
    symbol: str,
    start_date: str,
    end_date: str,
    period: str = "daily",
    adjust: str = "qfq",
    limit: int | None = None,
) -> List[OHLCV]:
    """
    通过 akshare 拉取 A 股/北交所历史行情，归一化为 OHLCV。
    symbol: 6 位或 8 位代码，如 "000001", "600519", "830799"（北交所）
    start_date / end_date: "20240101" 格式
    period: "daily" | "weekly" | "monthly"
    adjust: "qfq" 前复权 | "hfq" 后复权 | "" 不复权
    limit: 最多返回条数，默认不截断
    """
    if ak is None:
        raise ImportError("akshare is required: pip install akshare")
    code = str(symbol).strip().split(".", maxsplit=1)[0]
    if not code or len(code) < 5 or len(code) > 8:
        raise ValueError("A-share/BSE symbol: 6 or 8 digits, e.g. 000001, 830799")
    df = _fetch_hist_df(code, start_date, end_date, period, adjust)
    if df is None or df.empty:
        return []
    # 列名：日期, 开盘, 收盘, 最高, 最低, 成交量, ...
    col_date = "日期"
    col_o, col_h, col_l, col_c = "开盘", "最高", "最低", "收盘"
    col_vol = "成交量"
    if col_date not in df.columns:
        return []
    out_symbol = _normalize_symbol(code)
    interval = "1d" if period == "daily" else "1w" if period == "weekly" else "1M"
    result = []
    for _, row in df.iterrows():
        try:
            date_val = row[col_date]
            if hasattr(date_val, "to_pydatetime"):
                ts = date_val.to_pydatetime()
            elif isinstance(date_val, str):
                ts = dt.datetime.strptime(date_val[:10], "%Y-%m-%d")
            else:
                ts = dt.datetime.now(dt.timezone.utc)
            ts = _to_utc(ts)
            result.append(
                OHLCV(
                    symbol=out_symbol,
                    timestamp=ts,
                    open=float(row[col_o]),
                    high=float(row[col_h]),
                    low=float(row[col_l]),
                    close=float(row[col_c]),
                    volume=float(row.get(col_vol, 0) or 0),
                    interval=interval,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    if limit is not None and limit > 0:
        result = result[-limit:]
    return result


def _fetch_bse_stock_list() -> List[Dict[str, Any]]:
    """拉取北交所股票列表。"""
    out: List[Dict[str, Any]] = []
    bj = getattr(ak, "stock_info_bj_name_code", None) if ak else None
    if bj is None:
        return out
    try:
        df_bj = ak.stock_info_bj_name_code()
    except Exception:
        return out
    if df_bj is None or df_bj.empty:
        return out
    code_col = "code" if "code" in df_bj.columns else "证券代码"
    name_col = "name" if "name" in df_bj.columns else "证券简称"
    for _, row in df_bj.iterrows():
        code = str(row.get(code_col, row.get("证券代码", ""))).strip()
        name = str(row.get(name_col, row.get("证券简称", ""))).strip()
        if not code:
            continue
        sym = _normalize_symbol(code)
        out.append({"symbol": sym, "name": name or code, "market": "bse"})
    return out


def get_stock_list_akshare(include_bse: bool = True) -> List[Dict[str, Any]]:
    """
    从 akshare 拉取 A 股 + 北交所股票列表，供补全数据时使用。
    返回 [{ "symbol": "600519.SH", "name": "贵州茅台", "market": "sh" }, ...]
    market: sh/sz/bse
    """
    if ak is None:
        raise ImportError("akshare is required: pip install akshare")
    out: List[Dict[str, Any]] = []
    try:
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                name = str(row.get("name", "")).strip()
                if not code:
                    continue
                sym = _normalize_symbol(code)
                market = "sh" if sym.endswith(".SH") else "sz"
                out.append({"symbol": sym, "name": name or code, "market": market})
    except Exception:
        pass
    if include_bse:
        out.extend(_fetch_bse_stock_list())
    return out


def fetch_klines_akshare_minute(
    symbol: str,
    start_date: str,
    end_date: str,
    period: str = "1",
    limit: int | None = None,
) -> List[OHLCV]:
    """
    拉取 A 股分钟线（东方财富源）。period: "1"|"5"|"15"|"30"|"60" 分钟。
    start_date/end_date 格式 "20240101"。
    """
    if ak is None:
        raise ImportError("akshare is required: pip install akshare")
    code = str(symbol).strip().split(".", maxsplit=1)[0]
    if not code or len(code) != 6:
        raise ValueError("A-share symbol must be 6 digits")
    try:
        df = ak.stock_zh_a_hist_min_em(
            symbol=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception:
        return []
    if df is None or df.empty:
        return []
    out_symbol = _normalize_symbol(code)
    interval = f"{period}m"
    result = []
    for _, row in df.iterrows():
        try:
            date_val = row.get("时间", row.get("日期", None))
            if date_val is None:
                continue
            if hasattr(date_val, "to_pydatetime"):
                ts = date_val.to_pydatetime()
            elif isinstance(date_val, str):
                if " " in date_val:
                    ts = dt.datetime.strptime(date_val[:19], "%Y-%m-%d %H:%M:%S")
                else:
                    ts = dt.datetime.strptime(date_val[:10], "%Y-%m-%d")
            else:
                continue
            ts = _to_utc(ts)
            result.append(
                OHLCV(
                    symbol=out_symbol,
                    timestamp=ts,
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=float(row.get("成交量", 0) or 0),
                    interval=interval,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    if limit is not None and limit > 0:
        result = result[-limit:]
    return result
