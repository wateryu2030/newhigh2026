"""
A股财务报告采集器 (CLI)

使用 akshare.stock_financial_report_sina 下载 A 股上市公司财务报告（资产负债表、
利润表、现金流量表），将数据写入 DuckDB 统一数据仓库。

用法:
    python -m financial_report --symbol 600519
    python -m financial_report --symbols 600519,000858
    python -m financial_report --batch --limit 10 --statement-type 利润表
    python -m financial_report --batch --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# 模块级路径修补，使 lib/ 与 data-pipeline/ 可导入
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_PKG_ROOT = _THIS_FILE.parent.parent.parent.parent  # financial-report/
_NEWHIGH_ROOT = _PKG_ROOT.parent                    # newhigh/
for _p in (
    _NEWHIGH_ROOT,
    str(_NEWHIGH_ROOT / "lib"),
    str(_NEWHIGH_ROOT / "data-pipeline" / "src"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
STATEMENT_TYPES = ("资产负债表", "利润表", "现金流量表")

MONTH_TO_REPORT_TYPE: Dict[int, str] = {
    1: "年报",
    2: "年报",
    3: "一季报",
    4: "一季报",
    5: "中报/半年报",
    6: "中报/半年报",
    7: "中报/半年报",
    8: "中报/半年报",
    9: "三季报",
    10: "三季报",
    11: "三季报",
    12: "年报",
}

# Sina 报告日 2025-12-31 => 年报 (extra rule in determine_report_type)


def determine_report_type(report_date_str: str) -> str:
    """根据报告日期字符串 (YYYYMMDD 或 YYYY-MM-DD) 推测报告类型。"""
    if not report_date_str or len(report_date_str) < 6:
        return "年报"
    # 兼容 YYYY-MM-DD / YYYYMMDD / YYYY/MM/DD
    cleaned = report_date_str.replace("-", "").replace("/", "").strip()
    if len(cleaned) < 8:
        return "年报"
    try:
        y = int(cleaned[:4])
        m = int(cleaned[4:6])
        d = int(cleaned[6:8])
    except ValueError:
        return "年报"
    # 12-31 强制为年报
    if m == 12 and d == 31:
        return "年报"
    return MONTH_TO_REPORT_TYPE.get(m, "年报")


def _db_path() -> str:
    """获取 DuckDB 路径（同 duckdb_manager.get_db_path 语义）。"""
    env_var = (
        os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "")
        or os.environ.get("QUANT_DB_PATH", "")
        or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "")
        or os.environ.get("NEWHIGH_DB_PATH", "")
    )
    if env_var:
        return env_var
    env_file = _NEWHIGH_ROOT / ".env"
    if env_file.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(str(env_file))
        except ImportError:
            pass
        env_var = (
            os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "")
            or os.environ.get("QUANT_DB_PATH", "")
            or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "")
            or os.environ.get("NEWHIGH_DB_PATH", "")
        )
        if env_var:
            return env_var
    return str(_NEWHIGH_ROOT / "data" / "quant_system.duckdb")


def ensure_table(conn: duckdb.DuckDBPyConnection) -> None:
    """确保 financial_reports 表存在。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_reports (
            stock_code     VARCHAR,
            report_date    DATE,
            report_type    VARCHAR,
            statement_type VARCHAR,
            period_end     VARCHAR,
            data_json      JSON,
            currency       VARCHAR DEFAULT 'CNY',
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )


