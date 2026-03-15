"""财新新闻采集器：从财新网采集财经新闻。"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import pandas as pd


def update_caixin_news(keywords: str = "*", days_back: int = 7) -> int:
    """
    采集财新网新闻并存储到DuckDB。

    Args:
        keywords: 搜索关键词，默认"*"表示所有
        days_back: 回溯天数，默认采集最近7天新闻

    Returns:
        采集的新闻数量
    """
    try:
        import tushare.internet.caixinnews as caixin
    except ImportError:
        print("Error: tushare package not found or caixinnews module not available")
        return 0

    try:
        from ..storage.duckdb_manager import get_conn, ensure_tables
    except ImportError:
        print("Error: Could not import duckdb_manager")
        return 0

    # 计算日期范围
    end_date = dt.datetime.now()
    start_date = end_date - dt.timedelta(days=days_back)

    # 格式化日期字符串
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"采集财新新闻: 关键词={keywords}, 时间范围={start_str} 到 {end_str}")

    try:
        # 查询新闻URL列表
        urls = caixin.query_news(keywords=keywords, start_date=start_str, end_date=end_str)

        if not urls:
            print("未找到财新新闻")
            return 0

        print(f"找到 {len(urls)} 条财新新闻")

        news_data = []
        for i, url in enumerate(urls[:50]):  # 限制最多采集50条，避免耗时过长
            try:
                print(f"处理新闻 {i+1}/{min(len(urls), 50)}: {url}")
                title, content = caixin.read_page(url)

                if title and content:
                    # 提取股票代码（简单实现：从标题和内容中提取6位数字代码）
                    symbol = extract_stock_code(title + " " + content)

                    news_item = {
                        "symbol": symbol,
                        "source_site": "caixin.com",
                        "source": "财新网",
                        "title": title[:500] if len(title) > 500 else title,  # 限制标题长度
                        "content": (
                            content[:5000] if len(content) > 5000 else content
                        ),  # 限制内容长度
                        "url": url,
                        "keyword": keywords if keywords != "*" else "",
                        "tag": "财经新闻",
                        "publish_time": extract_publish_time(url, content),  # 需要从URL或内容提取
                        "sentiment_score": 0.0,  # 默认情感分数，可后续分析
                        "sentiment_label": "neutral",  # 默认情感标签
                    }
                    news_data.append(news_item)

            except Exception as e:
                print(f"处理新闻失败 {url}: {e}")
                continue

        if not news_data:
            print("未成功解析任何财新新闻内容")
            return 0

        # 存储到DuckDB
        df = pd.DataFrame(news_data)
        conn = get_conn()
        ensure_tables(conn)

        # 检查是否已存在相同URL的新闻（避免重复）
        for _, row in df.iterrows():
            existing = conn.execute(
                "SELECT COUNT(*) FROM news_items WHERE url = ?", [row["url"]]
            ).fetchone()[0]

            if existing == 0:
                conn.execute(
                    """
                    INSERT INTO news_items 
                    (symbol, source_site, source, title, content, url, keyword, tag, publish_time, sentiment_score, sentiment_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    [
                        row["symbol"],
                        row["source_site"],
                        row["source"],
                        row["title"],
                        row["content"],
                        row["url"],
                        row["keyword"],
                        row["tag"],
                        row["publish_time"],
                        row["sentiment_score"],
                        row["sentiment_label"],
                    ],
                )

        count = conn.execute(
            "SELECT COUNT(*) FROM news_items WHERE source_site = 'caixin.com'"
        ).fetchone()[0]
        conn.close()

        print(f"成功存储 {len(news_data)} 条财新新闻，数据库中共有 {count} 条财新新闻")
        return len(news_data)

    except Exception as e:
        print(f"采集财新新闻失败: {e}")
        return 0


def extract_stock_code(text: str) -> str:
    """
    从文本中提取股票代码。
    简单实现：查找6位数字代码，并添加市场后缀。
    """
    import re

    # 查找6位数字代码
    codes = re.findall(r"\b(\d{6})\b", text)

    if codes:
        code = codes[0]
        # 简单判断市场：6开头为沪市，0或3开头为深市
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith("0") or code.startswith("3"):
            return f"{code}.SZ"
        else:
            return f"{code}.UNKNOWN"

    return ""


def extract_publish_time(url: str, content: str) -> str:
    """
    从URL或内容中提取发布时间。
    简单实现：从URL中提取日期或使用当前时间。
    """
    import re
    from datetime import datetime

    # 尝试从URL中提取日期（财新URL通常包含日期）
    date_patterns = [
        r"/(\d{4})-(\d{2})-(\d{2})/",
        r"/(\d{4})(\d{2})(\d{2})/",
        r"_(\d{4})-(\d{2})-(\d{2})_",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, url)
        if match:
            if len(match.groups()) == 3:
                year, month, day = match.groups()
                return f"{year}-{month}-{day} 00:00:00"

    # 尝试从内容中查找日期
    content_date_patterns = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
    ]

    for pattern in content_date_patterns:
        match = re.search(pattern, content[:1000])  # 只在前1000字符中查找
        if match:
            if len(match.groups()) == 3:
                year, month, day = match.groups()
                month = month.zfill(2)
                day = day.zfill(2)
                return f"{year}-{month}-{day} 00:00:00"

    # 默认返回当前时间
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    # 测试代码
    count = update_caixin_news(keywords="经济", days_back=3)
    print(f"采集了 {count} 条财新新闻")
