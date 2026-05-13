"""
A股公司传闻/谣言采集器 (CLI)

从雪球热门推文、东方财富股吧热帖、已有 news_items 表中捕获
公司级别的传闻/谣言/澄清信息，写入 DuckDB company_rumors 表。

用法:
    python -m rumor_capture                    # 默认采集最近7天
    python -m rumor_capture --days 3           # 最近3天
    python -m rumor_capture --dry-run          # 预览模式
    python -m rumor_capture --source xueqiu    # 仅雪球
    python -m rumor_capture --source guba      # 仅东方财富股吧
    python -m rumor_capture --source news      # 仅 news_items 回退
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# 模块级路径修补
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_PKG_ROOT = _THIS_FILE.parent.parent.parent.parent  # rumor-capture/
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

# 传闻关键词（命中任一即标记为"传闻"）
RUMOUR_KEYWORDS: List[str] = [
    "传闻",
    "据传",
    "知情人士",
    "爆料",
    "内部消息",
    "传言",
    "rumour",
    "rumor",
]

# 澄清/辟谣关键词（命中任一 => rumor_type = "辟谣"）
CLARIFICATION_KEYWORDS: List[str] = [
    "澄清",
    "辟谣",
    "否认",
    "回应传闻",
    "说明",
]

# 利好关键词（用于辅助判定）
BULLISH_KEYWORDS: List[str] = [
    "回购",
    "增持",
    "收购",
    "要约",
    "溢价收购",
    "重大利好",
    "合同中标",
    "业绩预增",
    "重组",
]

# 利空关键词
BEARISH_KEYWORDS: List[str] = [
    "减持",
    "亏损",
    "暴雷",
    "违约",
    "st",
    "退市",
    "立案",
    "调查",
    "处罚",
    "跌停",
]

# 来源名称
SOURCE_XUEQIU = "雪球"
SOURCE_GUBA = "东方财富股吧"
SOURCE_NEWS = "news_items"

# DuckDB 时间戳列名
CREATED_AT = "created_at"
PUBLISH_TIME = "publish_time"

# 东财股吧 API
GUBA_API_URL = "https://guba.eastmoney.com/list,{code},1,f.html"
GUBA_ARTICLE_URL = "https://guba.eastmoney.com/news,{code},{artid}.html"

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


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


def ensure_company_rumors_table(conn: duckdb.DuckDBPyConnection) -> None:
    """确保 company_rumors 表存在（列与 duckdb_manager.ensure_tables 一致）。"""
    conn.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS seq_company_rumors_id START 1
    """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS company_rumors (
            id              INTEGER PRIMARY KEY DEFAULT nextval('seq_company_rumors_id'),
            stock_code      VARCHAR,
            title           VARCHAR,
            content         VARCHAR,
            source          VARCHAR,
            source_url      VARCHAR,
            rumor_type      VARCHAR,       -- 利好/利空/辟谣/中性/其他
            publish_time    VARCHAR,
            keywords        VARCHAR,       -- 逗号分隔
            sentiment_score DOUBLE,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )


def content_hash(title: str, content: str) -> str:
    """生成标题+内容的去重哈希。"""
    raw = f"{title or ''}|{content or ''}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def is_rumour_related(title: str, content: str) -> bool:
    """检查标题/内容是否命中传闻/澄清关键词（返回 True 的关键在于 rumor_type 判定）。"""
    combined = f"{title or ''} {content or ''}".lower()
    kw_set = set(RUMOUR_KEYWORDS + CLARIFICATION_KEYWORDS + BULLISH_KEYWORDS)
    for kw in kw_set:
        if kw.lower() in combined:
            return True
    return False


def classify_rumor_type(title: str, content: str) -> str:
    """基于关键词判定传闻类型。

    Returns:
        "辟谣" / "利好" / "利空" / "中性" / "其他"
    """
    combined = f"{title or ''} {content or ''}"

    # 澄清/辟谣优先
    for kw in CLARIFICATION_KEYWORDS:
        if kw in combined:
            return "辟谣"

    # 利好关键词
    has_bullish = any(kw in combined for kw in BULLISH_KEYWORDS)
    # 利空关键词
    has_bearish = any(kw in combined for kw in BEARISH_KEYWORDS)

    if has_bullish and has_bearish:
        return "中性"
    if has_bullish:
        return "利好"
    if has_bearish:
        return "利空"

    # 命中传闻关键词但无明确倾向
    for kw in RUMOUR_KEYWORDS:
        if kw in combined:
            return "中性"

    return "其他"