def fetch_sina_financial_report(
    stock_code: str,
    statement_type: str,
) -> pd.DataFrame:
    """调用 akshare 下载指定股票、指定报表类型的原始数据。

    Args:
        stock_code: 6 位 A 股代码（如 '600519'）。
        statement_type: 报表类型（资产负债表/利润表/现金流量表）。

    Returns:
        DataFrame，包含 sina 返回的全部列；失败时返回空 DataFrame。
    """
    import akshare as ak

    try:
        df = ak.stock_financial_report_sina(
            stock=f"sh{stock_code}", symbol=statement_type
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as exc:
        print(
            f"  [警告] 下载 {stock_code} {statement_type} 失败: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return pd.DataFrame()


def _extract_currency(row: dict) -> str:
    """从行数据中提取币种，默认 'CNY'。"""
    return row.get("币种", "CNY") or "CNY"


def parse_sina_rows(
    stock_code: str,
    statement_type: str,
    df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """将 sina 返回的 DataFrame 解析为插入行列表。

    每行包含:
        - stock_code, report_date, report_type, statement_type
        - period_end: 直接从 row 的 '类型' 列提取
        - data_json: 整行原始数据的 JSON 字符串
        - currency

    Args:
        stock_code: 股票代码。
        statement_type: 报表类型。
        df: akshare 返回的 DataFrame（含 报告日、公告日期, 币种 等列）。

    Returns:
        可写入 duckdb 的行字典列表。
    """
    rows: List[Dict[str, Any]] = []
    now_ts = datetime.now()

    for _, record in df.iterrows():
        row_dict = record.to_dict()
        report_date_str = str(row_dict.get("报告日", "") or "")

        if not report_date_str:
            continue

        # 规范化报告日期
        try:
            report_date = datetime.strptime(report_date_str, "%Y%m%d").date()
        except ValueError:
            try:
                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
            except ValueError:
                continue

        report_type = determine_report_type(report_date_str)
        period_end = str(row_dict.get("类型", "") or "")
        currency = _extract_currency(row_dict)
        data_json = json.dumps(row_dict, ensure_ascii=False, default=str)

        rows.append(
            {
                "stock_code": stock_code,
                "report_date": report_date,
                "report_type": report_type,
                "statement_type": statement_type,
                "period_end": period_end,
                "data_json": data_json,
                "currency": currency,
                "created_at": now_ts,
            }
        )

    return rows


def get_stocks_from_db(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """从 quant.duckdb 的 stocks 表中获取所有 A 股代码。"""
    try:
        result = conn.execute(
            "SELECT DISTINCT symbol FROM stocks WHERE symbol IS NOT NULL AND symbol != '' ORDER BY symbol"
        ).fetchall()
        codes = [str(r[0]).strip() for r in result if r[0]]
        # 仅保留纯数字 6 位代码
        return [c for c in codes if c.isdigit() and len(c) == 6]
    except Exception as exc:
        print(f"[错误] 查询 stocks 表失败: {exc}", file=sys.stderr, flush=True)
        return []


def deduplicate_stock_reports(
    conn: duckdb.DuckDBPyConnection,
    stock_code: str,
    statement_type: str,
    report_dates: List[date],
) -> set:
    """查询已存在的记录，返回已存在的报告日期集合。"""
    if not report_dates:
        return set()
    existing = conn.execute(
        """
        SELECT DISTINCT report_date
        FROM financial_reports
        WHERE stock_code = ? AND statement_type = ?
          AND report_date IN ({})
        """.format(",".join("?" for _ in report_dates)),
        [stock_code, statement_type] + report_dates,
    ).fetchall()
    return {r[0] for r in existing}


def write_reports(
    conn: duckdb.DuckDBPyConnection,
    rows: List[Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    """批量写入 financial_reports 表。

    Args:
        conn: DuckDB 连接。
        rows: 待写入的行列表。
        dry_run: 若为 True 仅打印不实际写入。

    Returns:
        写入/计划写入的行数。
    """
    if not rows:
        return 0
    if dry_run:
        print(f"  [dry-run] 将写入 {len(rows)} 行到 financial_reports 表")
        return len(rows)

    conn.executemany(
        """
        INSERT INTO financial_reports
            (stock_code, report_date, report_type, statement_type,
             period_end, data_json, currency, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["stock_code"],
                r["report_date"],
                r["report_type"],
                r["statement_type"],
                r["period_end"],
                r["data_json"],
                r["currency"],
                r["created_at"],
            )
            for r in rows
        ],
    )
    return len(rows)


def process_single_stock(
    stock_code: str,
    statement_types: Tuple[str, ...],
    conn: duckdb.DuckDBPyConnection,
    dry_run: bool = False,
) -> int:
    """处理单个股票的全部报表类型。

    Returns:
        写入行数。
    """
    total = 0
    for stmt in statement_types:
        print(f"  {stock_code} - {stmt} ... ", end="", flush=True)
        df = fetch_sina_financial_report(stock_code, stmt)
        if df.empty:
            print("无数据")
            continue

        rows = parse_sina_rows(stock_code, stmt, df)
        if not rows:
            print("无可插入行")
            continue

        # 去重：跳过已存在的报告日期
        report_dates = [r["report_date"] for r in rows]
        existing = deduplicate_stock_reports(conn, stock_code, stmt, report_dates)
        new_rows = [r for r in rows if r["report_date"] not in existing]
        skipped = len(rows) - len(new_rows)

        if not new_rows:
            print(f"已存在 {len(rows)} 行（全部跳过）")
            total += 0
            continue

        written = write_reports(conn, new_rows, dry_run=dry_run)
        total += written
        status = f"写入 {written} 行"
        if skipped:
            status += f"（跳过 {skipped} 行重复）"
        print(status)

    return total


def run_single(
    symbol: str,
    statement_types: Tuple[str, ...],
    db_path: str,
    dry_run: bool = False,
) -> int:
    """处理单个股票代码。"""
    print(f"\n处理股票: {symbol}")
    print(f"数据库: {db_path}")
    print(f"报表类型: {', '.join(statement_types)}")
    if dry_run:
        print("[dry-run] 模式：不会实际写入数据库")

    # 使用 duckdb_write_lock
    from duckdb_write_lock import duckdb_write_lock

    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            ensure_table(conn)
            total = process_single_stock(symbol, statement_types, conn, dry_run=dry_run)
            if not dry_run:
                conn.commit()
            print(f"\n完成: 股票 {symbol}, 共写入 {total} 行")
            return total
        finally:
            conn.close()


def run_batch(
    statement_types: Tuple[str, ...],
    db_path: str,
    limit: int = 0,
    dry_run: bool = False,
) -> int:
    """批量处理 stocks 表中所有 A 股。"""
    from duckdb_write_lock import duckdb_write_lock

    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            ensure_table(conn)
            stocks = get_stocks_from_db(conn)
            if not stocks:
                print("[错误] stocks 表中未找到任何 A 股代码", file=sys.stderr)
                return 0

            if limit > 0:
                stocks = stocks[:limit]

            print(f"\n批量模式: 共 {len(stocks)} 只股票")
            print(f"数据库: {resolved_path}")
            print(f"报表类型: {', '.join(statement_types)}")
            if dry_run:
                print("[dry-run] 模式：不会实际写入数据库")
            print()

            try:
                from tqdm import tqdm
            except ImportError:
                tqdm = lambda x, **kw: x  # type: ignore[assignment]

            grand_total = 0
            BATCH_CHUNK_SIZE = 50
            for i, stock_code in enumerate(tqdm(stocks, desc="采集进度", unit="股")):
                total = process_single_stock(
                    stock_code, statement_types, conn, dry_run=dry_run
                )
                grand_total += total
                if not dry_run and (i + 1) % BATCH_CHUNK_SIZE == 0:
                    conn.commit()
                    print(f"  [checkpoint] 已处理 {i+1}/{len(stocks)} 只股票，累计 {grand_total} 行")

            if not dry_run:
                conn.commit()
            print(f"\n批量完成: 处理 {len(stocks)} 只股票, 共写入 {grand_total} 行")
            return grand_total
        finally:
            conn.close()


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="financial-report",
        description="A股财务报告采集器 - 下载利润表/资产负债表/现金流量表并写入 DuckDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m financial_report --symbol 600519\n"
            "  python -m financial_report --symbols 600519,000858,000333\n"
            "  python -m financial_report --batch --limit 10\n"
            "  python -m financial_report --batch --statement-type 利润表\n"
            "  python -m financial_report --batch --dry-run\n"
            "  python -m financial_report --symbol 600519 --statement-type 资产负债表\n"
        ),
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--symbol",
        type=str,
        default=None,
        metavar="CODE",
        help="单只股票代码，如 600519",
    )
    group.add_argument(
        "--symbols",
        type=str,
        default=None,
        metavar="CODES",
        help="逗号分隔的股票代码列表，如 '600519,000858'",
    )
    group.add_argument(
        "--batch",
        action="store_true",
        default=False,
        help="批量模式：扫描 quant.duckdb stocks 表中全部 A 股",
    )

    parser.add_argument(
        "--statement-type",
        type=str,
        default=None,
        metavar="TYPE",
        help=(
            "报表类型，可选: 资产负债表 / 利润表 / 现金流量表；"
            "不指定则下载全部三种"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="预览模式：仅打印将要执行的操作，不写入数据库",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="批量模式时限制处理的股票数量（默认 0=全部）",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        metavar="PATH",
        help="DuckDB 文件路径（默认从环境变量或 .env 自动获取）",
    )

    return parser


def parse_statement_types(raw: Optional[str]) -> Tuple[str, ...]:
    """解析 --statement-type 参数。

    Args:
        raw: 用户输入的报表类型字符串，如 '利润表' 或 None。

    Returns:
        报表类型元组。
    """
    if raw is None:
        return STATEMENT_TYPES
    raw_stripped = raw.strip()
    if raw_stripped in STATEMENT_TYPES:
        return (raw_stripped,)
    print(
        f"[警告] 不支持的报表类型 '{raw}'，可选: {', '.join(STATEMENT_TYPES)}；"
        f"将使用全部三种类型",
        file=sys.stderr,
        flush=True,
    )
    return STATEMENT_TYPES


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    statement_types = parse_statement_types(args.statement_type)
    db_path = args.db_path or _db_path()
    dry_run = args.dry_run

    if args.batch:
        run_batch(
            statement_types=statement_types,
            db_path=db_path,
            limit=args.limit,
            dry_run=dry_run,
        )
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        total = 0
        for sym in symbols:
            total += run_single(sym, statement_types, db_path, dry_run=dry_run)
        print(f"\n全部完成: 共写入 {total} 行")
    elif args.symbol:
        run_single(args.symbol, statement_types, db_path, dry_run=dry_run)
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
