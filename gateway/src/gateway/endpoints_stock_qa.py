"""
股票问答：粘贴文本 → 识别标的（规则 + 可选 LLM NER）→ DuckDB 多维摘要 → 规则 + LSTM 走势适配。

支持同步/异步任务、用户纠偏代码列表、Markdown 导出。
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from core.ashare_symbol import normalize_ashare_symbol

from .response_utils import json_fail, json_ok

_log = logging.getLogger(__name__)

_MAX_TEXT_LEN = 32_000
_MAX_SYMBOLS = 12
_MIN_NAME_LEN = 3

_REPO_ROOT = Path(__file__).resolve().parents[3]

_jobs_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def _code6_from_db_code(raw: str) -> str:
    s = str(raw or "").strip().upper().split(".", 1)[0]
    digits = "".join(c for c in s if c.isdigit())
    return digits[:8] if len(digits) >= 6 else digits


def extract_six_digit_codes(text: str) -> List[str]:
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


def _name_to_code_map(name_pairs: List[Tuple[str, str]]) -> Dict[str, str]:
    return {n: c for n, c in name_pairs}


def _resolve_mention_to_code(mention: str, name_pairs: List[Tuple[str, str]], valid_codes: set) -> Optional[str]:
    """将 LLM 或用户给出的简称解析为 6/8 位代码。"""
    m = (mention or "").strip()
    if not m:
        return None
    if re.fullmatch(r"\d{6}", m) and m in valid_codes:
        return m
    if re.fullmatch(r"\d{8}", m) and m in valid_codes:
        return m
    nm = _name_to_code_map(name_pairs)
    if m in nm:
        c = nm[m]
        return c if c in valid_codes else None
    for n, c in name_pairs:
        if m in n or n in m:
            if c in valid_codes:
                return c
    return None


def _parse_llm_json_array(raw: str) -> List[Dict[str, Any]]:
    """从模型输出中解析 JSON 数组。"""
    s = raw.strip()
    if "```" in s:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
        if m:
            s = m.group(1).strip()
    try:
        data = json.loads(s)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    m2 = re.search(r"\[[\s\S]*\]", s)
    if m2:
        try:
            data = json.loads(m2.group(0))
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            pass
    return []


def _llm_extract_stock_entities(text: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    调用 DashScope/OpenAI 从文本抽取 A 股相关公司/代码。
    返回 (entities, error)；entities 项含 mention、code(可选)、source=llm_ner。
    """
    import os as _os

    snippet = text.strip()[:14_000]
    sys_prompt = (
        "你是 A 股证券信息抽取助手。从用户文本中识别提到的中国上市公司（沪深北），"
        "输出**仅** JSON 数组，不要其它说明。每项格式："
        '{"mention":"文本中出现的称呼或公司名","code":"6位数字代码或空字符串"}。'
        "code 仅在你能确定时使用；不确定则空字符串。最多 24 条，按出现顺序。"
    )
    user_prompt = "文本：\n" + snippet

    key = _os.environ.get("DASHSCOPE_API_KEY") or _os.environ.get("BAILIAN_API_KEY")
    model_ds = _os.environ.get("STOCK_QA_LLM_MODEL", _os.environ.get("RESEARCH_LLM_MODEL", "qwen-turbo"))
    if key:
        try:
            import requests

            r = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=60,
                json={
                    "model": model_ds,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 2000,
                },
            )
            data = r.json()
            if r.status_code != 200:
                err = data.get("message") or str(data)[:200]
                return [], f"dashscope_http_{r.status_code}: {err}"
            choices = data.get("choices") or []
            if not choices:
                return [], "dashscope_empty_choices"
            content = (choices[0].get("message") or {}).get("content") or ""
            arr = _parse_llm_json_array(content)
            out: List[Dict[str, Any]] = []
            for item in arr:
                mention = str(item.get("mention") or item.get("name") or "").strip()
                code = str(item.get("code") or "").strip()
                if not mention and not code:
                    continue
                if not mention:
                    mention = code
                out.append(
                    {
                        "mention": mention[:80],
                        "code_hint": code[:8] if code else "",
                        "source": "llm_ner",
                    }
                )
            return out, None
        except Exception as e:
            return [], f"dashscope:{e!s}"[:300]

    key_oai = _os.environ.get("OPENAI_API_KEY")
    model_oai = _os.environ.get("STOCK_QA_OPENAI_MODEL", _os.environ.get("RESEARCH_OPENAI_MODEL", "gpt-4o-mini"))
    if key_oai:
        try:
            import requests

            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key_oai}", "Content-Type": "application/json"},
                timeout=60,
                json={
                    "model": model_oai,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 2000,
                },
            )
            data = r.json()
            if r.status_code != 200:
                return [], f"openai_{r.status_code}"
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            arr = _parse_llm_json_array(content)
            out = []
            for item in arr:
                mention = str(item.get("mention") or "").strip()
                code = str(item.get("code") or "").strip()
                if not mention and not code:
                    continue
                if not mention:
                    mention = code
                out.append({"mention": mention[:80], "code_hint": code[:8] if code else "", "source": "llm_ner"})
            return out, None
        except Exception as e:
            return [], f"openai:{e!s}"[:300]

    return [], "no_llm_key"