def extract_keywords(title: str, content: str) -> str:
    """从标题+内容中提取所有命中的关键词，逗号分隔。"""
    combined = f"{title or ''} {content or ''}"
    kw_set: Set[str] = set()
    all_kw = RUMOUR_KEYWORDS + CLARIFICATION_KEYWORDS + BULLISH_KEYWORDS + BEARISH_KEYWORDS
    for kw in all_kw:
        if kw.lower() in combined.lower():
            kw_set.add(kw)
    return ",".join(sorted(kw_set))


def compute_sentiment_score(title: str, content: str) -> float:
    """简单的基于关键词的情感打分。

    范围 -1.0 ~ 1.0。
    """
    combined = f"{title or ''} {content or ''}"
    score = 0.0

    for kw in BULLISH_KEYWORDS:
        if kw in combined:
            score += 0.3
    for kw in BEARISH_KEYWORDS:
        if kw in combined:
            score -= 0.3
    for kw in CLARIFICATION_KEYWORDS:
        if kw in combined:
            score += 0.1  # 澄清通常偏正面或中性

    # 限制范围
    return max(-1.0, min(1.0, score))


def load_stock_map(conn: duckdb.DuckDBPyConnection) -> Dict[str, str]:
    """从 stocks 表加载 {name: symbol} 映射，用于从内容匹配股票代码。"""
    mapping: Dict[str, str] = {}
    try:
        rows = conn.execute(
            "SELECT DISTINCT symbol, name FROM stocks WHERE name IS NOT NULL AND name != ''"
        ).fetchall()
        for symbol, name in rows:
            name_clean = name.strip()
            if name_clean:
                mapping[name_clean] = symbol.strip()
    except Exception:
        pass
    return mapping


def match_stock_code(
    title: str,
    content: str,
    stock_map: Dict[str, str],
) -> Optional[str]:
    """尝试从标题/内容中匹配股票代码。

    策略:
      1. 正则匹配 6 位数字代码
      2. 匹配股票名称（stock_map 中的 name）
    """
    combined = f"{title or ''} {content or ''}"

    # 策略 1: 6 位数字代码
    codes = re.findall(r"\b(60[0-9]{4}|00[0-9]{4}|30[0-9]{4}|68[0-9]{4}|83[0-9]{4}|87[0-9]{4})\b", combined)
    if codes:
        return codes[0]

    # 策略 2: 匹配股票名称
    for name, symbol in stock_map.items():
        if name in combined:
            return symbol

    return None


# ---------------------------------------------------------------------------
# 数据源采集
# ---------------------------------------------------------------------------


def fetch_xueqiu_tweets(
    days: int,
    conn: duckdb.DuckDBPyConnection,
) -> List[Dict[str, Any]]:
    """从雪球热度推文采集数据（akshare.stock_hot_tweet_xq）。

    akshare 返回的列: 股票代码, 股票简称, 关注, 最新价
    我们将每只股票作为一条"热门话题"记录。

    Returns:
        符合 company_rumors 格式的字典列表。
    """
    import akshare as ak

    records: List[Dict[str, Any]] = []
    stock_map = load_stock_map(conn)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for mode_name in ("最热门", "本周新增"):
        try:
            df = ak.stock_hot_tweet_xq(symbol=mode_name)
        except Exception as exc:
            print(f"  [警告] 雪球 {mode_name} 采集失败: {exc}", file=sys.stderr, flush=True)
            continue

        if df is None or df.empty:
            continue

        for _, row in df.iterrows():
            symbol = str(row.get("股票代码", "") or "").strip()
            name = str(row.get("股票简称", "") or "").strip()
            tweet_count = row.get("关注", 0)
            price = row.get("最新价", 0)

            # 构建标题和内容
            title = f"{name}({symbol}) 雪球热门讨论"
            content = (
                f"股票 {name}({symbol}) 在雪球平台热度较高，"
                f"当前讨论量 {tweet_count}，最新价 {price}。"
            )

            # 归一化股票代码（去掉可能的前缀）
            code = symbol.replace("SH", "").replace("SZ", "").strip()
            if not code or not code.isdigit() or len(code) != 6:
                code = symbol  # 保留原样

            records.append(
                {
                    "stock_code": code,
                    "title": title,
                    "content": content,
                    "source": SOURCE_XUEQIU,
                    "source_url": f"https://xueqiu.com/S/{symbol}",
                    "rumor_type": "其他",  # 雪球数据本身不区分传闻类型
                    "publish_time": now_str,
                    "keywords": extract_keywords(title, content),
                    "sentiment_score": compute_sentiment_score(title, content),
                }
            )

    print(f"  [雪球] 采集 {len(records)} 条热门话题", file=sys.stderr, flush=True)
    return records


