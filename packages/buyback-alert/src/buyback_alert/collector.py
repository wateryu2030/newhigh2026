"""
collector.py — Buyback / acquisition data collector from akshare.

Sources:
  1. ak.stock_repurchase_em()     — stock repurchase data (东方财富-股票回购)
  2. ak.stock_dzjy_mrmx()         — block trade daily detail (大宗交易-每日明细)
  3. news_items table             — parse existing news for 回购/增持/要约收购/溢价收购 keywords

All results are written to the `buyback_events` table.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import duckdb
from tqdm import tqdm

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_EVENT_TYPES = {
    "回购": "回购",
    "增持": "增持",
    "要约收购": "要约收购",
    "溢价收购": "溢价收购",
}

_KEYWORDS = list(_EVENT_TYPES.keys())


def _ensure_buyback_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create buyback_events if not exists (defensive — ensure_tables should already do this)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS buyback_events (
            id INTEGER PRIMARY KEY,
            stock_code VARCHAR,
            event_type VARCHAR,
            announcement_date DATE,
            total_amount DOUBLE,
            price_low DOUBLE,
            price_high DOUBLE,
            planned_shares DOUBLE,
            actual_shares DOUBLE,
            status VARCHAR,
            source VARCHAR,
            source_url VARCHAR,
            summary VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _next_id(conn: duckdb.DuckDBPyConnection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM buyback_events").fetchone()
    return int(row[0]) if row else 1


# ---------------------------------------------------------------------------
# 1.  stock_repurchase_em()
# ---------------------------------------------------------------------------

def collect_repurchase(
    conn: duckdb.DuckDBPyConnection,
    *,
    dry_run: bool = False,
    symbol: Optional[str] = None,
) -> int:
    """Fetch stock_repurchase_em() and upsert into buyback_events.

    Returns count of new/updated rows.
    """
    import akshare as ak

    df = ak.stock_repurchase_em()
    if df.empty:
        print("[collector] stock_repurchase_em() returned empty DataFrame")
        return 0

    # Normalise columns
    col_map = {
        "股票代码": "stock_code",
        "股票简称": "stock_name",
        "计划回购价格区间": "price_range",
        "计划回购数量区间-下限": "planned_shares_lower",
        "计划回购数量区间-上限": "planned_shares_upper",
        "计划回购金额区间-下限": "amount_lower",
        "计划回购金额区间-上限": "amount_upper",
        "占公告前一日总股本比例-下限": "pct_lower",
        "占公告前一日总股本比例-上限": "pct_upper",
        "已回购股份数量": "actual_shares",
        "已回购金额": "actual_amount",
        "已回购股份价格区间-下限": "price_low",
        "已回购股份价格区间-上限": "price_high",
        "回购起始时间": "start_date",
        "最新公告日期": "announcement_date",
        "实施进度": "status",
    }
    # Filter by symbol
    if symbol:
        sym_code = symbol.replace(".XSHG", "").replace(".XSHE", "").replace(".BJ", "")
        df = df[df["股票代码"] == sym_code]
        if df.empty:
            print(f"[collector] No repurchase data for symbol {symbol}")
            return 0

    rows_written = 0
    next_pk = _next_id(conn)

    for _, row in tqdm(df.iterrows(), total=len(df), desc="回购数据"):
        raw = dict(row)

        code = str(raw.get("股票代码", "")).strip()
        if not code:
            continue

        summary_parts = []
        if raw.get("计划回购价格区间"):
            summary_parts.append(f"回购价≤{raw['计划回购价格区间']}")
        if raw.get("计划回购金额区间-下限") and raw.get("计划回购金额区间-上限"):
            summary_parts.append(
                f"金额区间{raw['计划回购金额区间-下限']}-{raw['计划回购金额区间-上限']}万"
            )
        if raw.get("已回购金额"):
            summary_parts.append(f"已回购{raw['已回购金额']}万")
        summary = "; ".join(summary_parts) if summary_parts else ""

        ann_date = raw.get("最新公告日期")
        if ann_date is None or (isinstance(ann_date, float) and pd.isna(ann_date)):
            ann_date = raw.get("回购起始时间")
        if isinstance(ann_date, date):
            ann_date_str = ann_date.isoformat()
        elif ann_date:
            ann_date_str = str(ann_date)[:10]
        else:
            ann_date_str = date.today().isoformat()

        # Check if already exists (by stock_code + announcement_date + event_type)
        existing = conn.execute(
            "SELECT id FROM buyback_events WHERE stock_code=? AND announcement_date=? AND event_type='回购'",
            [code, ann_date_str],
        ).fetchone()

        total_amount = (
            float(raw.get("计划回购金额区间-下限", 0) or 0)
            + float(raw.get("计划回购金额区间-上限", 0) or 0)
        ) / 2

        vals: Dict[str, Any] = {
            "stock_code": code,
            "event_type": "回购",
            "announcement_date": ann_date_str,
            "total_amount": total_amount if total_amount > 0 else None,
            "price_low": (float(raw["已回购股份价格区间-下限"]) if raw.get("已回购股份价格区间-下限") and str(raw["已回购股份价格区间-下限"]).strip() not in ("", "nan") else None),
            "price_high": (float(raw["已回购股份价格区间-上限"]) if raw.get("已回购股份价格区间-上限") and str(raw["已回购股份价格区间-上限"]).strip() not in ("", "nan") else None),
            "planned_shares": (
                float(raw.get("计划回购数量区间-上限", 0) or 0)
                if raw.get("计划回购数量区间-上限")
                else None
            ),
            "actual_shares": (float(raw["已回购股份数量"]) if raw.get("已回购股份数量") and str(raw["已回购股份数量"]).strip() not in ("", "nan") else None),
            "status": str(raw.get("实施进度", "")),
            "source": "akshare-stock_repurchase_em",
            "summary": summary,
        }

        if dry_run:
            print(f"  [DRY-RUN] 回购 {code}: {summary}")
            rows_written += 1
            continue

        if existing:
            conn.execute(
                """UPDATE buyback_events SET
                    total_amount=?, price_low=?, price_high=?, planned_shares=?,
                    actual_shares=?, status=?, summary=?, source=?
                   WHERE id=?""",
                [
                    vals["total_amount"],
                    vals["price_low"],
                    vals["price_high"],
                    vals["planned_shares"],
                    vals["actual_shares"],
                    vals["status"],
                    vals["summary"],
                    vals["source"],
                    int(existing[0]),
                ],
            )
        else:
            vals["id"] = next_pk
            next_pk += 1
            conn.execute(
                """INSERT INTO buyback_events
                   (id, stock_code, event_type, announcement_date, total_amount,
                    price_low, price_high, planned_shares, actual_shares,
                    status, source, summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    vals["id"],
                    vals["stock_code"],
                    vals["event_type"],
                    vals["announcement_date"],
                    vals["total_amount"],
                    vals["price_low"],
                    vals["price_high"],
                    vals["planned_shares"],
                    vals["actual_shares"],
                    vals["status"],
                    vals["source"],
                    vals["summary"],
                ],
            )
        rows_written += 1

    return rows_written