def _merge_llm_entities(
    llm_rows: List[Dict[str, Any]],
    name_pairs: List[Tuple[str, str]],
    valid_codes: set,
) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    seen_sym: set[str] = set()
    for row in llm_rows:
        mention = row.get("mention") or ""
        hint = str(row.get("code_hint") or "").strip()
        code6: Optional[str] = None
        if hint and hint.isdigit():
            if len(hint) >= 6:
                h6 = hint[:6]
                if h6 in valid_codes:
                    code6 = h6
                elif hint in valid_codes:
                    code6 = hint[:6] if len(hint) > 6 else hint
        if code6 is None:
            code6 = _resolve_mention_to_code(mention, name_pairs, valid_codes)
        if code6 is None and hint:
            code6 = _resolve_mention_to_code(hint, name_pairs, valid_codes)
        if code6 is None:
            continue
        sym = normalize_ashare_symbol(code6)
        if sym in seen_sym:
            continue
        seen_sym.add(sym)
        entities.append(
            {
                "mention": mention or code6,
                "symbol": sym,
                "confidence": 0.75,
                "source": "llm_ner",
            }
        )
    return entities


def _open_duckdb():
    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    if not os.path.isfile(get_db_path()):
        return None
    try:
        c = get_conn(read_only=True)
    except Exception as e:
        _log.warning("stock_qa: duckdb open failed (lock or path): %s", e)
        return None
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
            top.append({"name": str(r[0] or ""), "ratio": float(r[1]) if r[1] is not None else None})
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


def _try_lstm_predict(code6: str) -> Optional[Dict[str, Any]]:
    """调用 ai_models LSTMPricePredictor（若依赖与数据可用）。"""
    aim = _REPO_ROOT / "ai-models" / "src"
    if aim.is_dir():
        p = str(aim.resolve())
        if p not in __import__("sys").path:
            __import__("sys").path.insert(0, p)
    try:
        from ai_models.lstm_price_predictor import LSTMPricePredictor

        pred = LSTMPricePredictor()
        res = pred.predict(code6)
        if res is None:
            return None
        trend_cn = {"up": "模型偏多", "down": "模型偏空", "flat": "模型震荡"}[res.trend]
        return {
            "trend": res.trend,
            "trend_label": trend_cn,
            "current_price": res.current_price,
            "predicted_prices": res.predicted_prices[:5],
            "predicted_dates": res.predicted_dates[:5],
            "confidence": res.confidence,
            "model": "lstm_price_predictor",
        }
    except Exception as e:
        _log.debug("lstm predict skip %s: %s", code6, e)
        return None


