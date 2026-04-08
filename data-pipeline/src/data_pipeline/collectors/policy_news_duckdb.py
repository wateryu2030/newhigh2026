"""政策新闻（国务院/新华网等）写入主库 ``news_items``，与 RSS、东财快讯共用 ``quant_system.duckdb``。"""

from __future__ import annotations

POLICY_SYMBOL = "__POLICY__"
POLICY_SOURCE_SITE = "policy"


def _sentiment_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score > 0.1:
        return "利好"
    if score < -0.1:
        return "利空"
    return "中性"


def sync_policy_news_to_duckdb(items: list[dict]) -> int:
    """
    将 policy-news 采集条目写入 ``news_items``（去重：同 symbol 下优先 url，否则 title+publish_time）。
    """
    from ..storage.duckdb_manager import ensure_tables, get_conn

    conn = get_conn(read_only=False)
    ensure_tables(conn)
    inserted = 0
    for item in items:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        source = (item.get("source") or "").strip() or "policy"
        url = (item.get("url") or "").strip()
        pub = (item.get("date") or "").strip()
        tag = (item.get("category") or "其他政策").strip()
        content = (item.get("content") or "").strip()
        domains = item.get("domains") or []
        if isinstance(domains, str):
            kw = domains[:300]
        else:
            kw = ",".join(str(x) for x in domains)[:300]
        try:
            sc = float(item.get("sentiment"))
        except (TypeError, ValueError):
            sc = 0.0
        lbl = _sentiment_label(sc)

        by_url = 0
        if url:
            by_url = conn.execute(
                "SELECT COUNT(*) FROM news_items WHERE symbol = ? AND url = ?",
                [POLICY_SYMBOL, url],
            ).fetchone()[0]
        by_title = conn.execute(
            "SELECT COUNT(*) FROM news_items WHERE symbol = ? "
            "AND TRIM(COALESCE(title,'')) = ? AND TRIM(COALESCE(publish_time,'')) = ?",
            [POLICY_SYMBOL, title, pub],
        ).fetchone()[0]
        if by_url > 0 or by_title > 0:
            continue
        try:
            conn.execute(
                """
                INSERT INTO news_items
                (symbol, source_site, source, title, content, url, keyword, tag, publish_time,
                 sentiment_score, sentiment_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    POLICY_SYMBOL,
                    POLICY_SOURCE_SITE,
                    source,
                    title,
                    content or None,
                    url or None,
                    kw or None,
                    tag,
                    pub or None,
                    sc,
                    lbl,
                ],
            )
            inserted += 1
        except Exception:
            continue
    return inserted
