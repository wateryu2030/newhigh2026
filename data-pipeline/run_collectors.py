#!/usr/bin/env python3
"""统一数据采集器：按优先级重启所有核心数据管道。
用法: cd /Users/apple/Ahope/newhigh && .venv/bin/python data-pipeline/run_collectors.py [--full]
  --full: 全市场日K线更新（耗时数小时），否则仅更新有信号的 30 只个股
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from typing import List

# 确保 data-pipeline 的 src 在 sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))


def _now() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


def step(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  [{_now()}] {name}")
    print(f"{'='*60}")


def run_stock_list() -> int:
    step("1/6 股票池更新")
    try:
        from data_pipeline.collectors import update_stock_list
        n = update_stock_list()
        print(f"  OK: {n} 只股票写入 a_stock_basic")
        return n
    except Exception as e:
        print(f"  FAIL: {e}")
        return 0


def run_realtime_quotes() -> int:
    step("2/6 全市场实时行情")
    try:
        from data_pipeline.collectors import update_realtime_quotes
        n = update_realtime_quotes()
        print(f"  OK: {n} 条行情写入 a_stock_realtime")
        return n
    except Exception as e:
        print(f"  FAIL: {e}")
        return 0


def run_daily_klines(codes: List[str], recent_only: bool = True) -> int:
    step(f"3/6 日K线更新 ({len(codes)} 只{'主要信号' if recent_only else '全市场'}股)")
    from data_pipeline.collectors import update_daily_kline
    total = 0
    errors = 0
    for i, code in enumerate(codes):
        try:
            n = update_daily_kline(str(code))
            total += n
            if (i + 1) % 5 == 0 or i == len(codes) - 1:
                print(f"  [{i+1}/{len(codes)}] 进度: {total} 条, 错误: {errors}")
        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(codes)}] {code} FAIL: {e}")
        time.sleep(0.15)  # 反爬
    print(f"  OK: {total} 条K线写入, 错误: {errors}")
    return total


def run_fund_flow() -> int:
    step("4/6 资金流向")
    try:
        from data_pipeline.collectors import update_fundflow
        n = update_fundflow()
        print(f"  OK: {n} 条资金流写入 a_stock_fundflow")
        return n
    except Exception as e:
        print(f"  FAIL: {e}")
        return 0


def run_limit_up() -> int:
    step("5/6 涨停池")
    try:
        from data_pipeline.collectors import update_limitup
        n = update_limitup()
        print(f"  OK: {n} 条涨停写入 a_stock_limitup")
        return n
    except Exception as e:
        print(f"  FAIL: {e}")
        return 0


def run_longhubang() -> int:
    step("6/6 龙虎榜")
    try:
        from data_pipeline.collectors import update_longhubang
        n = update_longhubang()
        print(f"  OK: {n} 条龙虎榜写入 a_stock_longhubang")
        return n
    except Exception as e:
        print(f"  FAIL: {e}")
        return 0


def get_signal_stocks(limit: int = 50) -> List[str]:
    """从 trade_signals 表获取活跃信号股列表"""
    try:
        import duckdb
        from data_pipeline.storage.duckdb_manager import get_db_path
        conn = duckdb.connect(get_db_path(), read_only=True)
        rows = conn.execute(f"""
            SELECT DISTINCT code FROM trade_signals
            WHERE snapshot_time > '2026-01-01'
            ORDER BY MAX(snapshot_time) DESC
            LIMIT {limit}
        """).fetchall()
        conn.close()
        codes = [r[0] for r in rows]
        print(f"  从 trade_signals 获取 {len(codes)} 只活跃信号股")
        return codes
    except Exception:
        # 回退：核心蓝筹
        codes = [
            "600519", "000858", "601398", "600036", "000001", "600276", "000333",
            "601318", "600900", "002415", "600030", "601012", "000725", "600809",
            "601166", "600585", "000651", "300750", "601888", "002594",
        ]
        print(f"  回退: {len(codes)} 只核心蓝筹")
        return codes


def check_db_health() -> dict:
    """快速数据库健康检查"""
    import duckdb
    from data_pipeline.storage.duckdb_manager import get_db_path
    path = get_db_path()
    if not os.path.exists(path):
        return {"ok": False, "error": f"{path} 不存在"}
    try:
        conn = duckdb.connect(path, read_only=True)
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        n_tables = len(tables)
        # 检查关键表行数
        rt = conn.execute("SELECT COUNT(*) FROM a_stock_realtime").fetchone()[0]
        kline = conn.execute("SELECT COUNT(*) FROM a_stock_daily").fetchone()[0]
        signals = conn.execute("SELECT COUNT(*) FROM trade_signals").fetchone()[0]
        conn.close()
        return {
            "ok": True,
            "db_path": path,
            "db_size_mb": round(os.path.getsize(path) / 1024 / 1024, 1),
            "tables": n_tables,
            "realtime_rows": rt,
            "kline_rows": kline,
            "signal_rows": signals,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="统一数据采集器")
    parser.add_argument("--full", action="store_true", help="全市场K线（耗时长）")
    parser.add_argument("--skip-kline", action="store_true", help="跳过K线更新")
    parser.add_argument("--skip-stocks", action="store_true", help="跳过股票池更新")
    args = parser.parse_args()

    print("=" * 60)
    print("  红山量化平台 - 数据采集器")
    print(f"  启动时间: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 0. 健康检查
    health = check_db_health()
    if not health["ok"]:
        print(f"\n  FATAL: 数据库异常 - {health['error']}")
        sys.exit(1)
    print(f"\n  数据库: {health['db_path']} ({health['db_size_mb']}MB)")
    print(f"  表数量: {health['tables']} | 行情: {health['realtime_rows']}行 | K线: {health['kline_rows']}行 | 信号: {health['signal_rows']}行")

    stats = {}

    # 1. 股票池（先更新，后面采集依赖）
    if not args.skip_stocks:
        stats["stock_list"] = run_stock_list()
        time.sleep(1)

    # 2. 实时行情（最快，信号依赖）
    stats["realtime"] = run_realtime_quotes()

    # 3. 日K线
    if not args.skip_kline:
        if args.full:
            # 全市场 - 从 a_stock_basic 取所有股票
            import duckdb
            conn = duckdb.connect(health["db_path"], read_only=True)
            all_codes = conn.execute(
                "SELECT code FROM a_stock_basic ORDER BY code"
            ).fetchall()
            conn.close()
            codes = [r[0] for r in all_codes]
        else:
            codes = get_signal_stocks(limit=50)
        stats["kline"] = run_daily_klines(codes)
    else:
        stats["kline"] = "(skip)"

    # 4-6. 资金/涨停/龙虎榜
    stats["fundflow"] = run_fund_flow()
    stats["limitup"] = run_limit_up()
    stats["longhubang"] = run_longhubang()

    # 汇总
    print(f"\n{'='*60}")
    print(f"  采集完成 [{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"{'='*60}")

    # 最终健康检查
    health2 = check_db_health()
    if health2["ok"]:
        delta_rt = health2["realtime_rows"] - health["realtime_rows"]
        delta_kl = health2["kline_rows"] - health["kline_rows"]
        print(f"\n  增量: 实时行情 +{delta_rt}行 | K线 +{delta_kl}行")
        print(f"  数据库现 {health2['db_size_mb']}MB")


if __name__ == "__main__":
    main()