def fetch_guba_posts(
    days: int,
    conn: duckdb.DuckDBPyConnection,
    top_n: int = 100,
) -> List[Dict[str, Any]]:
    """从东方财富股吧采集热门帖子。

    使用 akshare.stock_hot_rank_em() 获取人气榜股票列表，
    然后对前 top_n 只股票，通过 requests 抓取股吧帖子。

    Returns:
        符合 company_rumors 格式的字典列表。
    """
    import requests

    import akshare as ak

    records: List[Dict[str, Any]] = []
    stock_map = load_stock_map(conn)
    now_ts = datetime.now(timezone.utc)
    cutoff = now_ts - timedelta(days=days)

    # 1. 获取人气榜股票
    try:
        rank_df = ak.stock_hot_rank_em()
    except Exception as exc:
        print(f"  [警告] 东方财富人气榜采集失败: {exc}", file=sys.stderr, flush=True)
        return records

    if rank_df is None or rank_df.empty:
        return records

    stocks = rank_df.head(top_n).to_dict("records")

    for stock in stocks:
        code_raw = str(stock.get("代码", "") or "").strip()
        # 代码格式类似 "SZ000001" 或 "SH600519"
        code = code_raw.replace("SH", "").replace("SZ", "").strip()
        name = str(stock.get("股票名称", "") or "").strip()

        if not code or not code.isdigit():
            continue

        # 2. 请求股吧列表页
        url = f"https://guba.eastmoney.com/list,{code},1,f.html"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            resp.encoding = "utf-8"
            html = resp.text
        except Exception as exc:
            print(f"    [股吧] {code} 请求失败: {exc}", file=sys.stderr, flush=True)
            continue

        # 3. 简单的 HTML 解析 — 提取文章标题和链接
        # 股吧列表页包含 <div class="articleh ..."> 结构
        articles = _parse_guba_html(html, code)
        for art in articles:
            pub_time_str = art.get("publish_time", "")
            # 时间过滤
            if pub_time_str:
                try:
                    art_time = _parse_guba_time(pub_time_str)
                    if art_time and art_time < cutoff:
                        continue
                except Exception:
                    pass

            title = art.get("title", "")
            content = art.get("content", title)
            art_url = art.get("url", "")

            # 只保留与传闻相关的帖子
            if not is_rumour_related(title, content):
                continue

            matched_code = match_stock_code(title, content, stock_map) or code

            records.append(
                {
                    "stock_code": matched_code,
                    "title": title,
                    "content": content,
                    "source": SOURCE_GUBA,
                    "source_url": art_url,
                    "rumor_type": classify_rumor_type(title, content),
                    "publish_time": pub_time_str,
                    "keywords": extract_keywords(title, content),
                    "sentiment_score": compute_sentiment_score(title, content),
                }
            )

    print(f"  [股吧] 采集 {len(records)} 条传闻相关帖子", file=sys.stderr, flush=True)
    return records


