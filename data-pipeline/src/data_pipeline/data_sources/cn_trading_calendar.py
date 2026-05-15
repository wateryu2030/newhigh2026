"""
A 股日线增量拉取用的「合理结束日期」。

东财 akshare 的 `stock_zh_a_hist_em(..., end_date=YYYYMMDD)` 在 **end 落在周六、周日**
时，部分环境下会整段返回空表，导致增量批次 +0 行（误以为接口故障）。

处理：将 **周末** 的「今天」回退到 **上一交易日（周五）**；法定节假日暂不解析（可后续接交易所日历）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


def incremental_range_empty(start_key: Optional[str], end_yyyymmdd: str) -> bool:
    """
    增量拉取：库内最后交易日为 start_key（YYYYMMDD）时，下一交易日为拉取起点；
    若起点已晚于 end_yyyymmdd，则无区间可拉（多为已对齐到截止日）。
    """
    if not start_key:
        return False
    try:
        nxt = datetime.strptime(start_key[:8], "%Y%m%d") + timedelta(days=1)
        return nxt.strftime("%Y%m%d") > end_yyyymmdd
    except Exception:
        return False


def cn_ashare_increment_end_yyyymmdd(now: Optional[datetime] = None) -> str:
    """
    用于 ashare / tushare 日 K 增量的默认 end_key（YYYYMMDD）。

    - 周六、周日 → 使用周五日期，避免东财接口对 end 落在休市日时的空返回。
    - 周一至周五 → 使用当日历日（收盘后数据一般已可用；盘前未开盘时仍可能少当日 K，属预期）。
    """
    dt = now or datetime.now()
    d = dt.date()
    wd = d.weekday()  # 0=周一 … 6=周日
    if wd == 5:  # 周六
        d = d - timedelta(days=1)
    elif wd == 6:  # 周日
        d = d - timedelta(days=2)
    return d.strftime("%Y%m%d")