def _rules_trend(
    quote: Dict[str, Any],
    sniper: Optional[Dict[str, Any]],
    fin: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
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
        parts.append(f"最近披露净利率约 {fin['net_margin']:.2f}%。")
    if sniper and sniper.get("sniper_score") is not None:
        parts.append(
            f"平台狙击评分约 {sniper['sniper_score']:.2f}"
            + (f"（{sniper.get('theme') or ''}）" if sniper.get("theme") else "")
            + "。"
        )
    return {"bias": bias, "summary": " ".join(parts), "model": "rules_v1"}


def _merge_trend_outlook(
    rules: Dict[str, Any],
    lstm: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """规则 + LSTM 合成。"""
    if not lstm:
        return rules
    extra = (
        f" LSTM 走势模型（{lstm.get('model', 'lstm')}）：{lstm.get('trend_label', '')}"
        f"，置信度约 {float(lstm.get('confidence') or 0):.2f}。"
    )
    return {
        "bias": rules.get("bias"),
        "summary": (rules.get("summary") or "") + extra,
        "model": "rules_v1+lstm",
        "rules": rules,
        "lstm": lstm,
    }


def _build_valid_codes(conn: Any, name_pairs: List[Tuple[str, str]]) -> set:
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
    return valid_codes


def _parse_symbols_override(raw: List[str], valid_codes: set) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for s in raw:
        t = str(s or "").strip().upper()
        if not t:
            continue
        base = t.split(".", 1)[0]
        digits = "".join(c for c in base if c.isdigit())
        if len(digits) >= 6:
            c6 = digits[:6]
            if c6 in valid_codes or any(digits.startswith(v) for v in valid_codes if len(v) > 6):
                if c6 not in seen:
                    seen.add(c6)
                    out.append(c6)
        elif len(digits) == 8:
            if digits not in seen:
                seen.add(digits)
                out.append(digits)
    return out


def _build_entities_rule(
    text: str,
    name_pairs: List[Tuple[str, str]],
    valid_codes: set,
) -> Tuple[List[Dict[str, Any]], List[str]]:
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
            {"mention": name, "symbol": sym, "confidence": 0.85, "source": "name_match"}
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
            {"mention": c6, "symbol": sym, "confidence": 0.95, "source": "code_match"}
        )
    return entities, order[:_MAX_SYMBOLS]


def run_stock_qa_analysis(
    text: str,
    max_symbols: int,
    use_llm_ner: bool,
    symbols_override: Optional[List[str]],
    include_lstm: bool,
    ner_mode: str = "hybrid",
) -> Dict[str, Any]:
    """
    ner_mode: hybrid | rules_only | llm_only
    """
    max_n = min(max_symbols, _MAX_SYMBOLS)
    conn = _open_duckdb()
    if not conn:
        return {"error": "数据库不可用", "code": 503}
    try:
        name_pairs = _load_name_pairs(conn)
        valid_codes = _build_valid_codes(conn, name_pairs)

        entities: List[Dict[str, Any]] = []
        order: List[str] = []
        llm_err: Optional[str] = None

        if symbols_override:
            order = _parse_symbols_override(symbols_override, valid_codes)[:max_n]
            for c6 in order:
                sym = normalize_ashare_symbol(c6)
                entities.append(
                    {
                        "mention": c6,
                        "symbol": sym,
                        "confidence": 1.0,
                        "source": "user_override",
                    }
                )
        else:
            if not text.strip():
                return {"error": "文本为空且未提供 symbols_override", "code": 400}

            rule_ent, rule_order = _build_entities_rule(text, name_pairs, valid_codes)

            if ner_mode == "rules_only" or not use_llm_ner:
                entities, order = rule_ent, rule_order[:max_n]
            elif ner_mode == "llm_only":
                llm_raw, llm_err = _llm_extract_stock_entities(text)
                entities = _merge_llm_entities(llm_raw, name_pairs, valid_codes)
                order = []
                seen_o: set[str] = set()
                for e in entities:
                    c = e["symbol"].split(".", 1)[0]
                    digits = "".join(x for x in c if x.isdigit())[:8]
                    if len(digits) >= 6 and digits[:6] not in seen_o:
                        seen_o.add(digits[:6])
                        order.append(digits[:6])
                order = order[:max_n]
            else:
                # hybrid: LLM + 规则去重合并
                llm_raw, llm_err = _llm_extract_stock_entities(text)
                llm_ent = _merge_llm_entities(llm_raw, name_pairs, valid_codes)
                seen_sym = {e["symbol"] for e in llm_ent}
                merged = list(llm_ent)
                for e in rule_ent:
                    if e["symbol"] not in seen_sym:
                        merged.append(e)
                        seen_sym.add(e["symbol"])
                entities = merged
                order = []
                seen_c: set[str] = set()
                for e in entities:
                    sym = e["symbol"]
                    c6 = "".join(x for x in sym.split(".", 1)[0] if x.isdigit())[:8]
                    if len(c6) >= 6:
                        k = c6[:6]
                        if k not in seen_c:
                            seen_c.add(k)
                            order.append(k)
                order = order[:max_n]

        symbols_out: List[Dict[str, Any]] = []
        for code6 in order:
            sym = normalize_ashare_symbol(code6)
            one: Dict[str, Any] = {"symbol": sym, "errors": []}
            try:
                ckey = code6[:6] if len(code6) >= 6 else code6
                basic = _fetch_basic(conn, ckey)
                one["name"] = basic.get("name") or ""
                one["sector"] = basic.get("sector") or ""
                one["quote"] = _fetch_quote(conn, ckey)
                one["financial"] = _fetch_financial_latest(conn, ckey)
                one["shareholders"] = _fetch_shareholder_summary(conn, ckey)
                one["sniper"] = _fetch_sniper(conn, ckey)
                rules = _rules_trend(one.get("quote") or {}, one.get("sniper"), one.get("financial"))
                lstm = _try_lstm_predict(ckey) if include_lstm else None
                one["trend"] = _merge_trend_outlook(rules, lstm)
            except Exception as ex:
                one["errors"].append(str(ex)[:200])
            symbols_out.append(one)

        summary_parts = [
            f"共识别 {len(entities)} 处标的提及，本次分析 {len(symbols_out)} 只。"
        ]
        if llm_err and use_llm_ner and ner_mode != "rules_only":
            summary_parts.append(f"（LLM 提示：{llm_err}，已回退或合并规则结果。）")
        if not entities:
            summary_parts.append("未匹配到有效标的；可尝试「仅分析这些代码」手动指定。")
        else:
            summary_parts.append("基于本地库与可选 LSTM 模型，不构成投资建议。")

        return {
            "entities": entities,
            "symbols": symbols_out,
            "summary": "".join(summary_parts),
            "llm_ner_error": llm_err,
            "ner_mode": ner_mode,
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def build_markdown_report(payload: Dict[str, Any]) -> str:
    """由 analyze 返回的 data 对象生成 Markdown。"""
    lines: List[str] = []
    lines.append("# 股票问答报告\n")
    lines.append(f"\n{payload.get('summary', '')}\n")
    ents = payload.get("entities") or []
    if ents:
        lines.append("\n## 识别实体\n")
        for e in ents:
            lines.append(
                f"- {e.get('mention')} → **{e.get('symbol')}** （{e.get('source')}）\n"
            )
    for blk in payload.get("symbols") or []:
        sym = blk.get("symbol", "")
        lines.append(f"\n## {blk.get('name') or sym} ({sym})\n")
        if blk.get("sector"):
            lines.append(f"- 行业/板块：{blk['sector']}\n")
        q = blk.get("quote") or {}
        if q:
            lines.append(
                f"- 行情：最新 {q.get('last_price')} ，涨跌 {q.get('change_pct')}% \n"
            )
        f = blk.get("financial")
        if f:
            lines.append(
                f"- 财务（{f.get('report_date')}）：营收 {f.get('total_revenue')} ，净利 {f.get('net_profit')}\n"
            )
        sh = blk.get("shareholders") or {}
        if sh.get("top_holders"):
            lines.append("- 前五大股东：\n")
            for h in sh["top_holders"][:5]:
                lines.append(f"  - {h.get('name')} {h.get('ratio')}%\n")
        tr = blk.get("trend") or {}
        lines.append(f"- **走势研判**：{tr.get('bias')} — {tr.get('summary')}\n")
        if tr.get("lstm"):
            lstm = tr.get("lstm")
        if isinstance(lstm, dict):
            lines.append(
                f"  - LSTM：{lstm.get('trend_label', '')} ({lstm.get('model', '')}) 置信度 {lstm.get('confidence', '')}\n"
            )
        if blk.get("errors"):
            lines.append(f"- 备注：{blk['errors']}\n")
    lines.append("\n---\n*仅供参考，不构成投资建议。*\n")
    return "".join(lines)


def _new_job_id() -> str:
    return uuid.uuid4().hex[:16]


def _job_set(job_id: str, **kwargs: Any) -> None:
    with _jobs_lock:
        cur = _jobs.get(job_id, {})
        cur.update(kwargs)
        _jobs[job_id] = cur


def _run_job_async(job_id: str, params: Dict[str, Any]) -> None:
    try:
        _job_set(job_id, status="running", progress=0.1, error=None)
        out = run_stock_qa_analysis(
            text=str(params.get("text") or ""),
            max_symbols=int(params.get("max_symbols") or 8),
            use_llm_ner=bool(params.get("use_llm_ner", True)),
            symbols_override=params.get("symbols_override"),
            include_lstm=bool(params.get("include_lstm", True)),
            ner_mode=str(params.get("ner_mode") or "hybrid"),
        )
        if out.get("error"):
            _job_set(
                job_id,
                status="failed",
                progress=1.0,
                error=out.get("error"),
                result=None,
            )
            return
        _job_set(job_id, status="completed", progress=1.0, result=out, error=None)
    except Exception as e:
        _log.exception("stock_qa job %s", job_id)
        _job_set(job_id, status="failed", error=str(e)[:500], result=None)


class StockQARequest(BaseModel):
    text: str = Field(default="", description="粘贴文本；若 symbols_override 非空可为空")
    max_symbols: int = Field(default=8, ge=1, le=_MAX_SYMBOLS)
    async_mode: bool = Field(default=False, description="为 true 时创建异步任务，返回 job_id")
    use_llm_ner: bool = Field(default=True)
    ner_mode: str = Field(
        default="hybrid",
        description="hybrid | rules_only | llm_only",
    )
    symbols_override: Optional[List[str]] = Field(default=None, description="用户纠偏：仅分析这些代码/带后缀")
    include_lstm: bool = Field(default=True, description="是否调用 LSTM 走势模型")


class StockQAReportBody(BaseModel):
    data: Dict[str, Any] = Field(..., description="与 /analyze 返回的 data 结构相同")


def build_stock_qa_router() -> APIRouter:
    r = APIRouter(prefix="/stock-qa", tags=["stock-qa"])

    @r.post("/analyze")
    def analyze(body: StockQARequest, background_tasks: BackgroundTasks) -> Any:
        raw = body.text.strip()
        if len(raw) > _MAX_TEXT_LEN:
            return json_fail(f"文本过长（上限 {_MAX_TEXT_LEN} 字）", status_code=400)
        if not raw and not (body.symbols_override and len(body.symbols_override) > 0):
            return json_fail("请提供 text 或 symbols_override", status_code=400)

        if body.async_mode:
            job_id = _new_job_id()
            _job_set(
                job_id,
                status="queued",
                progress=0.0,
                result=None,
                error=None,
                created=True,
            )
            background_tasks.add_task(
                _run_job_async,
                job_id,
                {
                    "text": raw,
                    "max_symbols": body.max_symbols,
                    "use_llm_ner": body.use_llm_ner,
                    "symbols_override": body.symbols_override,
                    "include_lstm": body.include_lstm,
                    "ner_mode": body.ner_mode,
                },
            )
            return json_ok({"job_id": job_id, "async": True}, source="stock_qa")

        out = run_stock_qa_analysis(
            text=raw,
            max_symbols=body.max_symbols,
            use_llm_ner=body.use_llm_ner,
            symbols_override=body.symbols_override,
            include_lstm=body.include_lstm,
            ner_mode=body.ner_mode,
        )
        if out.get("error"):
            return json_fail(str(out["error"]), status_code=int(out.get("code") or 503))
        return json_ok(out, source="stock_qa")

    @r.get("/jobs/{job_id}")
    def get_job(job_id: str) -> Any:
        with _jobs_lock:
            j = _jobs.get(job_id)
        if not j:
            return json_fail("任务不存在", status_code=404)
        return json_ok(
            {
                "job_id": job_id,
                "status": j.get("status"),
                "progress": j.get("progress"),
                "error": j.get("error"),
                "result": j.get("result") if j.get("status") == "completed" else None,
            },
            source="stock_qa",
        )

    @r.get("/jobs/{job_id}/report.md")
    def get_job_report(job_id: str) -> Any:
        with _jobs_lock:
            j = _jobs.get(job_id)
        if not j:
            return json_fail("任务不存在", status_code=404)
        if j.get("status") != "completed" or not j.get("result"):
            return json_fail("报告未就绪", status_code=400)
        md = build_markdown_report(j["result"])
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")

    @r.post("/report")
    def post_report(body: StockQAReportBody) -> PlainTextResponse:
        md = build_markdown_report(body.data)
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")

    return r