def _parse_guba_html(html: str, code: str) -> List[Dict[str, Any]]:
    """从股吧列表页 HTML 中解析文章列表。

    股吧页面结构大致为:
        <div class="articleh">
            <span class="l3"><a href="/news,{code},{artid}.html">标题</a></span>
            <span class="l6">作者</span>
            <span class="l9">2025-12-01 10:30:00</span>
        </div>

    这是一个简化解析器，生产环境中建议用 lxml 或正则提取。
    """
    import html as html_mod

    articles: List[Dict[str, Any]] = []

    # 寻找文章条目
    pattern = re.compile(
        r'<div[^>]*class\s*=\s*["\']articleh[^>]*>.*?</div>',
        re.DOTALL,
    )
    blocks = pattern.findall(html)

    for block_html in blocks:
        # 提取标题
        title_match = re.search(
            r'<span[^>]*class\s*=\s*["\']l3[^>]*>.*?<a[^>]*href\s*=\s*["\'](/news/[^"\']+)["\'][^>]*>(.*?)</a>',
            block_html,
            re.DOTALL,
        )
        if not title_match:
            # 尝试更宽松的匹配
            title_match = re.search(
                r'<a[^>]*href\s*=\s*["\'](/news/[^"\']+)["\'][^>]*>(.*?)</a>',
                block_html,
                re.DOTALL,
            )

        if not title_match:
            continue

        href = title_match.group(1).strip()
        title_raw = title_match.group(2).strip()
        title = html_mod.unescape(re.sub(r"<[^>]+>", "", title_raw)).strip()

        if not title:
            continue

        # 提取时间
        time_match = re.search(
            r'<span[^>]*class\s*=\s*["\']l9[^>]*>(.*?)</span>',
            block_html,
        )
        pub_time = ""
        if time_match:
            pub_time = time_match.group(1).strip()

        # 提取作者（l6）
        author_match = re.search(
            r'<span[^>]*class\s*=\s*["\']l6[^>]*>(.*?)</span>',
            block_html,
        )
        author = ""
        if author_match:
            author = html_mod.unescape(re.sub(r"<[^>]+>", "", author_match.group(1))).strip()

        # 构建 URL
        art_id = ""
        id_match = re.search(r"/news/[^/]+?/(\d+)", href)
        if id_match:
            art_id = id_match.group(1)
        article_url = GUBA_ARTICLE_URL.format(code=code, artid=art_id) if art_id else ""

        content = f"[股吧]{title}"
        if author:
            content += f" 作者:{author}"

        articles.append(
            {
                "title": title,
                "content": content,
                "url": article_url,
                "publish_time": pub_time,
                "author": author,
            }
        )

    return articles


def _parse_guba_time(time_str: str) -> Optional[datetime]:
    """解析股吧时间字符串。"""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m-%d %H:%M"):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def fetch_news_fallback(
    days: int,
    conn: duckdb.DuckDBPyConnection,
) -> List[Dict[str, Any]]:
    """从 news_items 表中回退采集与传闻关键词匹配的新闻。

    Returns:
        符合 company_rumors 格式的字典列表。
    """
    records: List[Dict[str, Any]] = []
    stock_map = load_stock_map(conn)

    # 检查表是否存在
    try:
        conn.execute("SELECT 1 FROM news_items LIMIT 1")
    except Exception:
        return records

    now_ts = datetime.now(timezone.utc)
    cutoff_date = (now_ts - timedelta(days=days)).strftime("%Y-%m-%d")

    # 构建关键词查询条件
    kw_conditions = []
    all_kw = RUMOUR_KEYWORDS + CLARIFICATION_KEYWORDS + BULLISH_KEYWORDS
    for kw in all_kw:
        kw_conditions.append(f"title ILIKE '%{kw}%'")
        kw_conditions.append(f"content ILIKE '%{kw}%'")

    if not kw_conditions:
        return records

    where_clause = " OR ".join(kw_conditions)
    sql = f"""
        SELECT
            ts, symbol, source_site, source, title, content,
            url, keyword, tag, publish_time, sentiment_score, sentiment_label
        FROM news_items
        WHERE ({where_clause})
          AND (publish_time >= ? OR publish_time IS NULL OR publish_time = '')
        ORDER BY publish_time DESC
        LIMIT 2000
    """

    try:
        rows = conn.execute(sql, [cutoff_date]).fetchall()
        cols = [
            "ts",
            "symbol",
            "source_site",
            "source",
            "title",
            "content",
            "url",
            "keyword",
            "tag",
            "publish_time",
            "sentiment_score",
            "sentiment_label",
        ]
    except Exception as exc:
        print(f"  [警告] news_items 查询失败: {exc}", file=sys.stderr, flush=True)
        return records

    for row in rows:
        item = dict(zip(cols, row))
        title = str(item.get("title", "") or "")
        content = str(item.get("content", "") or "")
        pub_time = str(item.get("publish_time", "") or "")
        news_symbol = str(item.get("symbol", "") or "").strip()
        src_url = str(item.get("url", "") or "")
        src_site = str(item.get("source_site", "") or str(item.get("source", "") or SOURCE_NEWS))

        # 匹配股票代码
        matched_code = news_symbol if news_symbol and len(news_symbol) >= 4 else ""
        if not matched_code:
            mc = match_stock_code(title, content, stock_map)
            if mc:
                matched_code = mc

        records.append(
            {
                "stock_code": matched_code,
                "title": title,
                "content": content[:5000],  # 限制长度
                "source": f"{SOURCE_NEWS}({src_site})",
                "source_url": src_url,
                "rumor_type": classify_rumor_type(title, content),
                "publish_time": pub_time,
                "keywords": extract_keywords(title, content),
                "sentiment_score": float(item.get("sentiment_score", 0) or 0),
            }
        )

    print(f"  [news_items] 采集 {len(records)} 条传闻相关新闻", file=sys.stderr, flush=True)
    return records


