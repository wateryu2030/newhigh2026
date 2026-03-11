"""
数据调度：统一调用 data_pipeline collectors，执行股票池、日K、实时、资金流、涨停、龙虎榜更新。
"""
from __future__ import annotations

from typing import Dict, Any


def update(
    run_stock_list: bool = True,
    run_daily_kline: bool = False,
    run_realtime: bool = True,
    run_fundflow: bool = True,
    run_limitup: bool = True,
    run_longhubang: bool = True,
    daily_kline_codes_limit: int = 0,
    use_incremental_daily_kline: bool = False,
    use_incremental_longhubang: bool = False,
) -> Dict[str, Any]:
    """
    按开关执行各 collector，返回各步骤写入条数或状态。
    run_daily_kline 为 True 且 daily_kline_codes_limit > 0 时批量拉日 K（耗时长）。
    use_incremental_daily_kline 为 True 时优先用数据源增量更新日 K（按 last_date 拉新数据）。
    use_incremental_longhubang 为 True 时用数据源增量更新龙虎榜。
    """
    result = {
        "stock_list": 0,
        "daily_kline": 0,
        "realtime": 0,
        "fundflow": 0,
        "limitup": 0,
        "longhubang": 0,
        "errors": [],
    }
    try:
        from data_pipeline.collectors import (
            update_stock_list,
            update_daily_kline,
            update_realtime_quotes,
            update_fundflow,
            update_limitup,
            update_longhubang,
        )
        from data_pipeline.storage.duckdb_manager import get_conn
    except ImportError as e:
        result["errors"].append(str(e))
        return result

    if run_stock_list:
        try:
            result["stock_list"] = update_stock_list()
        except Exception as e:
            result["errors"].append(f"stock_list: {e}")

    if run_daily_kline:
        if use_incremental_daily_kline:
            try:
                from data_pipeline import run_incremental
                result["daily_kline"] = run_incremental("ashare_daily_kline", force_full=False)
            except Exception as e:
                result["errors"].append(f"daily_kline incremental: {e}")
        elif daily_kline_codes_limit > 0:
            try:
                conn = get_conn(read_only=True)
                df = conn.execute("SELECT code FROM a_stock_basic LIMIT ?", [daily_kline_codes_limit]).fetchdf()
                conn.close()
                if df is not None and not df.empty:
                    for code in df["code"].astype(str).tolist():
                        try:
                            result["daily_kline"] += update_daily_kline(code)
                        except Exception as e:
                            result["errors"].append(f"daily_kline {code}: {e}")
            except Exception as e:
                result["errors"].append(f"daily_kline batch: {e}")

    if run_realtime:
        try:
            result["realtime"] = update_realtime_quotes()
        except Exception as e:
            result["errors"].append(f"realtime: {e}")

    if run_fundflow:
        try:
            result["fundflow"] = update_fundflow()
        except Exception as e:
            result["errors"].append(f"fundflow: {e}")

    if run_limitup:
        try:
            result["limitup"] = update_limitup()
        except Exception as e:
            result["errors"].append(f"limitup: {e}")

    if run_longhubang:
        if use_incremental_longhubang:
            try:
                from data_pipeline import run_incremental
                result["longhubang"] = run_incremental("ashare_longhubang", force_full=False)
            except Exception as e:
                result["errors"].append(f"longhubang incremental: {e}")
        else:
            try:
                result["longhubang"] = update_longhubang()
            except Exception as e:
                result["errors"].append(f"longhubang: {e}")

    return result
