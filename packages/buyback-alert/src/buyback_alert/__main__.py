"""
__main__.py — CLI entry point for ``python -m buyback_alert``.

Usage:
    python -m buyback_alert --run-all
    python -m buyback_alert --collect
    python -m buyback_alert --detect --min-days 3
    python -m buyback_alert --alert
    python -m buyback_alert --collect --symbol 600519
    python -m buyback_alert --dry-run --collect --detect --alert
    python -m buyback_alert --db-path /path/to/custom.duckdb --collect
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

import duckdb

from buyback_alert.collector import run_collect
from buyback_alert.detector import detect_consecutive_drops
from buyback_alert.alerter import cross_reference


def _get_connection(db_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection. Use explicit db_path or fall back to duckdb_manager."""
    if db_path:
        p = Path(db_path).expanduser().resolve()
        if not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(p))
        # Ensure tables exist
        from buyback_alert.collector import _ensure_buyback_table
        from buyback_alert.alerter import _ensure_alerts_table
        _ensure_buyback_table(conn)
        _ensure_alerts_table(conn)
        return conn

    # Try to use duckdb_manager — avoid importing data_pipeline.__init__ (triggers broken tushare_source import)
    try:
        root = Path(__file__).resolve().parent.parent.parent.parent.parent  # newhigh/
        # Directly import the specific module without triggering __init__.py
        import importlib.util

        dp_src = root / "data-pipeline" / "src"
        manager_path = dp_src / "data_pipeline" / "storage" / "duckdb_manager.py"
        if manager_path.exists():
            spec = importlib.util.spec_from_file_location(
                "duckdb_manager", str(manager_path),
                submodule_search_locations=[]
            )
            ddb_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ddb_mod)
            db_path_resolved = ddb_mod.get_db_path()
            conn = duckdb.connect(str(db_path_resolved))
            ddb_mod.ensure_tables(conn)
            return conn
    except Exception as e:
        print(f"[buyback_alert] duckdb_manager import failed: {e}", file=sys.stderr)

    # Fallback: find quant_system.duckdb directly
    try:
        root = Path(__file__).resolve().parent.parent.parent.parent.parent  # newhigh/
    except NameError:
        root = Path.cwd()
    fallback = root / "data" / "quant_system.duckdb"
    print(f"[buyback_alert] 尝试 fallback: {fallback}", file=sys.stderr)
    if fallback.exists():
        conn = duckdb.connect(str(fallback))
        return conn

    raise FileNotFoundError(f"无法找到 DuckDB 数据库。请使用 --db-path 指定路径，或确保 {fallback} 存在。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m buyback_alert",
        description="""\
回购/增持/溢价收购预警系统

功能:
  --collect    从 akshare 采集回购、大宗交易溢价数据，解析新闻关键词，写入 buyback_events 表
  --detect     基于 daily_bars 检测连跌股票（默认 >= 3 日连跌）
  --alert      将连跌股票与 buyback_events 交叉分析，生成预警写入 alerts 表
  --run-all    依次执行 --collect --detect --alert

示例:
  python -m buyback_alert --run-all
  python -m buyback_alert --collect --detect --alert
  python -m buyback_alert --detect --min-days 5
  python -m buyback_alert --collect --symbol 600519
  python -m buyback_alert --dry-run --collect --detect --alert
  python -m buyback_alert --db-path /path/to/custom.duckdb --detect --min-days 3
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--collect",
        action="store_true",
        help="采集回购/增持/溢价收购数据到 buyback_events 表",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="检测连跌股票（基于 daily_bars）",
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="交叉分析连跌+回购事件，生成预警",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="依次执行采集 → 检测 → 预警",
    )
    parser.add_argument(
        "--min-days",
        type=int,
        default=3,
        help="连跌最小天数（默认: 3）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不写入数据库",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="限定单只股票代码（如 600519 或 600519.XSHG）",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="DuckDB 数据库路径（默认自动获取）",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not any([args.collect, args.detect, args.alert, args.run_all]):
        parser.print_help()
        return 0

    if args.run_all:
        args.collect = True
        args.detect = True
        args.alert = True

    # Get connection (with write lock for write operations)
    conn = _get_connection(args.db_path)
    print(f"[buyback_alert] 数据库: {conn.execute('SELECT current_database()').fetchone()[0]}")

    try:
        if args.collect:
            print("\n=== 第一步: 数据采集 ===")
            run_collect(conn, dry_run=args.dry_run, symbol=args.symbol)

        if args.detect:
            print("\n=== 第二步: 连跌检测 ===")
            drops = detect_consecutive_drops(
                conn,
                min_days=args.min_days,
                symbol=args.symbol,
                dry_run=args.dry_run,
            )
            print(f"检测结果: {len(drops)} 只股票连跌 ≥ {args.min_days} 天")
            if drops and not args.dry_run and not args.alert:
                # Print summary table
                print("\n{:<10} {:<12} {:<6} {:<10} {:<12} {:<12}".format(
                    "代码", "名称", "天数", "跌幅%", "开始", "结束"
                ))
                print("-" * 65)
                for d in drops:
                    print("{:<10} {:<12} {:<6} {:<10.2f} {:<12} {:<12}".format(
                        d["stock_code"], d["stock_name"],
                        d["consecutive_drop_days"], d["total_drop_pct"],
                        d["start_date"], d["end_date"],
                    ))

        if args.alert:
            print("\n=== 第三步: 交叉预警 ===")
            if not args.detect:
                # Run detection with defaults if not already done
                drops = detect_consecutive_drops(
                    conn,
                    min_days=args.min_days,
                    symbol=args.symbol,
                    dry_run=args.dry_run,
                )
            alerts = cross_reference(conn, drops, dry_run=args.dry_run)
            print(f"预警结果: 生成 {len(alerts)} 条预警")
            if alerts and not args.dry_run:
                print("\n{:<14} {:<10} {:<12} {:<6} {:<10}".format(
                    "类型", "代码", "名称", "天数", "跌幅%"
                ))
                print("-" * 55)
                for a in alerts:
                    print("{:<14} {:<10} {:<12} {:<6} {:<10.2f}".format(
                        a["alert_type"], a["stock_code"], a["stock_name"],
                        a["consecutive_drop_days"], a["total_drop_pct"],
                    ))

    except KeyboardInterrupt:
        print("\n[buyback_alert] 用户中断")
        conn.close()
        return 130
    except Exception as e:
        print(f"\n[buyback_alert] 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        conn.close()
        return 1

    conn.close()
    print("\n[buyback_alert] 完成 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
