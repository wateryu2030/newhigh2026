"""东方财富个股新闻（akshare stock_news_em）：写入 news_items，含可点击原文 url。"""

from __future__ import annotations


def _normalize_news_article_url(raw: object) -> str:
    u = (raw or "").strip() if isinstance(raw, str) else str(raw or "").strip()
    if not u or u.lower() in ("nan", "none"):
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://finance.eastmoney.com" + u
    return u


def update_em_stock_news(
    codes_limit: int = 50,
    per_code_limit: int = 15,
    extra_codes_first: list[str] | None = None,
) -> int:
    """
    从 a_stock_basic 取前 codes_limit 只股票，逐只拉东财新闻并写入 news_items。
    extra_codes_first：优先采集的股票代码（含 .SZ 亦可），去重后排在最前，再按 basic 补齐至 codes_limit。
    与 Gateway akshare 兜底列名逻辑对齐；按 url / (title, publish_time) 去重插入。
    """
    try:
        import akshare as ak  # type: ignore
    except ImportError:
        print("错误：未安装 akshare，请 pip install akshare")
        return 0

    try:
        from ..storage.duckdb_manager import ensure_tables, get_conn
    except ImportError:
        print("错误：无法导入 duckdb_manager")
        return 0

    conn = get_conn()
    ensure_tables(conn)

    lim = max(1, int(codes_limit))
    seen: set[str] = set()
    ordered: list[str] = []

    if extra_codes_first:
        for raw in extra_codes_first:
            code6 = str(raw).split(".", maxsplit=1)[0].strip()
            if len(code6) < 5 or code6 in seen:
                continue
            seen.add(code6)
            ordered.append(code6)
            if len(ordered) >= lim:
                ordered = ordered[:lim]
                break

    if len(ordered) < lim:
        try:
            codes_df = conn.execute(
                "SELECT code FROM a_stock_basic ORDER BY code LIMIT ?",
                [max(lim * 4, 800)],
            ).fetchdf()
        except Exception as e:
            print(f"读取股票池失败: {e}")
            conn.close()
            return 0

        if (codes_df is None or codes_df.empty) and not ordered:
            print("a_stock_basic 为空且无优先代码，跳过东财新闻采集")
            conn.close()
            return 0

        if codes_df is not None and not codes_df.empty:
            for raw_code in codes_df["code"].astype(str).tolist():
                if len(ordered) >= lim:
                    break
                code6 = raw_code.split(".", maxsplit=1)[0].strip()
                if len(code6) < 5 or code6 in seen:
                    continue
                seen.add(code6)
                ordered.append(code6)

    if not ordered:
        print("无可用股票代码，跳过东财新闻采集")
        conn.close()
        return 0

    inserted = 0
    for code6 in ordered:
        try:
            df = ak.stock_news_em(symbol=code6)
        except Exception as e:
            print(f"  {code6} 拉取失败: {e}")
            continue
        if df is None or df.empty:
            continue

        cols = [str(c) for c in df.columns.tolist()]
        title_col = next((c for c in ["新闻标题", "title"] if c in cols), cols[0] if cols else None)
        content_col = next((c for c in ["新闻内容", "content"] if c in cols), None)
        time_col = next((c for c in ["发布时间", "publish_time"] if c in cols), None)
        url_col = next((c for c in ["新闻链接", "链接", "url", "link"] if c in cols), None)
        source_col = next((c for c in ["文章来源", "source"] if c in cols), None)

        for _, row in df.head(max(1, int(per_code_limit))).iterrows():
            title = str(row.get(title_col, "")).strip() if title_col else ""
            if not title:
                continue
            content = (str(row.get(content_col, ""))[:2000]) if content_col else ""
            pub = str(row.get(time_col, "")).strip() if time_col else ""
            url = _normalize_news_article_url(str(row.get(url_col, "")) if url_col else "")
            src = str(row.get(source_col, "东方财富")).strip() if source_col else "东方财富"

            by_url = 0
            if url:
                by_url = conn.execute(
                    "SELECT COUNT(*) FROM news_items WHERE url = ?", [url]
                ).fetchone()[0]
            by_title_time = conn.execute(
                "SELECT COUNT(*) FROM news_items WHERE TRIM(COALESCE(title,'')) = ? AND TRIM(COALESCE(publish_time,'')) = ?",
                [title, pub],
            ).fetchone()[0]

            if by_url > 0 or by_title_time > 0:
                continue
            try:
                conn.execute(
                    """
                    INSERT INTO news_items
                    (symbol, source_site, source, title, content, url, keyword, tag, publish_time, sentiment_score, sentiment_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        code6,
                        "eastmoney",
                        src,
                        title[:500],
                        content,
                        url or None,
                        "",
                        "个股新闻",
                        pub,
                        None,
                        None,
                    ],
                )
                inserted += 1
            except Exception as e:
                print(f"  写入跳过 {title[:40]}…: {e}")

    conn.close()
    print(f"东财个股新闻: 新写入 {inserted} 条")
    return inserted
