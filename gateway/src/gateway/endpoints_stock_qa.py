"""
股票问答 MVP：粘贴文本 → 识别 A 股名称/代码 → 拉取 DuckDB 行情与财报/股东摘要 → 规则化走势研判。

同步接口，单请求内完成；单只股票失败不拖垮整批。
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.ashare_symbol import normalize_ashare_symbol

from .response_utils import json_fail, json_ok

_log = logging.getLogger(__name__)

# MVP 限制：避免单次请求过重
_MAX_TEXT_LEN = 32_000
_MAX_SYMBOLS = 12
_MIN_NAME_LEN = 3


def _code6_from_db_code(raw: str) -> str:
    s = str(raw or "").strip().upper().split(".", 1)[0]
    digits = "".join(c for c in s if c.isdigit())
    return digits[:8] if len(digits) >= 6 else digits


def extract_six_digit_codes(text: str) -> List[str]:
    """从文本中提取 6 位连续数字，视为 A 股/北交所代码候选。"""
    if not text:
        return []
    found = re.findall(r"(?<!\d)(\d{6})(?!\d)", text)
    out: List[str] = []
    seen: set[str] = set()
    for c in found:
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def extract_name_matches(
    text: str,
    names_sorted: List[Tuple[str, str]],
    used: Optional[List[bool]] = None,
) -> List[Tuple[str, str]]:
    """
    按名称从长到短在文本中匹配，避免短词抢占长词；重叠区间不重复匹配。
    names_sorted: [(name, code6), ...] 已按 len(name) 降序。
    """
    if not text.strip():
        return []
    if used is None:
        used = [False] * len(text)
    matches: List[Tuple[str, str]] = []
    for name, code in names_sorted:
        if len(name) < _MIN_NAME_LEN:
            continue
        start = 0
        while True:
            idx = text.find(name, start)
            if idx < 0:
                break
            end = idx + len(name)
            if any(used[idx:end]):
                start = idx + 1
                continue
            for i in range(idx, end):
                used[i] = True
            matches.append((name, code))
            start = end
    return matches


def _load_name_pairs(conn: Any) -> List[Tuple[str, str]]:
    """返回 [(name, code6), ...]，按名称长度降序（同长度任意顺序）。"""
    try:
        rows = conn.execute(
            """
            SELECT CAST(name AS VARCHAR), CAST(code AS VARCHAR)
            FROM a_stock_basic
            WHERE name IS NOT NULL AND TRIM(CAST(name AS VARCHAR)) != ''
            """
        ).fetchall()
    except Exception as e:
        _log.warning("stock_qa: a_stock_basic load failed: %s", e)
        return []
    pairs: List[Tuple[str, str]] = []
    for row in rows or []:
        n, c = str(row[0] or "").strip(), _code6_from_db_code(str(row[1] or ""))
        if len(n) < _MIN_NAME_LEN or len(c) < 6:
            continue
        pairs.append((n, c))
    pairs.sort(key=lambda x: -len(x[0]))
    return pairs


def _open_duckdb():
    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    if not os.path.isfile(get_db_path()):
        return None
    c = get_conn(read_only=True)
    try:
        ensure_tables(c)
    except Exception:
        pass
    return c


def _fetch_basic(conn: Any, code6: str) -> Dict[str, Any]:
    row = conn.execute(
        """
        SELECT CAST(code AS VARCHAR), CAST(name AS VARCHAR), CAST(sector AS VARCHAR)
        FROM a_stock_basic
        WHERE split_part(upper(trim(CAST(code AS VARCHAR))), '.', 1) = ?
        LIMIT 1
        """,
        [code6],
    ).fetchone()
    if not row:
        return {"code": code6, "name": "", "sector": ""}
    return {"code": _code6_from_db_code(row[0]), "name": str(row[1] or ""), "sector": str(row[2] or "")}


def _fetch_quote(conn: Any, code6: str) -> Dict[str, Any]:
    sym = normalize_ashare_symbol(code6)
    ex = sym
    if sym.endswith(".BSE"):
        ex = f"{code6}.BJ"
    row = conn.execute(
        """
        SELECT code, name, latest_price, change_pct, volume, amount, snapshot_time
        FROM a_stock_realtime
        WHERE split_part(upper(trim(CAST(code AS VARCHAR))), '.', 1) = ?
           OR code = ? OR code = ?
        ORDER BY snapshot_time DESC NULLS LAST
        LIMIT 1
        """,
        [code6, code6, ex],
    ).fetchone()
    if row:
        price = float(row[2] or 0)
        chg = float(row[3]) if row[3] is not None else 0.0
        return {
            "last_price": price,
            "change_pct": chg,
            "volume": int(row[4] or 0),
            "amount": float(row[5] or 0),
            "snapshot_time": str(row[6]) if row[6] else None,
        }
    drow = conn.execute(
        """
        SELECT code, close, volume, amount, date
        FROM a_stock_daily
        WHERE split_part(upper(trim(CAST(code AS VARCHAR))), '.', 1) = ?
           OR code = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        [code6, ex],
    ).fetchone()
    if drow:
        price = float(drow[1] or 0)
        return {
            "last_price": price,
            "change_pct": 0.0,
            "volume": int(drow[2] or 0),
            "amount": float(drow[3] or 0),
            "snapshot_time": str(drow[4]) if drow[4] else None,
        }
    return {}