# ---------------------------------------------------------------------------
# 2.  stock_dzjy_mrmx() — block trades (溢价收购 signals)
# ---------------------------------------------------------------------------

def collect_block_trades(
    conn: duckdb.DuckDBPyConnection,
    *,
    dry_run: bool = False,
    symbol: Optional[str] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
) -> int:
    """Fetch block trades with premium ratio > 0 (溢价成交)."""
    import akshare as ak

    if end_date_str is None:
        end_date_str = date.today().strftime("%Y%m%d")
    if start_date_str is None:
        # default: last 30 days
        from datetime import timedelta
        start_date_str = (date.today() - timedelta(days=30)).strftime("%Y%m%d")

    df = ak.stock_dzjy_mrmx(
        symbol="A股",
        start_date=start_date_str,
        end_date=end_date_str,
    )
    if df.empty:
        print("[collector] stock_dzjy_mrmx() returned empty DataFrame")
        return 0

    # Filter premium trades and optionally by symbol
    df = df[df["折溢率"] > 0].copy()  # 溢价成交
    if symbol:
        sym_code = symbol.replace(".XSHG", "").replace(".XSHE", "").replace(".BJ", "")
        df = df[df["证券代码"] == sym_code]

    rows_written = 0
    next_pk = _next_id(conn)

    for _, row in tqdm(df.iterrows(), total=len(df), desc="大宗交易(溢价)"):
        raw = dict(row)
        code = str(raw.get("证券代码", "")).strip()
        if not code:
            continue

        trade_date = raw.get("交易日期")
        if isinstance(trade_date, date):
            ann_date_str = trade_date.isoformat()
        else:
            ann_date_str = str(trade_date)[:10]

        premium = float(raw.get("折溢率", 0) or 0)
        summary = (
            f"大宗交易溢价{premium:.2f}%; "
            f"成交价{raw.get('成交价','')}; "
            f"成交额{raw.get('成交额','')}"
        )

        existing = conn.execute(
            "SELECT id FROM buyback_events WHERE stock_code=? AND announcement_date=? AND event_type='溢价收购'",
            [code, ann_date_str],
        ).fetchone()

        if dry_run:
            print(f"  [DRY-RUN] 溢价收购 {code}: {summary}")
            rows_written += 1
            continue

        vals = {
            "stock_code": code,
            "event_type": "溢价收购",
            "announcement_date": ann_date_str,
            "total_amount": float(raw.get("成交额", 0) or 0),
            "price_low": None,
            "price_high": float(raw.get("成交价", 0) or 0),
            "planned_shares": float(raw.get("成交量", 0) or 0),
            "actual_shares": None,
            "status": "溢价成交",
            "source": "akshare-stock_dzjy_mrmx",
            "summary": summary,
        }

        if existing:
            conn.execute(
                """UPDATE buyback_events SET total_amount=?, price_high=?, planned_shares=?,
                   summary=?, source=? WHERE id=?""",
                [vals["total_amount"], vals["price_high"], vals["planned_shares"],
                 vals["summary"], vals["source"], int(existing[0])],
            )
        else:
            vals["id"] = next_pk
            next_pk += 1
            conn.execute(
                """INSERT INTO buyback_events
                   (id, stock_code, event_type, announcement_date, total_amount,
                    price_low, price_high, planned_shares, actual_shares,
                    status, source, summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    vals["id"], vals["stock_code"], vals["event_type"],
                    vals["announcement_date"], vals["total_amount"],
                    vals["price_low"], vals["price_high"], vals["planned_shares"],
                    vals["actual_shares"], vals["status"], vals["source"],
                    vals["summary"],
                ],
            )
        rows_written += 1

    return rows_written


# ---------------------------------------------------------------------------
# 3.  news_items keyword parsing
# ---------------------------------------------------------------------------

def collect_from_news(
    conn: duckdb.DuckDBPyConnection,
    *,
    dry_run: bool = False,
    symbol: Optional[str] = None,
) -> int:
    """Parse existing news_items for buyback/acquisition keywords."""
    rows_written = 0
    next_pk = _next_id(conn)

    # Build query
    like_clauses = " OR ".join(f"title LIKE '%{kw}%'" for kw in _KEYWORDS)
    query = f"SELECT ts, symbol, title, content, source, url FROM news_items WHERE {like_clauses}"
    if symbol:
        sym_code = symbol.replace(".XSHG", "").replace(".XSHE", "").replace(".BJ", "")
        query += f" AND (symbol LIKE '%{sym_code}%' OR title LIKE '%{sym_code}%')"

    try:
        rows = conn.execute(query).fetchall()
    except Exception as e:
        print(f"[collector] news query failed: {e}")
        return 0

    for r in tqdm(rows, desc="新闻关键词匹配"):
        ts, sym, title, content, source, url = r
        if not sym and not title:
            continue

        # Determine event_type from keywords in title
        event_type = None
        for kw, etype in _EVENT_TYPES.items():
            if title and kw in title:
                event_type = etype
                break
        if not event_type:
            continue

        # Extract stock code from symbol or title
        stock_code = sym if sym else ""
        # Try to extract 6-digit code from title if no symbol
        if not stock_code and title:
            import re
            codes = re.findall(r'\b(\d{6})\b', title)
            if codes:
                stock_code = codes[0]

        if not stock_code:
            continue

        ann_date = ts.date().isoformat() if ts is not None and hasattr(ts, "date") else (str(ts)[:10] if ts else None)
        if not ann_date:
            continue

        summary = title or ""
        if content:
            summary += " | " + content[:200]

        if dry_run:
            print(f"  [DRY-RUN] {event_type} {stock_code}: {title}")
            rows_written += 1
            continue

        existing = conn.execute(
            "SELECT id FROM buyback_events WHERE stock_code=? AND announcement_date=? AND event_type=? AND source_url=?",
            [stock_code, ann_date, event_type, url or ""],
        ).fetchone()

        if existing:
            continue

        vals = {
            "id": next_pk,
            "stock_code": stock_code,
            "event_type": event_type,
            "announcement_date": ann_date,
            "total_amount": None,
            "price_low": None,
            "price_high": None,
            "planned_shares": None,
            "actual_shares": None,
            "status": "公告",
            "source": source or "news_items",
            "source_url": url or "",
            "summary": summary,
        }
        next_pk += 1
        conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, total_amount,
                price_low, price_high, planned_shares, actual_shares,
                status, source, source_url, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                vals["id"], vals["stock_code"], vals["event_type"],
                vals["announcement_date"], vals["total_amount"],
                vals["price_low"], vals["price_high"], vals["planned_shares"],
                vals["actual_shares"], vals["status"], vals["source"],
                vals["source_url"], vals["summary"],
            ],
        )
        rows_written += 1

    return rows_written


# ---------------------------------------------------------------------------
# unified collector entry
# ---------------------------------------------------------------------------

def run_collect(
    conn: duckdb.DuckDBPyConnection,
    *,
    dry_run: bool = False,
    symbol: Optional[str] = None,
) -> Dict[str, int]:
    """Run all collection sources and return counts per source."""
    # Skip DDL in dry-run / read-only mode if table already exists
    if not dry_run:
        _ensure_buyback_table(conn)
    else:
        try:
            conn.execute("SELECT COUNT(*) FROM buyback_events")
        except Exception:
            _ensure_buyback_table(conn)

    counts: Dict[str, int] = {}

    print("=" * 50)
    print("收集回购数据 (akshare stock_repurchase_em)...")
    try:
        c = collect_repurchase(conn, dry_run=dry_run, symbol=symbol)
    except Exception as e:
        print(f"  ⚠ 回购API失败（网络/东方财富接口问题）: {e}")
        c = 0
    counts["repurchase"] = c
    print(f"  -> {c} 条记录" if c else "  -> 0 条记录（已跳过）")

    print("收集大宗交易溢价数据 (akshare stock_dzjy_mrmx)...")
    try:
        c = collect_block_trades(conn, dry_run=dry_run, symbol=symbol)
    except Exception as e:
        print(f"  ⚠ 大宗交易API失败: {e}")
        c = 0
    counts["block_trades"] = c
    print(f"  -> {c} 条记录" if c else "  -> 0 条记录（已跳过）")

    print("分析历史新闻关键词匹配...")
    c = collect_from_news(conn, dry_run=dry_run, symbol=symbol)
    counts["news"] = c
    print(f"  -> {c} 条记录")

    if not dry_run:
        conn.commit()
        print("[collector] 已提交事务")

    return counts


# Make pd available for the module
import pandas as pd
