"""
国际 / 宏观突发快讯：RSS → news_items（与东财个股新闻互补）。

覆盖美欧地缘、大宗、联储等 A 股外盘敏感信息；默认数据源为 BBC RSS（稳定、无需 key）。
推送：NEWS_BREAKING_WEBHOOK_URL 配置飞书自定义机器人 Webhook，标题命中 NEWS_BREAKING_ALERT_KEYWORDS 时 POST（msg_type=text）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError

GLOBAL_SYMBOL = "__GLOBAL__"

_DEFAULT_FEEDS = (
    "http://feeds.bbci.co.uk/news/world/rss.xml,"
    "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml,"
    "http://feeds.bbci.co.uk/news/business/rss.xml,"
    "http://feeds.bbci.co.uk/news/politics/rss.xml,"
    "http://feeds.bbci.co.uk/news/world/middle_east/rss.xml"
)


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[-1]
    return tag


def _feed_label_from_url(url: str) -> str:
    u = url.lower()
    if "bbc.co.uk" in u:
        return "rss.bbc"
    if "reuters.com" in u:
        return "rss.reuters"
    if "theguardian.com" in u:
        return "rss.guardian"
    if "xinhuanet" in u or "news.cn" in u:
        return "rss.cn"
    return "rss"


def _fetch_rss(url: str, timeout: float = 18.0) -> bytes | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "newhigh-news-bot/1.0 (+rss macro)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, OSError, TimeoutError) as e:
        print(f"RSS 拉取失败 {url[:64]}…: {e}")
        return None


def _parse_rss_feed(xml: bytes, max_items: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"RSS 解析失败: {e}")
        return out

    # Atom
    if _strip_ns(root.tag).lower() == "feed":
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for ent in root.findall("atom:entry", ns)[:max_items]:
            title_el = ent.find("atom:title", ns)
            link_el = ent.find("atom:link", ns)
            updated_el = ent.find("atom:updated", ns) or ent.find("atom:published", ns)
            title = (title_el.text or "").strip() if title_el is not None else ""
            href = (link_el.get("href") or "").strip() if link_el is not None else ""
            pub = (updated_el.text or "").strip() if updated_el is not None else ""
            if title:
                out.append({"title": title[:500], "url": href, "publish_time": pub[:80]})
        return out

    channel = root.find("channel") if _strip_ns(root.tag).lower() == "rss" else root
    if channel is None:
        return out
    for child in channel:
        if _strip_ns(child.tag).lower() != "item":
            continue
        title_el = child.find("title")
        link_el = child.find("link")
        pub_el = child.find("pubDate") or child.find("published")
        title = (title_el.text or "").strip() if title_el is not None else ""
        link_txt = ""
        if link_el is not None:
            link_txt = (link_el.text or link_el.get("href") or "").strip()
        pub = (pub_el.text or "").strip() if pub_el is not None else ""
        if title:
            out.append({"title": title[:500], "url": link_txt, "publish_time": pub[:80]})
        if len(out) >= max_items:
            break
    return out


def _load_sent_hashes(path: Path, max_lines: int = 1500) -> set[str]:
    if not path.is_file():
        return set()
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return set(lines[-max_lines:])


def _append_sent_hash(path: Path, h: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(h + "\n")


def _title_matches_breaking(title: str, patterns: list[re.Pattern[str]]) -> bool:
    if not patterns:
        return False
    t = title.lower()
    for p in patterns:
        try:
            if p.search(title) or p.search(t):
                return True
        except re.error:
            continue
    return False


def _build_breaking_patterns() -> list[re.Pattern[str]]:
    raw = (os.environ.get("NEWS_BREAKING_ALERT_KEYWORDS") or "").strip()
    if not raw:
        raw = (
            "特朗普|川普|Trump|拜登|Biden|伊朗|Iran|Israel|以色列|中东|战争|美伊|军事打击|空袭|"
            "Houthi|哈梅内伊|五角大楼|Pentagon|霍尔木兹|核|制裁|"
            "原油|欧佩克|OPEC|联储|Fed|鲍威尔|降息|加息|美债|美元|黄金"
        )
    patterns: list[re.Pattern[str]] = []
    for part in re.split(r"[,\n;|]", raw):
        p = part.strip()
        if len(p) < 2:
            continue
        if any(x in p for x in ("*", "^", "$", "[", "(", "?", "+")):
            try:
                patterns.append(re.compile(p, re.I))
            except re.error:
                patterns.append(re.compile(re.escape(p), re.I))
        else:
            patterns.append(re.compile(re.escape(p), re.I))
    return patterns


def _send_feishu_text(webhook_url: str, text: str) -> bool:
    payload = json.dumps({"msg_type": "text", "content": {"text": text[:4000]}}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return 200 <= resp.status < 300
    except (URLError, OSError) as e:
        print(f"Webhook 发送失败: {e}")
        return False


def update_rss_macro_news(
    feeds_csv: str | None = None,
    max_per_feed: int | None = None,
    send_breaking_alerts: bool | None = None,
) -> int:
    """
    拉取 RSS → news_items（symbol=__GLOBAL__，tag=国际宏观）。
    返回新插入条数。
    """
    feeds = (feeds_csv or os.environ.get("NEWS_RSS_FEEDS") or _DEFAULT_FEEDS).strip()
    lim = max_per_feed if max_per_feed is not None else int(os.environ.get("NEWS_RSS_MAX_PER_FEED", "35"))
    webhook = (os.environ.get("NEWS_BREAKING_WEBHOOK_URL") or "").strip()
    if send_breaking_alerts is not None:
        do_push = send_breaking_alerts and bool(webhook)
    else:
        do_push = bool(webhook)

    env_state = (os.environ.get("NEWS_BREAKING_STATE_PATH") or "").strip()
    hash_file = (
        Path(env_state).expanduser()
        if env_state
        else Path(__file__).resolve().parents[4] / "logs" / "breaking_news_hashes.txt"
    )
    sent_hashes = _load_sent_hashes(hash_file) if do_push else set()
    patterns = _build_breaking_patterns() if do_push else []

    from ..storage.duckdb_manager import ensure_tables, get_conn

    conn = get_conn()
    ensure_tables(conn)
    inserted = 0
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for feed_url in [x.strip() for x in feeds.split(",") if x.strip()]:
        raw = _fetch_rss(feed_url)
        if not raw:
            continue
        items = _parse_rss_feed(raw, lim)
        site = _feed_label_from_url(feed_url)
        for it in items:
            title = it["title"]
            url = it.get("url") or ""
            pub = it.get("publish_time") or ""

            by_url = 0
            if url:
                by_url = conn.execute("SELECT COUNT(*) FROM news_items WHERE url = ?", [url]).fetchone()[0]
            by_title = conn.execute(
                "SELECT COUNT(*) FROM news_items WHERE TRIM(COALESCE(title,'')) = ? "
                "AND TRIM(COALESCE(publish_time,'')) = ?",
                [title, pub],
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
                        GLOBAL_SYMBOL,
                        site,
                        "RSS",
                        title,
                        "",
                        url or None,
                        feed_url[:300],
                        "国际宏观",
                        pub or None,
                        None,
                        None,
                    ],
                )
                inserted += 1
            except Exception as e:
                print(f"  RSS 写入跳过: {e!s}")
                continue

            if do_push and patterns and _title_matches_breaking(title, patterns):
                sig = hashlib.sha256(f"{title}|{url}".encode("utf-8", errors="ignore")).hexdigest()
                if sig not in sent_hashes:
                    front = (os.environ.get("FRONTEND_BASE_URL") or "https://htma.newhigh.com.cn").rstrip("/")
                    body = (
                        f"[宏观突发] {title}\n"
                        f"{(url or '无链接')[:500]}\n"
                        f"时间(源): {pub or now_iso}\n"
                        f"全文新闻页: {front}/news"
                    )
                    if _send_feishu_text(webhook, body):
                        sent_hashes.add(sig)
                        _append_sent_hash(hash_file, sig)

    conn.close()
    if inserted:
        print(f"RSS 宏观快讯: 新写入 {inserted} 条")
    return inserted