def _fetch_financial_latest(conn: Any, code6: str) -> Optional[Dict[str, Any]]:
    try:
        row = conn.execute(
            """
            SELECT report_date, total_revenue, net_profit, gross_margin, net_margin,
                   operating_cash_flow
            FROM financial_report
            WHERE stock_code = ?
            ORDER BY report_date DESC NULLS LAST
            LIMIT 1
            """,
            [code6],
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "report_date": str(row[0]) if row[0] else None,
        "total_revenue": float(row[1]) if row[1] is not None else None,
        "net_profit": float(row[2]) if row[2] is not None else None,
        "gross_margin": float(row[3]) if row[3] is not None else None,
        "net_margin": float(row[4]) if row[4] is not None else None,
        "operating_cash_flow": float(row[5]) if row[5] is not None else None,
    }


def _fetch_shareholder_summary(conn: Any, code6: str) -> Dict[str, Any]:
    try:
        rd = conn.execute(
            "SELECT MAX(report_date) FROM top_10_shareholders WHERE stock_code = ?",
            [code6],
        ).fetchone()
        report_date = rd[0] if rd else None
        if report_date is None:
            return {"report_date": None, "top_holders": []}
        df = conn.execute(
            """
            SELECT shareholder_name, share_ratio
            FROM top_10_shareholders
            WHERE stock_code = ? AND report_date = ?
            ORDER BY rank NULLS LAST
            LIMIT 5
            """,
            [code6, report_date],
        ).fetchall()
        top = []
        for r in df or []:
            top.append(
                {
                    "name": str(r[0] or ""),
                    "ratio": float(r[1]) if r[1] is not None else None,
                }
            )
        return {"report_date": str(report_date), "top_holders": top}
    except Exception:
        return {"report_date": None, "top_holders": []}


def _fetch_sniper(conn: Any, code6: str) -> Optional[Dict[str, Any]]:
    try:
        row = conn.execute(
            """
            SELECT sniper_score, confidence, theme
            FROM sniper_candidates
            WHERE split_part(upper(trim(CAST(code AS VARCHAR))), '.', 1) = ?
            ORDER BY snapshot_time DESC NULLS LAST
            LIMIT 1
            """,
            [code6],
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "sniper_score": float(row[0]) if row[0] is not None else None,
        "confidence": float(row[1]) if row[1] is not None else None,
        "theme": str(row[2] or ""),
    }


