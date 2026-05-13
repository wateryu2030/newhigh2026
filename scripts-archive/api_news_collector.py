#!/usr/bin/env python3
"""
新闻 API 采集器 - 方案 C（外部 API 集成）
支持多个新闻 API 服务，自动去重，稳定可靠

数据源:
- 聚合数据 (juhe.cn) - 主数据源
- 新浪财经 API - 免费补充
- 东方财富 API - 免费补充
- RSS 源 - 兜底方案
"""

import os
import sys
import json
import hashlib
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

try:
    import requests
    import feedparser  # RSS 解析
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    print(f"❌ 缺少依赖：{e}")
    print("请运行：pip install requests feedparser")

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("❌ duckdb 未安装")


@dataclass
class NewsItem:
    """新闻数据结构"""
    id: str
    title: str
    content: str
    source: str
    url: str
    publish_time: str
    category: str = "general"
    keywords: str = ""
    sentiment_score: float = 0.5
    sentiment_label: str = "neutral"
    collected_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NewsAPICollector:
    """新闻 API 采集器"""

    def __init__(self):
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        # API 配置
        self.juhe_key = os.getenv("JUHE_API_KEY", "")
        self.juhe_available = bool(self.juhe_key)

        # 去重缓存
        self.seen_urls = set()
        self.seen_titles = set()

    def generate_id(self, title: str, url: str) -> str:
        """生成唯一 ID（基于标题+URL）"""
        content = f"{title}:{url}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]

    def is_duplicate(self, title: str, url: str) -> bool:
        """检查是否重复"""
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        title_hash = hashlib.md5(title[:50].encode('utf-8')).hexdigest()

        if url_hash in self.seen_urls or title_hash in self.seen_titles:
            return True

        self.seen_urls.add(url_hash)
        self.seen_titles.add(title_hash)
        return False

    def fetch_juhe_finance(self, limit: int = 50) -> List[NewsItem]:
        """
        从聚合数据获取财经新闻

        API 文档：https://www.juhe.cn/docs/api/id/235
        """
        news_list = []

        if not self.juhe_available:
            print("  ⚠️  跳过聚合数据 API（未配置 JUHE_API_KEY）")
            return news_list

        url = "http://v.juhe.cn/toutiao/index"
        params = {
            "type": "finance",
            "key": self.juhe_key
        }

        try:
            print("  📡 请求聚合数据 API...")
            response = self.session.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("error_code") != 0:
                print(f"  ⚠️  API 返回错误：{data.get('reason', '未知错误')}")
                return news_list

            result = data.get("result", {})
            items = result.get("data", [])

            for item in items[:limit]:
                title = item.get("title", "")
                url = item.get("url", "")

                if not title or self.is_duplicate(title, url):
                    continue

                news = NewsItem(
                    id=self.generate_id(title, url),
                    title=title,
                    content=item.get("description", "") or item.get("content", ""),
                    source="聚合数据-" + item.get("author_name", "财经新闻"),
                    url=url,
                    publish_time=item.get("date", dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    category="finance",
                    keywords="财经，新闻",
                    collected_at=dt.datetime.now().isoformat()
                )
                news_list.append(news)

            print(f"  ✅ 获取 {len(news_list)} 条财经新闻")

        except Exception as e:
            print(f"  ❌ 聚合数据 API 失败：{e}")

        return news_list

    def fetch_sina_finance(self, limit: int = 50) -> List[NewsItem]:
        """
        从新浪财经获取 7x24 快讯

        API: https://feed.mix.sina.com.cn/api/roll/get
        """
        news_list = []

        url = "https://feed.mix.sina.com.cn/api/roll/get"
        params = {
            "pageid": "153",
            "lid": "2509",  # 财经频道
            "num": str(limit),
            "format": "json"
        }

        try:
            print("  📡 请求新浪财经 API...")
            response = self.session.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            # 正确的解析路径：result.data
            items = data.get("result", {}).get("data", [])

            for item in items:
                title = item.get("title", "")
                url = item.get("url", "")

                if not title or self.is_duplicate(title, url):
                    continue

                # 转换时间格式
                ctime = item.get("ctime", "")
                if ctime:
                    try:
                        publish_time = dt.datetime.fromtimestamp(int(ctime)).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        publish_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    publish_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                news = NewsItem(
                    id=self.generate_id(title, url),
                    title=title,
                    content=item.get("description", "") or item.get("content", ""),
                    source="新浪财经",
                    url=url,
                    publish_time=publish_time,
                    category="finance",
                    keywords="财经，股票，快讯",
                    collected_at=dt.datetime.now().isoformat()
                )
                news_list.append(news)

            print(f"  ✅ 获取 {len(news_list)} 条新浪财经新闻")

        except Exception as e:
            print(f"  ❌ 新浪财经 API 失败：{e}")

        return news_list

    def fetch_eastmoney_news(self, limit: int = 50) -> List[NewsItem]:
        """
        从东方财富获取快讯

        API: https://push2.eastmoney.com/api/qt/ulist/get
        """
        news_list = []

        url = "https://push2.eastmoney.com/api/qt/ulist/get"
        params = {
            "pn": "1",
            "pz": str(limit),
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f19,f13,f15,f16,f17,f18",
            "_": str(int(dt.datetime.now().timestamp() * 1000))
        }

        try:
            print("  📡 请求东方财富 API...")
            response = self.session.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get("data", {}).get("diff", [])

            for item in items:
                title = item.get("f14", "")  # 标题
                content = item.get("f19", "")  # 内容

                if not title:
                    continue

                # 生成 URL（东方财富快讯 URL 格式）
                url = f"https://quote.eastmoney.com/news/{item.get('f12', '')}.html"

                if self.is_duplicate(title, url):
                    continue

                # 时间戳转换
                ts = item.get("f19", "")
                if isinstance(ts, (int, float)):
                    publish_time = dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    publish_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                news = NewsItem(
                    id=self.generate_id(title, url),
                    title=title,
                    content=content,
                    source="东方财富",
                    url=url,
                    publish_time=publish_time,
                    category="finance",
                    keywords="财经，股票，快讯",
                    collected_at=dt.datetime.now().isoformat()
                )
                news_list.append(news)

            print(f"  ✅ 获取 {len(news_list)} 条东方财富新闻")

        except Exception as e:
            print(f"  ❌ 东方财富 API 失败：{e}")

        return news_list

    def fetch_rss_news(self, feed_urls: List[str] = None) -> List[NewsItem]:
        """
        从 RSS 源获取新闻（兜底方案）
        """
        if feed_urls is None:
            feed_urls = [
                # 国际财经（中文）
                "https://feeds.bbci.co.uk/news/world/asia/china/rss.xml",
                # 备用源
                "https://www.reutersagency.com/feed/?best-topics=china-finance&post_type=best",
            ]

        news_list = []

        for feed_url in feed_urls:
            try:
                print(f"  📡 解析 RSS: {feed_url[:50]}...")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:20]:
                    title = entry.get("title", "")
                    url = entry.get("link", "")

                    if not title or self.is_duplicate(title, url):
                        continue

                    # 时间解析
                    publish_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            publish_time = dt.datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            pass

                    news = NewsItem(
                        id=self.generate_id(title, url),
                        title=title,
                        content=entry.get("summary", "") or entry.get("description", ""),
                        source=f"RSS-{feed.feed.get('title', 'Unknown')}",
                        url=url,
                        publish_time=publish_time,
                        category="finance",
                        keywords="财经，RSS",
                        collected_at=dt.datetime.now().isoformat()
                    )
                    news_list.append(news)

            except Exception as e:
                print(f"  ⚠️  RSS 解析失败 {feed_url[:40]}: {e}")

        if news_list:
            print(f"  ✅ 获取 {len(news_list)} 条 RSS 新闻")

        return news_list

    def save_to_duckdb(self, news_list: List[NewsItem]) -> int:
        """保存到 DuckDB 数据库"""
        if not DUCKDB_AVAILABLE or not news_list:
            return 0

        db_path = project_root / "data" / "quant_system.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = duckdb.connect(str(db_path))

        # 确保表存在（添加 id 字段）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_items (
                id VARCHAR,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR DEFAULT 'ALL',
                source_site VARCHAR,
                source VARCHAR,
                title VARCHAR,
                content TEXT,
                url VARCHAR,
                keyword VARCHAR,
                tag VARCHAR,
                publish_time VARCHAR,
                sentiment_score DOUBLE,
                sentiment_label VARCHAR,
                PRIMARY KEY (id)
            )
        """)

        # 检查是否需要添加 id 列到现有表
        try:
            columns = conn.execute("DESCRIBE news_items").fetchall()
            column_names = [col[0] for col in columns]
            if 'id' not in column_names:
                print("  📝 检测到旧表结构，添加 id 列...")
                conn.execute("ALTER TABLE news_items ADD COLUMN id VARCHAR")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_news_id ON news_items(id)")
        except Exception as e:
            print(f"  ⚠️  表结构检查失败：{e}")

        saved = 0
        for news in news_list:
            try:
                # 检查是否已存在（基于 ID）
                existing = conn.execute(
                    "SELECT id FROM news_items WHERE id = ?",
                    (news.id,)
                ).fetchone()

                if existing:
                    continue

                conn.execute("""
                    INSERT INTO news_items (
                        id, ts, symbol, source_site, source,
                        title, content, url, keyword, tag,
                        publish_time, sentiment_score, sentiment_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    news.id,
                    dt.datetime.now(),
                    'ALL',
                    news.category,
                    news.source,
                    news.title,
                    news.content,
                    news.url,
                    news.keywords,
                    'API',
                    news.publish_time,
                    news.sentiment_score,
                    news.sentiment_label
                ])
                saved += 1

            except Exception as e:
                print(f"  ⚠️  保存失败 {news.title[:30]}: {e}")

        conn.close()
        return saved

    def collect_all(self) -> Dict[str, Any]:
        """采集所有新闻源"""
        print("=" * 60)
        print("📰 新闻 API 采集器 - 方案 C")
        print(f"执行时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if not REQUESTS_AVAILABLE:
            print("❌ 缺少依赖包，请运行：pip install requests feedparser")
            return {"error": "missing_dependencies"}

        all_news = []
        stats = {
            "juhe": 0,
            "sina": 0,
            "eastmoney": 0,
            "rss": 0,
            "total": 0,
            "saved": 0,
            "duplicates": 0
        }

        # 1. 聚合数据（主数据源）
        print("\n1️⃣  聚合数据 API...")
        juhe_news = self.fetch_juhe_finance(limit=50)
        all_news.extend(juhe_news)
        stats["juhe"] = len(juhe_news)

        # 2. 新浪财经（免费补充）
        print("\n2️⃣  新浪财经 API...")
        sina_news = self.fetch_sina_finance(limit=50)
        all_news.extend(sina_news)
        stats["sina"] = len(sina_news)

        # 3. 东方财富（免费补充）
        print("\n3️⃣  东方财富 API...")
        em_news = self.fetch_eastmoney_news(limit=50)
        all_news.extend(em_news)
        stats["eastmoney"] = len(em_news)

        # 4. RSS 源（兜底）
        print("\n4️⃣  RSS 源...")
        rss_news = self.fetch_rss_news()
        all_news.extend(rss_news)
        stats["rss"] = len(rss_news)

        stats["total"] = len(all_news)

        # 保存到数据库
        print("\n" + "=" * 60)
        print(f"总计采集：{len(all_news)} 条新闻")
        print("保存到数据库...")

        saved = self.save_to_duckdb(all_news)
        stats["saved"] = saved

        print(f"✅ 保存成功 {saved} 条（去重后）")

        # 显示最新新闻
        if all_news:
            print("\n📋 最新 5 条新闻:")
            for news in all_news[:5]:
                print(f"  - {news.title[:50]} ({news.source})")

        print("\n" + "=" * 60)
        print("✅ 采集任务完成!")
        print("=" * 60)

        # 统计信息
        print("\n📊 采集统计:")
        print(f"  聚合数据：{stats['juhe']} 条")
        print(f"  新浪财经：{stats['sina']} 条")
        print(f"  东方财富：{stats['eastmoney']} 条")
        print(f"  RSS 源：{stats['rss']} 条")
        print(f"  总计：{stats['total']} 条")
        print(f"  入库：{stats['saved']} 条")

        # 保存执行日志
        self.save_log(stats)

        return stats

    def save_log(self, stats: Dict[str, Any]):
        """保存执行日志"""
        log_dir = project_root / "logs" / "news_api"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"run_{timestamp}.json"

        log_data = {
            "timestamp": dt.datetime.now().isoformat(),
            "stats": stats
        }

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        print(f"\n📝 日志已保存：{log_file}")


def main():
    """主函数"""
    collector = NewsAPICollector()
    stats = collector.collect_all()
    return stats


if __name__ == "__main__":
    stats = main()

    # 如果没有获取到任何新闻，退出时返回错误码
    if stats.get("total", 0) == 0:
        print("\n⚠️  警告：未采集到任何新闻")
        sys.exit(1)

    sys.exit(0)