# ---------------------------------------------------------------------------
# 去重
# ---------------------------------------------------------------------------


def dedup_records(
    records: List[Dict[str, Any]],
    source: str,
    conn: duckdb.DuckDBPyConnection,
) -> List[Dict[str, Any]]:
    """对同一来源的记录按 title+content hash 去重。"""
    if not records:
        return []

    # 1. 内存去重（同一批次内的重复）
    seen: Set[str] = set()
    unique: List[Dict[str, Any]] = []
    for r in records:
        h = content_hash(r.get("title", ""), r.get("content", ""))
        if h not in seen:
            seen.add(h)
            unique.append(r)

    # 2. 数据库去重（检查已存在的记录）
    if not unique:
        return []

    # 分批查询已存在的哈希
    try:
        existing_hashes: Set[str] = set()
        # 对数据库中的记录计算哈希并比较
        existing_rows = conn.execute(
            """
            SELECT title, content
            FROM company_rumors
            WHERE source = ?
              AND title IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 50000
            """,
            [source],
        ).fetchall()

        for title, content in existing_rows:
            h = content_hash(title or "", content or "")
            existing_hashes.add(h)
    except Exception:
        existing_hashes = set()

    result = [r for r in unique if content_hash(r.get("title", ""), r.get("content", "")) not in existing_hashes]
    return result


# ---------------------------------------------------------------------------
# 批量写入
# ---------------------------------------------------------------------------


