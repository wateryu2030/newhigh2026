#!/usr/bin/env python3
"""
量化平台数据就绪检查（对齐 docs/ITERATION_AND_DATA_SLA.md、scripts/check_goals.py）。

不启动 Gateway 也可跑：直接读 quant_system.duckdb；可选 --live 再探 /health 与 /api/data/status。

用法:
  python scripts/verify_quant_readiness.py
  python scripts/verify_quant_readiness.py --strict   # 硬 WARN 时退出码 1（资金流空表除外，见下）
  python scripts/verify_quant_readiness.py --live     # 需本机 :8000 Gateway

--strict 与 a_stock_fundflow:
  · 行数为 0 或表不可读 → 打印 WARN，记入「软 WARN」；strict 下仍退出 0（不阻断 CI）
  · 行数 >0 但仍偏少：当 a_stock_basic≥800 时，要求
    ``effective_min = max(NEWHIGH_FUND_FLOW_STRICT_MIN, basic÷25)``（默认环境变量 400，即至少池子约 4%）
    低于 effective_min → 硬 WARN「覆盖偏低」，strict 下退出 1
  · 小库（basic<800）不判「稀疏」，避免本地迷你库误伤
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_DP = ROOT / "data-pipeline" / "src"
if _DP.is_dir():
    p = str(_DP)
    if p not in sys.path:
        sys.path.insert(0, p)


def _count(conn: Any, table: str) -> int | None:
    try:
        r = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(r[0]) if r and r[0] is not None else 0
    except Exception:
        return None


def _daily_bounds(conn: Any) -> tuple[str | None, str | None]:
    try:
        r = conn.execute(
            "SELECT MIN(date), MAX(date) FROM a_stock_daily"
        ).fetchone()
        if not r:
            return None, None
        d0 = r[0]
        d1 = r[1]
        return (
            str(d0)[:10] if d0 is not None else None,
            str(d1)[:10] if d1 is not None else None,
        )
    except Exception:
        return None, None


def _days_behind_latest(date_max_s: str | None) -> int | None:
    if not date_max_s:
        return None
    try:
        d = datetime.strptime(date_max_s[:10], "%Y-%m-%d").date()
        return (date.today() - d).days
    except ValueError:
        return None


def _check_fundflow_strictness(
    counts: dict[str, int | None],
    n_basic: int,
    strict: bool,
    warns: list[str],
    soft_warns: list[str],
) -> None:
    """
    资金流表：空表仅软 WARN（strict 不失败）；大池子下覆盖不足为硬 WARN。
    阈值：effective_min = max(NEWHIGH_FUND_FLOW_STRICT_MIN, basic//25)，且仅 basic>=800 时检查稀疏。
    """
    fn = counts.get("a_stock_fundflow")
    empty = fn is None or fn == 0
    if empty:
        print(
            "INFO a_stock_fundflow 为空 → 资金类扫描/卡片弱: 跑 data 更新或 scripts/start_schedulers.py intraday-now"
        )
    if strict and empty:
        soft_warns.append("a_stock_fundflow_empty")
        print(
            "WARN [strict] a_stock_fundflow 无数据（不阻断退出码）→ 请跑日内/数据 orchestrator 写入资金流"
        )
        return
    if not strict or empty:
        return
    try:
        env_floor = int(str(os.environ.get("NEWHIGH_FUND_FLOW_STRICT_MIN", "400")).strip() or "400")
    except ValueError:
        env_floor = 400
    pool = max(0, int(n_basic))
    if pool < 800:
        return
    effective_min = max(env_floor, pool // 25)
    if fn is not None and fn < effective_min:
        warns.append("a_stock_fundflow_sparse")
        print(
            f"WARN [strict] a_stock_fundflow={fn} < 建议下限 {effective_min} "
            f"(max(NEWHIGH_FUND_FLOW_STRICT_MIN={env_floor}, basic÷25={pool//25})) → 覆盖偏低"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Quant DB + optional Gateway readiness")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="硬 WARN 时退出码 1（a_stock_fundflow 空表仅为软 WARN，仍退出 0）",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="探测 http://127.0.0.1:8000 /health 与 /api/data/status",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("GATEWAY_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
    )
    args = parser.parse_args()

    warns: list[str] = []
    soft_warns: list[str] = []
    critical: list[str] = []

    print("=" * 64)
    print("newhigh 量化数据就绪检查")
    print("=" * 64)

    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
    except ImportError as e:
        print(f"CRITICAL 无法导入 data_pipeline: {e}")
        return 2

    dbp = get_db_path()
    print(f"DuckDB 路径: {dbp}")
    if not os.path.isfile(dbp):
        critical.append("数据库文件不存在")
        print("CRITICAL 数据库文件不存在 → 运行: python scripts/ensure_market_data.py（或 pipeline 灌库）")
        _print_remediation()
        return 1

    conn = None
    try:
        conn = get_conn(read_only=True)
    except Exception as e:
        warns.append("duckdb_lock_or_io")
        print(
            f"WARN 无法只读打开 DuckDB（常见于 Gateway/调度占用写锁）: {e}\n"
            "  → 可停 uvicorn 后重试本脚本，或仅用 --live 依赖 Gateway JSON（不含表级明细）。"
        )

    if conn is None:
        if not args.live:
            print("提示: 加 --live 可在锁库时仍检查 /health 与 /api/data/status")

    if conn is not None:
        try:
            tables = (
                "a_stock_basic",
                "a_stock_daily",
                "a_stock_realtime",
                "a_stock_limitup",
                "a_stock_fundflow",
                "news_items",
                "market_signals",
                "trade_signals",
            )
            counts: dict[str, int | None] = {}
            for t in tables:
                counts[t] = _count(conn, t)
                v = counts[t]
                label = "—" if v is None else str(v)
                print(f"  {t}: {label}")

            n_basic = counts.get("a_stock_basic") or 0
            if n_basic < 100:
                warns.append("a_stock_basic 过少")
                print(f"WARN 股票主表仅 {n_basic} 行（全市场通常数千）→ ensure_market_data / Tushare 股票列表")

            dmin, dmax = _daily_bounds(conn)
            print(f"  a_stock_daily 日期范围: {dmin or '—'} ~ {dmax or '—'}")
            behind = _days_behind_latest(dmax)
            if behind is not None:
                print(f"  日线最新距今: {behind} 个自然日")
                if behind > 14:
                    warns.append("日线过旧")
                    print(
                        "WARN 日线最新日期偏旧 → 跑调度或: python scripts/ensure_market_data.py / "
                        "scripts/backfill_a_stock_daily.py（见 docs/ITERATION_AND_DATA_SLA.md）"
                    )
                elif behind > 5:
                    print(
                        "INFO 日线略旧（可能节假日）→ 确认 TUSHARE_TOKEN 与 start_schedulers 日任务"
                    )

            n_daily = counts.get("a_stock_daily")
            if n_daily is not None and n_daily == 0:
                warns.append("无日线")
                print("WARN a_stock_daily 为空 → 同上回补日线")

            if counts.get("market_signals") == 0:
                print(
                    "INFO market_signals 为空 → 策略/首页部分卡片空: python scripts/run_full_cycle.py --skip-data"
                )
            _check_fundflow_strictness(
                counts, n_basic, args.strict, warns, soft_warns
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass

    if args.live:
        print("-" * 64)
        print(f"Live Gateway: {args.base_url}")
        try:
            import urllib.request

            for path in ("/health", "/api/data/status"):
                url = f"{args.base_url}{path}"
                req = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "newhigh-verify-quant-readiness/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    body = json.loads(r.read().decode())
                if path == "/health":
                    ok = isinstance(body, dict) and body.get("status") == "ok"
                    print(f"  {path} -> {'OK' if ok else 'unexpected'}")
                    if not ok:
                        warns.append("health 异常")
                else:
                    ok = isinstance(body, dict) and body.get("ok") is True
                    print(f"  {path} -> ok={body.get('ok')} source={body.get('source')}")
                    if not ok:
                        warns.append("data/status 未就绪")
        except Exception as e:
            warns.append(f"live 探测失败: {e}")
            print(f"WARN Live 探测失败（Gateway 未起或端口不对）: {e}")

    print("=" * 64)
    if critical:
        print("结果: CRITICAL", "; ".join(critical))
        _print_remediation()
        return 1
    if warns:
        print("结果: WARN", "; ".join(warns))
        if soft_warns:
            print("     软 WARN（strict 不因此失败）:", "; ".join(soft_warns))
        _print_remediation()
        return 1 if args.strict else 0
    if soft_warns:
        print("结果: WARN（软，strict 仍退出 0）", "; ".join(soft_warns))
        _print_remediation()
        return 0
    print("结果: OK（无 WARN）")
    return 0


def _print_remediation() -> None:
    print(
        "建议: docs/ITERATION_AND_DATA_SLA.md | "
        "python scripts/check_goals.py | "
        "bash scripts/verify_homepage_apis.sh | "
        "bash scripts/heartbeat_check.sh"
    )


if __name__ == "__main__":
    sys.exit(main())
