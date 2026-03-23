#!/usr/bin/env python3
"""
检查各股票「前十大股东」数据在 DuckDB 中的覆盖情况。

依赖: lib.database（默认 data/quant_system.duckdb，可用 QUANT_DB_PATH 覆盖）

用法:
  python scripts/check_top10_shareholders_coverage.py
  python scripts/check_top10_shareholders_coverage.py --sample-missing 20
  python scripts/check_top10_shareholders_coverage.py --json
  python scripts/check_top10_shareholders_coverage.py --write-missing reports/missing_stocks.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))


def check_coverage(
    sample_missing: int = 0,
    max_missing_file: int = 50_000,
    write_missing_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    执行覆盖检查，返回可 JSON 序列化的字典。
    write_missing_path 若给定，写入缺失股票代码（一行一个），最多 max_missing_file 行。
    """
    from lib.database import get_connection, get_db_path

    out: Dict[str, Any] = {
        "ok": True,
        "database_path": get_db_path(),
        "check": "top_10_shareholders",
    }

    conn = get_connection(read_only=False)
    if conn is None:
        return {"ok": False, "error": "无法连接数据库"}

    try:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' AND table_name='top_10_shareholders'"
        ).fetchall()
        if not tables:
            return {"ok": False, "error": "表 top_10_shareholders 不存在"}

        row = conn.execute("SELECT COUNT(*) FROM top_10_shareholders").fetchone()
        total_rows = int(row[0]) if row else 0

        row = conn.execute(
            "SELECT COUNT(DISTINCT stock_code), COUNT(DISTINCT report_date) FROM top_10_shareholders"
        ).fetchone()
        n_stocks = int(row[0]) if row else 0
        n_report_dates = int(row[1]) if row else 0

        row = conn.execute(
            "SELECT MIN(report_date)::VARCHAR, MAX(report_date)::VARCHAR FROM top_10_shareholders"
        ).fetchone()
        min_rd, max_rd = (row[0], row[1]) if row else (None, None)

        dist = conn.execute(
            """
            WITH per AS (
              SELECT stock_code, COUNT(DISTINCT report_date) AS periods
              FROM top_10_shareholders
              GROUP BY 1
            )
            SELECT periods, COUNT(*) AS stocks
            FROM per
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
        period_distribution = [{"periods": int(p), "stocks": int(s)} for p, s in dist]

        latest = conn.execute("SELECT MAX(report_date) FROM top_10_shareholders").fetchone()
        latest_rd = latest[0] if latest and latest[0] is not None else None

        stocks_on_latest: Optional[int] = None
        if latest_rd:
            r3 = conn.execute(
                "SELECT COUNT(DISTINCT stock_code) FROM top_10_shareholders WHERE report_date = ?",
                [latest_rd],
            ).fetchone()
            stocks_on_latest = int(r3[0]) if r3 else 0

        incomplete_latest: List[Dict[str, Any]] = []
        if latest_rd:
            rows_inc = conn.execute(
                """
                SELECT stock_code, COUNT(*) AS cnt
                FROM top_10_shareholders
                WHERE report_date = ?
                GROUP BY 1
                HAVING COUNT(*) < 10
                ORDER BY cnt ASC
                LIMIT 15
                """,
                [latest_rd],
            ).fetchall()
            incomplete_latest = [{"stock_code": str(c), "rows": int(cnt)} for c, cnt in rows_inc]

        basic_count = 0
        missing_in_holder = 0
        coverage_rate: Optional[float] = None
        sample_codes: List[str] = []
        missing_codes: List[str] = []

        try:
            basic_count = conn.execute(
                "SELECT COUNT(DISTINCT code) FROM a_stock_basic "
                "WHERE code IS NOT NULL AND TRIM(CAST(code AS VARCHAR)) <> ''"
            ).fetchone()
            basic_count = int(basic_count[0]) if basic_count else 0

            missing_in_holder = conn.execute(
                """
                SELECT COUNT(*)
                FROM (
                  SELECT DISTINCT b.code AS stock_code
                  FROM a_stock_basic b
                  LEFT JOIN top_10_shareholders t ON t.stock_code = b.code
                  WHERE b.code IS NOT NULL AND TRIM(CAST(b.code AS VARCHAR)) <> ''
                    AND t.stock_code IS NULL
                ) x
                """
            ).fetchone()
            missing_in_holder = int(missing_in_holder[0]) if missing_in_holder else 0

            if basic_count:
                covered = basic_count - missing_in_holder
                coverage_rate = round((covered / basic_count) * 100, 2)

            lim = sample_missing if sample_missing > 0 else 0
            if lim:
                rows = conn.execute(
                    """
                    SELECT b.code
                    FROM a_stock_basic b
                    LEFT JOIN top_10_shareholders t ON t.stock_code = b.code
                    WHERE b.code IS NOT NULL AND TRIM(CAST(b.code AS VARCHAR)) <> ''
                      AND t.stock_code IS NULL
                    ORDER BY b.code
                    LIMIT ?
                    """,
                    [lim],
                ).fetchall()
                sample_codes = [str(r[0]) for r in rows]

            q_missing = conn.execute(
                """
                SELECT b.code
                FROM a_stock_basic b
                LEFT JOIN top_10_shareholders t ON t.stock_code = b.code
                WHERE b.code IS NOT NULL AND TRIM(CAST(b.code AS VARCHAR)) <> ''
                  AND t.stock_code IS NULL
                ORDER BY b.code
                LIMIT ?
                """,
                [max_missing_file],
            ).fetchall()
            missing_codes = [str(r[0]) for r in q_missing]
        except Exception as ex:
            out["basic_table_warning"] = str(ex)[:200]

        out.update(
            {
                "total_rows": total_rows,
                "distinct_stocks_with_data": n_stocks,
                "distinct_report_dates": n_report_dates,
                "report_date_min": min_rd,
                "report_date_max": max_rd,
                "latest_report_date": str(latest_rd) if latest_rd is not None else None,
                "stocks_on_latest_report_date": stocks_on_latest,
                "period_distribution": period_distribution,
                "incomplete_on_latest_sample": incomplete_latest,
                "a_stock_basic_count": basic_count,
                "missing_stocks_count": missing_in_holder,
                "coverage_rate_pct": coverage_rate,
                "missing_sample_codes": sample_codes,
                "missing_list_truncated": missing_in_holder > len(missing_codes),
            }
        )

        if write_missing_path is not None and missing_codes:
            write_missing_path.parent.mkdir(parents=True, exist_ok=True)
            write_missing_path.write_text("\n".join(missing_codes) + "\n", encoding="utf-8")
            out["missing_stocks_file"] = str(write_missing_path.resolve())
            out["missing_stocks_file_count"] = len(missing_codes)

    finally:
        conn.close()

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 top_10_shareholders 覆盖情况")
    parser.add_argument("--sample-missing", type=int, default=0, help="打印缺失代码示例数量")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--write-missing",
        type=str,
        default="",
        help="将缺失股票代码写入文件（一行一个）",
    )
    parser.add_argument(
        "--max-missing-file",
        type=int,
        default=50_000,
        help="写入缺失列表的最大行数",
    )
    args = parser.parse_args()

    wpath = Path(args.write_missing) if args.write_missing.strip() else None

    rep = check_coverage(
        sample_missing=args.sample_missing,
        max_missing_file=args.max_missing_file,
        write_missing_path=wpath,
    )

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1

    path = rep.get("database_path", "")
    print(f"数据库: {path}\n")
    if not rep.get("ok"):
        print("❌", rep.get("error", "unknown"))
        return 1

    print("=== top_10_shareholders 概览 ===")
    print(f"  总记录数:     {rep['total_rows']:,}")
    print(f"  有数据股票数: {rep['distinct_stocks_with_data']:,}")
    print(f"  不同报告期数: {rep['distinct_report_dates']:,}")
    print(f"  报告期范围:   {rep.get('report_date_min')} ~ {rep.get('report_date_max')}")
    if rep.get("latest_report_date"):
        print(f"  最新报告期:   {rep['latest_report_date']}")
        if rep.get("stocks_on_latest_report_date") is not None:
            print(f"  该期股票数:   {rep['stocks_on_latest_report_date']:,}")

    print("\n=== 每股报告期数分布（distinct report_date）===")
    pdist = rep.get("period_distribution") or []
    if not pdist:
        print("  （无数据）")
    else:
        for item in pdist[:20]:
            print(f"  {item['periods']} 期: {item['stocks']:,} 只股票")
        if len(pdist) > 20:
            print(f"  ... 共 {len(pdist)} 档")

    inc = rep.get("incomplete_on_latest_sample") or []
    if inc:
        print("\n=== 最新报告期下不足 10 条记录的股票（示例）===")
        for item in inc:
            print(f"  {item['stock_code']}: {item['rows']} 条")

    bc = rep.get("a_stock_basic_count") or 0
    if bc:
        print("\n=== 与 a_stock_basic 对比 ===")
        print(f"  股票表标的数:     {bc:,}")
        cr = rep.get("coverage_rate_pct")
        miss = rep.get("missing_stocks_count", 0)
        print(f"  覆盖率:           {cr}%")
        print(f"  股票表无股东记录: {miss:,}")
        if rep.get("missing_sample_codes"):
            print(f"  缺失示例代码: {', '.join(rep['missing_sample_codes'])}")
    if wpath:
        print(f"\n已写入缺失列表: {rep.get('missing_stocks_file')} ({rep.get('missing_stocks_file_count', 0)} 行)")

    print("\n=== 采集说明 ===")
    print("  全量/补采: python scripts/run_shareholder_collect.py --shareholders-only")
    print("  指定补采: python scripts/run_shareholder_collect.py --shareholders-only --stocks-file reports/missing_stocks.txt")
    print("  定时任务:  scripts/start_schedulers.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