def _trend_outlook(
    quote: Dict[str, Any],
    sniper: Optional[Dict[str, Any]],
    fin: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """MVP：规则化研判（非 ML）；后续可换为模型适配器输出。"""
    chg = float(quote.get("change_pct") or 0)
    parts: List[str] = []
    bias = "中性"
    if chg >= 5:
        bias = "短线偏强"
        parts.append(f"当日涨幅约 {chg:.2f}%，短线动能偏强，注意追高风险。")
    elif chg >= 2:
        bias = "温和偏强"
        parts.append(f"当日涨幅约 {chg:.2f}%，交投相对活跃。")
    elif chg <= -5:
        bias = "短线偏弱"
        parts.append(f"当日跌幅约 {abs(chg):.2f}%，注意波动与止损纪律。")
    elif chg <= -2:
        bias = "温和偏弱"
        parts.append(f"当日调整约 {abs(chg):.2f}%，宜结合基本面与仓位管理。")
    else:
        parts.append("当日波动不大，可更多参考基本面与资金结构。")

    if fin and fin.get("net_margin") is not None:
        nm = fin["net_margin"]
        parts.append(f"最近披露净利率约 {nm:.2f}%。")
    if sniper and sniper.get("sniper_score") is not None:
        parts.append(
            f"平台狙击评分约 {sniper['sniper_score']:.2f}"
            + (f"（{sniper.get('theme') or '主题'}）" if sniper.get("theme") else "")
            + "，仅供参考。"
        )

    return {
        "bias": bias,
        "summary": " ".join(parts),
        "model": "rules_v1",
    }


def _build_entities(
    text: str,
    name_pairs: List[Tuple[str, str]],
    valid_codes: set,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """返回 entities 列表与有序 symbol6 列表（去重保序）。"""
    used = [False] * len(text)
    from_names = extract_name_matches(text, name_pairs, used)
    entities: List[Dict[str, Any]] = []
    order: List[str] = []
    seen: set[str] = set()

    for name, code6 in from_names:
        if code6 not in valid_codes:
            continue
        sym = normalize_ashare_symbol(code6)
        if sym in seen:
            continue
        seen.add(sym)
        order.append(code6)
        entities.append(
            {
                "mention": name,
                "symbol": sym,
                "confidence": 0.85,
                "source": "name_match",
            }
        )

    for c6 in extract_six_digit_codes(text):
        if c6 not in valid_codes:
            continue
        sym = normalize_ashare_symbol(c6)
        if sym in seen:
            continue
        seen.add(sym)
        order.append(c6)
        entities.append(
            {
                "mention": c6,
                "symbol": sym,
                "confidence": 0.95,
                "source": "code_match",
            }
        )

    return entities, order[:_MAX_SYMBOLS]


class StockQARequest(BaseModel):
    text: str = Field(..., min_length=1, description="用户粘贴的文本")
    max_symbols: int = Field(default=8, ge=1, le=_MAX_SYMBOLS, description="最多分析标的数")


def build_stock_qa_router() -> APIRouter:
    r = APIRouter(prefix="/stock-qa", tags=["stock-qa"])

    @r.post("/analyze")
    def analyze(body: StockQARequest) -> Any:
        text = body.text.strip()
        if len(text) > _MAX_TEXT_LEN:
            return json_fail(f"文本过长（上限 {_MAX_TEXT_LEN} 字）", status_code=400)
        max_n = min(body.max_symbols, _MAX_SYMBOLS)

        conn = _open_duckdb()
        if not conn:
            return json_fail("数据库不可用", status_code=503)
        try:
            name_pairs = _load_name_pairs(conn)
            valid_codes: set[str] = set()
            for _, c6 in name_pairs:
                if len(c6) >= 6:
                    valid_codes.add(c6)
            try:
                rows = conn.execute(
                    "SELECT DISTINCT split_part(upper(trim(CAST(code AS VARCHAR))), '.', 1) FROM a_stock_basic"
                ).fetchall()
                for row in rows or []:
                    d = "".join(x for x in str(row[0] or "") if x.isdigit())[:8]
                    if len(d) >= 6:
                        valid_codes.add(d[:6])
                        if len(d) == 8:
                            valid_codes.add(d)
            except Exception:
                pass

            entities, order = _build_entities(text, name_pairs, valid_codes)
            order = order[:max_n]

            symbols_out: List[Dict[str, Any]] = []
            for code6 in order:
                sym = normalize_ashare_symbol(code6)
                one: Dict[str, Any] = {
                    "symbol": sym,
                    "errors": [],
                }
                try:
                    basic = _fetch_basic(conn, code6[:6])
                    one["name"] = basic.get("name") or ""
                    one["sector"] = basic.get("sector") or ""
                    one["quote"] = _fetch_quote(conn, code6[:6])
                    one["financial"] = _fetch_financial_latest(conn, code6[:6])
                    one["shareholders"] = _fetch_shareholder_summary(conn, code6[:6])
                    one["sniper"] = _fetch_sniper(conn, code6[:6])
                    one["trend"] = _trend_outlook(
                        one.get("quote") or {},
                        one.get("sniper"),
                        one.get("financial"),
                    )
                except Exception as ex:
                    one["errors"].append(str(ex)[:200])
                symbols_out.append(one)

            summary_parts = [
                f"共识别 {len(entities)} 处标的提及，本次深度分析 {len(symbols_out)} 只。"
            ]
            if not entities:
                summary_parts.append("未从文本中匹配到已知 A 股名称或 6 位代码，可尝试含公司全称或股票代码。")
            else:
                summary_parts.append("以下为基于本地库行情、财报与股东数据的规则化摘要，不构成投资建议。")

            return json_ok(
                {
                    "entities": entities,
                    "symbols": symbols_out,
                    "summary": "".join(summary_parts),
                },
                source="stock_qa",
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return r
