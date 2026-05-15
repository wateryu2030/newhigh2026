"""
选股/截面筛选 API：大宗交易 × 区间震荡等。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Query

from .response_utils import json_fail, json_ok

_log = logging.getLogger(__name__)


def build_screening_router() -> APIRouter:
    r = APIRouter(prefix="/screen", tags=["screening"])

    @r.get("/block-trade-sideways")
    def block_trade_sideways(
        block_days: int = Query(30, ge=5, le=120, description="回溯自然日，拉取该区间内大宗成交汇总"),
        lookback_days: int = Query(60, ge=15, le=250, description="日 K 窗口（交易日条数，取库内最近 N 条）"),
        range_ratio_max: float = Query(
            0.32,
            ge=0.08,
            le=0.8,
            description="区间震荡：(区间高低差)/均价 上限，越小越「窄」",
        ),
        trend_abs_max: float = Query(
            0.12,
            ge=0.02,
            le=0.5,
            description="窗口首尾涨跌幅绝对值上限，过滤强趋势",
        ),
        ret_std_max: float = Query(
            0.035,
            ge=0.005,
            le=0.2,
            description="日收益波动率上限",
        ),
        min_amount_wan: float = Query(
            0,
            ge=0,
            description="大宗累计成交额下限（万元），0 表示不限制",
        ),
        max_codes: int = Query(400, ge=50, le=2000, description="参与扫描的大宗标的数量上限（按成交额排序截断）"),
    ) -> Any:
        """
        筛选：区间内有大宗成交，且同期日 K 呈区间震荡（非单边、波动有限）。

        依赖：AkShare 大宗接口 + DuckDB ``a_stock_daily``；无 Tushare 积分要求。
        """
        from datetime import date, timedelta

        from data_pipeline.analysis.block_trade_sideways import run_screen
        from data_pipeline.storage.duckdb_manager import DuckDbFileBusy, get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return json_fail("DuckDB 不可用", status_code=503)

        ed = date.today()
        sd = ed - timedelta(days=block_days)
        block_start = sd.strftime("%Y%m%d")
        block_end = ed.strftime("%Y%m%d")

        conn: Optional[Any] = None
        try:
            # 只读 SELECT，勿在此 ensure_tables（DDL 与只读连接冲突且会争锁）
            conn = get_conn(read_only=True)
            out = run_screen(
                conn,
                block_start=block_start,
                block_end=block_end,
                lookback_days=lookback_days,
                range_ratio_max=range_ratio_max,
                trend_abs_max=trend_abs_max,
                ret_std_max=ret_std_max,
                min_amount_wan=min_amount_wan,
                max_codes=max_codes,
            )
        except DuckDbFileBusy as e:
            _log.warning("block_trade_sideways duckdb busy: %s", e)
            return json_fail(str(e)[:400], status_code=503)
        except Exception as e:
            _log.exception("block_trade_sideways")
            return json_fail(str(e)[:300], status_code=500)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    _log.error("Failed to close database connection", exc_info=True)

        if not out.get("ok"):
            return json_fail(str(out.get("error") or "筛选失败"), status_code=502)

        body = {k: v for k, v in out.items() if k != "ok"}
        return json_ok(body, source="screening")

    return r
