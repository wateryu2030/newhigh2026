#!/usr/bin/env python3
"""
优化版新闻采集器
- 使用更易访问的数据源（东方财富、同花顺、新浪财经 API）
- 支持 RSS 订阅（GitHub、技术博客等）
- 支持本地配置文件定义数据源
- 增加重试机制和缓存
"""

import sys
import datetime
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import requests
    import feedparser
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    print(f"警告：依赖库未安装：{e}")
    print("安装命令：pip install requests feedparser")

try:
    from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("警告：duckdb_manager 不可用，数据将保存到文件")


@dataclass
class NewsItem:
    """新闻数据结构"""
    id: str
    title: str
    content: str
    source: str
    department: str
    url: str
    publish_time: str
    keywords: List[str]
    collected_at: str
    sentiment_score: Optional[float] = None


class OptimizedNewsCollector:
    """优化版新闻采集器"""

    def __init__(self, config_file: str = None):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        # 默认配置 - 使用更易访问的 API 数据源
        self.config = {
            'eastmoney': {
                'name': '东方财富',
                'endpoints': [
                    'https://api.eastmoney.com/api/data/get?callback=jQuery&reportName=API_KUAIXUN&columns=1000&filter=(DATETIME%3C%3D%27{datetime}%27)&pageNumber=1&pageSize=50&sortTypes=-1&sortColumns=DATETIME&_=1234567890',
                ],
                'timeout': 10
            },
            'sina': {
                'name': '新浪财经',
                'endpoints': [
                    'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&etime={etime}&num=20',
                ],
                'timeout': 10
            },
            'jin10': {
                'name': '金十数据',
                'api_url': 'https://www.jin10.com/flash_newest.js',
                'timeout': 10
            },
            'rss_feeds': {
                'name': 'RSS 订阅',
                'feeds': [
                    # 财经 RSS
                    'https://feeds.feedburner.com/pancaitan',
                    # 技术 RSS（可选）
                    'https://github.com/trending.atom',
                ],
                'timeout': 15
            },
            'local_sources': {
                'name': '本地数据源',
                'files': [
                    'data/manual_news.json',  # 手动添加的重要新闻
                ]
            }
        }

        # 加载自定义配置
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file: str):
        """加载自定义配置文件"""
        with open(config_file, 'r', encoding='utf-8') as f:
            custom_config = json.load(f)
            # 合并配置
            for key, value in custom_config.items():
                if key in self.config:
                    self.config[key].update(value)
                else:
                    self.config[key] = value

    def init_session(self):
        """初始化请求会话"""
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update(self.headers)

    def generate_id(self, title: str, source: str, publish_time: str) -> str:
        """生成新闻 ID（去重）"""
        content = f"{title}_{source}_{publish_time}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def fetch_eastmoney_kuaixun(self) -> List[NewsItem]:
        """采集东方财富快讯"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        try:
            now = datetime.datetime.now()
            datetime_str = now.strftime('%Y-%m-%d %H:%M:%S')

            url = self.config['eastmoney']['endpoints'][0].format(datetime=datetime_str)

            resp = self.session.get(url, timeout=self.config['eastmoney']['timeout'])

            # 解析 JSONP
            import re
            json_str = re.search(r'jQuery\d+\((.*)\)', resp.text)
            if json_str:
                data = json.loads(json_str.group(1))

                for item in data.get('result', [])[:20]:  # 取最新 20 条
                    publish_time = item.get('DATETIME', '')
                    news_list.append(NewsItem(
                        id=self.generate_id(item.get('TITLE', ''), '东方财富', publish_time),
                        title=item.get('TITLE', ''),
                        content=item.get('CONTENT', ''),
                        source='东方财富',
                        department='eastmoney',
                        url=item.get('URL', ''),
                        publish_time=publish_time,
                        keywords=[],
                        collected_at=datetime.datetime.now().isoformat()
                    ))

            print(f"  东方财富快讯：{len(news_list)} 条")

        except Exception as e:
            print(f"  东方财富采集失败：{e}")

        return news_list

    def fetch_sina_finance(self) -> List[NewsItem]:
        """采集新浪财经"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        try:
            etime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            url = self.config['sina']['endpoints'][0].format(etime=etime)

            resp = self.session.get(url, timeout=self.config['sina']['timeout'])
            data = resp.json()

            for item in data.get('result', {}).get('data', [])[:20]:
                publish_time = item.get('ctime', '')
                news_list.append(NewsItem(
                    id=self.generate_id(item.get('title', ''), '新浪财经', publish_time),
                    title=item.get('title', ''),
                    content=item.get('intro', ''),
                    source='新浪财经',
                    department='sina',
                    url=item.get('url', ''),
                    publish_time=publish_time,
                    keywords=[],
                    collected_at=datetime.datetime.now().isoformat()
                ))

            print(f"  新浪财经：{len(news_list)} 条")

        except Exception as e:
            print(f"  新浪财经采集失败：{e}")

        return news_list

    def fetch_jin10_flash(self) -> List[NewsItem]:
        """采集金十数据快讯"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        try:
            url = self.config['jin10']['api_url']
            resp = self.session.get(url, timeout=self.config['jin10']['timeout'])

            # 解析 JS 文件（格式：var flash_data = [...];）
            import re
            json_match = re.search(r'var\s+flash_data\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))

                for item in data[:20]:  # 取最新 20 条
                    publish_time = item.get('time', '')
                    news_list.append(NewsItem(
                        id=self.generate_id(item.get('data', {}).get('content', ''), '金十数据', publish_time),
                        title=item.get('data', {}).get('content', '')[:100],
                        content=item.get('data', {}).get('content', ''),
                        source='金十数据',
                        department='jin10',
                        url='',
                        publish_time=publish_time,
                        keywords=[],
                        collected_at=datetime.datetime.now().isoformat()
                    ))

            print(f"  金十数据：{len(news_list)} 条")

        except Exception as e:
            print(f"  金十数据采集失败：{e}")

        return news_list

    def fetch_rss_feeds(self) -> List[NewsItem]:
        """采集 RSS 订阅源"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        for feed_url in self.config['rss_feeds']['feeds']:
            try:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:10]:
                    publish_time = entry.published if hasattr(entry, 'published') else ''
                    news_list.append(NewsItem(
                        id=self.generate_id(entry.title, 'RSS', publish_time),
                        title=entry.title,
                        content=entry.summary if hasattr(entry, 'summary') else entry.title,
                        source='RSS',
                        department='rss',
                        url=entry.link,
                        publish_time=publish_time,
                        keywords=[tag.term for tag in entry.tags] if hasattr(entry, 'tags') else [],
                        collected_at=datetime.datetime.now().isoformat()
                    ))

            except Exception as e:
                print(f"  RSS 采集失败 ({feed_url}): {e}")

        print(f"  RSS 订阅：{len(news_list)} 条")
        return news_list

    def load_local_news(self) -> List[NewsItem]:
        """加载本地手动添加的新闻"""
        news_list = []

        for file_path in self.config['local_sources']['files']:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data:
                            news_list.append(NewsItem(**item))
                    print(f"  本地新闻：{len(news_list)} 条")
                except Exception as e:
                    print(f"  本地新闻加载失败：{e}")

        return news_list

    def save_to_database(self, news_list: List[NewsItem]) -> int:
        """保存新闻到数据库"""
        if not news_list:
            return 0

        if not DUCKDB_AVAILABLE:
            print("数据库不可用，跳过保存")
            return 0

        try:
            conn = get_conn(read_only=False)
            ensure_tables(conn)

            # 转换为 DataFrame
            import pandas as pd
            df = pd.DataFrame([asdict(n) for n in news_list])

            # 去重：只插入不存在的新闻（基于 title + publish_time 去重）
            conn.register('tmp_news', df)

            result = conn.execute("""
                INSERT INTO news_items
                (symbol, source_site, source, title, content, url, publish_time, sentiment_score)
                SELECT
                    '' as symbol,
                    department as source_site,
                    source,
                    title,
                    content,
                    url,
                    publish_time,
                    sentiment_score
                FROM tmp_news
                WHERE NOT EXISTS (
                    SELECT 1 FROM news_items n
                    WHERE n.title = tmp_news.title
                    AND n.publish_time = tmp_news.publish_time
                )
            """)

            saved_count = result.rowcount
            print(f"  保存到数据库：{saved_count} 条")

            conn.close()
            return saved_count

        except Exception as e:
            print(f"  数据库保存失败：{e}")
            return 0

    def save_to_json(self, news_list: List[NewsItem], output_file: str = None):
        """保存新闻到 JSON 文件"""
        if not output_file:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"news_collection_{timestamp}.json"

        output_path = project_root / output_file

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(n) for n in news_list], f, ensure_ascii=False, indent=2)

        print(f"  保存到 JSON: {output_path}")

    def run(self, sources: List[str] = None, save_db: bool = True, save_json: bool = True) -> Dict[str, Any]:
        """运行采集器"""
        print("=" * 60)
        print("📰 优化版新闻采集器")
        print("=" * 60)
        print(f"时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        self.init_session()

        all_news = []
        stats = {}

        # 确定要采集的数据源
        if sources is None:
            sources = ['eastmoney', 'sina', 'jin10', 'rss']

        # 采集各数据源
        if 'eastmoney' in sources:
            print("📈 采集东方财富快讯...")
            news = self.fetch_eastmoney_kuaixun()
            all_news.extend(news)
            stats['eastmoney'] = len(news)

        if 'sina' in sources:
            print("📈 采集新浪财经...")
            news = self.fetch_sina_finance()
            all_news.extend(news)
            stats['sina'] = len(news)

        if 'jin10' in sources:
            print("⚡ 采集金十数据...")
            news = self.fetch_jin10_flash()
            all_news.extend(news)
            stats['jin10'] = len(news)

        if 'rss' in sources:
            print("📡 采集 RSS 订阅...")
            news = self.fetch_rss_feeds()
            all_news.extend(news)
            stats['rss'] = len(news)

        if 'local' in sources:
            print("📁 加载本地新闻...")
            news = self.load_local_news()
            all_news.extend(news)
            stats['local'] = len(news)

        print()
        print("=" * 60)
        print("采集完成")
        print("=" * 60)
        print(f"总计采集：{len(all_news)} 条")
        print(f"各来源统计：{stats}")

        # 保存
        saved_db = 0
        if save_db:
            saved_db = self.save_to_database(all_news)

        if save_json:
            self.save_to_json(all_news)

        print()
        print("=" * 60)
        print("任务完成")
        print("=" * 60)

        return {
            'total': len(all_news),
            'stats': stats,
            'saved_to_db': saved_db,
            'timestamp': datetime.datetime.now().isoformat()
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='优化版新闻采集器')
    parser.add_argument('--sources', nargs='+', default=['eastmoney', 'sina', 'jin10', 'rss'],
                        help='数据源列表：eastmoney, sina, jin10, rss, local')
    parser.add_argument('--no-db', action='store_true', help='不保存到数据库')
    parser.add_argument('--no-json', action='store_true', help='不保存到 JSON')
    parser.add_argument('--config', type=str, help='自定义配置文件路径')

    args = parser.parse_args()

    collector = OptimizedNewsCollector(config_file=args.config)
    result = collector.run(
        sources=args.sources,
        save_db=not args.no_db,
        save_json=not args.no_json
    )

    # 返回统计信息（供脚本调用）
    print()
    print(f"JSON 统计：{json.dumps(result, ensure_ascii=False)}")


if __name__ == '__main__':
    main()