def write_records(
    records: List[Dict[str, Any]],
    conn: duckdb.DuckDBPyConnection,
    dry_run: bool = False,
) -> int:
    """写入 company_rumors 表。

    Returns:
        写入的行数。
    """
    if not records:
        return 0

    if dry_run:
        print(f"  [dry-run] 将写入 {len(records)} 行到 company_rumors 表", file=sys.stderr)
        for r in records[:5]:
            print(
                f"    - [{r['rumor_type']}] {r['stock_code']}: {r['title'][:60]}...",
                file=sys.stderr,
            )
        if len(records) > 5:
            print(f"    ... 还有 {len(records) - 5} 行", file=sys.stderr)
        return len(records)

    now_ts = datetime.now()

    conn.executemany(
        """
        INSERT INTO company_rumors
            (stock_code, title, content, source, source_url,
             rumor_type, publish_time, keywords, sentiment_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.get("stock_code", ""),
                r.get("title", ""),
                r.get("content", ""),
                r.get("source", ""),
                r.get("source_url", ""),
                r.get("rumor_type", "其他"),
                r.get("publish_time", ""),
                r.get("keywords", ""),
                r.get("sentiment_score", 0.0),
                now_ts,
            )
            for r in records
        ],
    )
    return len(records)


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------


def collect_rumors(
    days: int,
    sources: List[str],
    conn: duckdb.DuckDBPyConnection,
    dry_run: bool = False,
) -> Tuple[int, Dict[str, int]]:
    """执行完整的传闻采集流程。

    Args:
        days: 采集最近 N 天的数据。
        sources: 数据来源列表（'xueqiu', 'guba', 'news'）。
        conn: DuckDB 连接。
        dry_run: 预览模式。

    Returns:
        (总写入行数, {来源: 写入行数})。
    """
    ensure_company_rumors_table(conn)

    all_new_records: List[Dict[str, Any]] = []
    source_counts: Dict[str, int] = {}

    try:
        from tqdm import tqdm
    except ImportError:

        def tqdm(x, **kw):  # type: ignore
            return x

    source_handlers = {
        "xueqiu": ("雪球热门推文", fetch_xueqiu_tweets),
        "guba": ("东方财富股吧", fetch_guba_posts),
        "news": ("news_items 回退", fetch_news_fallback),
    }

    for src_key in sources:
        if src_key not in source_handlers:
            print(f"  [跳过] 未知来源: {src_key}", file=sys.stderr)
            continue

        label, handler = source_handlers[src_key]
        print(f"\n>> 采集来源: {label}", file=sys.stderr)
        raw = handler(days, conn)
        print(f"  原始采集: {len(raw)} 条", file=sys.stderr)

        if not raw:
            continue

        # 去重
        deduped = dedup_records(raw, label, conn)
        print(f"  去重后: {len(deduped)} 条新记录", file=sys.stderr)

        if not deduped:
            continue

        all_new_records.extend(deduped)

    # 写入
    print(f"\n>> 总计新记录: {len(all_new_records)} 条", file=sys.stderr)

    if not all_new_records:
        print("  无可写入的新记录。", file=sys.stderr)
        return 0, {}

    written = write_records(all_new_records, conn, dry_run=dry_run)
    source_counts["总计"] = written

    if not dry_run:
        conn.commit()

    return written, source_counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="rumor-capture",
        description="A股公司传闻/谣言采集器 — 从雪球、东方财富股吧、新闻中捕获传闻/澄清信息并写入 DuckDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m rumor_capture                          # 默认采集最近 7 天\n"
            "  python -m rumor_capture --days 3                 # 最近 3 天\n"
            "  python -m rumor_capture --dry-run                # 预览模式\n"
            "  python -m rumor_capture --source xueqiu          # 仅雪球\n"
            "  python -m rumor_capture --source guba            # 仅东方财富股吧\n"
            "  python -m rumor_capture --source news            # 仅 news_items 回退\n"
            "  python -m rumor_capture --source xueqiu,guba     # 雪球 + 股吧\n"
        ),
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        metavar="N",
        help="仅处理最近 N 天内的数据（默认: 7）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="预览模式：仅打印将要写入的记录，不实际写入数据库",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="xueqiu,guba,news",
        metavar="SOURCES",
        help=(
            "数据来源，逗号分隔。可选: xueqiu (雪球), guba (东方财富股吧), "
            "news (news_items 回退)。默认全部"
        ),
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        metavar="PATH",
        help="DuckDB 文件路径（默认从环境变量或 .env 自动获取）",
    )
    parser.add_argument(
        "--guba-top",
        type=int,
        default=100,
        metavar="N",
        help="股吧采集：人气榜前 N 只股票（默认: 100）",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    days = max(1, args.days)
    dry_run = args.dry_run
    sources_raw = [s.strip().lower() for s in args.source.split(",") if s.strip()]
    db_path = args.db_path or _db_path()

    print(f"数据库路径: {db_path}", file=sys.stderr)
    print(f"采集天数: {days}", file=sys.stderr)
    print(f"数据来源: {', '.join(sources_raw)}", file=sys.stderr)
    if dry_run:
        print("[dry-run] 模式：不会实际写入数据库", file=sys.stderr)

    # 使用 duckdb_write_lock 上下文管理器
    from duckdb_write_lock import duckdb_write_lock

    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            ensure_company_rumors_table(conn)
            total_written, source_counts = collect_rumors(
                days=days,
                sources=sources_raw,
                conn=conn,
                dry_run=dry_run,
            )

            print(f"\n{'='*50}", file=sys.stderr)
            if dry_run:
                print(f"预览完成: 共 {total_written} 条记录将被写入", file=sys.stderr)
            else:
                status = "写入" if total_written > 0 else "无新记录"
                print(f"采集完成: {status} {total_written} 条", file=sys.stderr)
            print(f"{'='*50}", file=sys.stderr)

            return 0 if total_written >= 0 else 1
        finally:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
