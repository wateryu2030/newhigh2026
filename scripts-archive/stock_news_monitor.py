#!/usr/bin/env python3
"""
重点股票新闻监控采集器
监控标的：002701 奥瑞金、300212 易华录、600881 亚泰集团
数据源：东方财富网、新浪财经、证券时报等
"""

import sys
import datetime
import json
import time
import hashlib
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("警告：requests 未安装")

# 重点监控股票
MONITORED_STOCKS = [
    {'code': '002701', 'name': '奥瑞金', 'full_name': '奥瑞金科技股份有限公司'},
    {'code': '300212', 'name': '易华录', 'full_name': '北京易华录信息技术股份有限公司'},
    {'code': '600881', 'name': '亚泰集团', 'full_name': '吉林亚泰 (集团) 股份有限公司'}
]

# 监控关键词
MONITOR_KEYWORDS = [
    '奥瑞金', 'ORGTECH', '红牛罐', '金属包装',
    '易华录', '数据湖', '数据要素', '智能交通', '华录集团',
    '亚泰集团', '亚泰', '吉林水泥', '东北建材'
]


class StockNewsCollector:
    """重点股票新闻采集器"""

    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        # 东方财富数据源
        self.data_sources = {
            'eastmoney_news': {
                'name': '东方财富新闻',
                'url': 'https://search.eastmoney.com/api/result/get?keyword={keyword}&pageIndex=1&pageSize=20&pageType=news',
                'type': 'api'
            },
            'eastmoney_stock_news': {
                'name': '东方财富个股新闻',
                'url': 'https://newsapi.eastmoney.com/stock/{code}.html',
                'type': 'web'
            },
            'sina_finance': {
                'name': '新浪财经',
                'url': 'https://finance.sina.com.cn/stock/rollnews.d.html',
                'type': 'web'
            }
        }

    def init_session(self):
        """初始化请求会话"""
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update(self.headers)

    def generate_id(self, title: str, source: str, publish_time: str) -> str:
        """生成新闻 ID"""
        content = f"{title}_{source}_{publish_time}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def extract_keywords(self, text: str) -> List[str]:
        """提取匹配关键词"""
        matched = []
        for kw in MONITOR_KEYWORDS:
            if kw in text:
                matched.append(kw)
        return matched[:5]

    def identify_stocks(self, text: str) -> List[Dict[str, str]]:
        """识别新闻中涉及的股票"""
        stocks = []
        for stock in MONITORED_STOCKS:
            if stock['name'] in text or stock['code'] in text or stock['full_name'] in text:
                stocks.append(stock)
        return stocks

    def fetch_eastmoney_search(self, keyword: str) -> List[Dict[str, Any]]:
        """从东方财富搜索 API 采集新闻"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        try:
            # 使用东方财富搜索接口
            url = f"https://search.eastmoney.com/api/result/get?keyword={keyword}&pageIndex=1&pageSize=20&pageType=news"

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()

            if data.get('Data' and data['Data'].get('result')):
                items = data['Data']['result']
                for item in items:
                    try:
                        title = item.get('title', '')
                        if not title:
                            continue

                        content = item.get('content', '') or item.get('digest', '')
                        url = item.get('url', '')
                        publish_time = item.get('pubTime', '')
                        source = item.get('source', '东方财富')

                        # 提取关键词和涉及的股票
                        keywords = self.extract_keywords(title + ' ' + content)
                        stocks = self.identify_stocks(title + ' ' + content)

                        if not keywords:
                            continue

                        news_item = {
                            'id': self.generate_id(title, source, publish_time),
                            'title': title,
                            'source': source,
                            'category': 'stock_news',
                            'publish_time': publish_time,
                            'content': content[:500],
                            'url': url,
                            'keywords': keywords,
                            'related_stocks': [s['code'] for s in stocks],
                            'collected_at': datetime.datetime.now().isoformat(),
                            'data_source': 'eastmoney_search'
                        }

                        news_list.append(news_item)

                    except Exception:  # pylint: disable=broad-exception-caught
                        continue

            print(f"  东方财富搜索 '{keyword}': {len(news_list)} 条相关新闻")

        except Exception as ex:  # pylint: disable=broad-exception-caught
            print(f"  东方财富搜索失败：{ex}")

        return news_list

    def fetch_eastmoney_stock_news(self, code: str) -> List[Dict[str, Any]]:
        """采集东方财富个股新闻"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        try:
            # 东方财富个股新闻 API
            url = f"https://newsapi.eastmoney.com/ajax/NewsList?callback=jQuery&symbol={code}&marketType={'sz' if code.startswith(('0', '3')) else 'sh'}&page=1&pagesize=20"

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            # 解析 JSONP
            content = response.text
            if 'jQuery' in content:
                content = content.replace('jQuery(', '').rstrip(')')

            data = json.loads(content)

            if data.get('Data'):
                for item in data['Data']:
                    try:
                        title = item.get('Title', '')
                        if not title:
                            continue

                        news_item = {
                            'id': self.generate_id(title, '东方财富', item.get('ShowTime', '')),
                            'title': title,
                            'source': '东方财富',
                            'category': 'stock_news',
                            'publish_time': item.get('ShowTime', ''),
                            'content': item.get('Content', '')[:500],
                            'url': item.get('Url', ''),
                            'keywords': self.extract_keywords(title),
                            'related_stocks': [code],
                            'collected_at': datetime.datetime.now().isoformat(),
                            'data_source': f'eastmoney_stock_{code}'
                        }

                        news_list.append(news_item)

                    except Exception:  # pylint: disable=broad-exception-caught
                        continue

            print(f"  东方财富个股新闻 {code}: {len(news_list)} 条")

        except Exception as ex:  # pylint: disable=broad-exception-caught
            print(f"  东方财富个股新闻采集失败 {code}: {ex}")

        return news_list

    def save_to_database(self, news_list: List[Dict[str, Any]]) -> int:
        """保存到数据库"""
        if not news_list:
            return 0

        try:
            import duckdb

            db_path = 'data/quant_system.duckdb'
            conn = duckdb.connect(db_path)

            saved_count = 0
            for news in news_list:
                try:
                    # 检查是否已存在
                    existing = conn.execute(
                        "SELECT id FROM news_items WHERE id = ?",
                        [news['id']]
                    ).fetchone()

                    if existing:
                        continue

                    # 插入新记录
                    conn.execute("""
                        INSERT INTO news_items
                        (id, title, source, category, publish_time, content, url, keywords, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        news['id'],
                        news['title'],
                        news['source'],
                        news['category'],
                        news['publish_time'],
                        news['content'],
                        news['url'],
                        str(news['keywords']),
                        news['collected_at']
                    ])
                    saved_count += 1

                except Exception:  # pylint: disable=broad-exception-caught
                    continue

            conn.close()
            return saved_count

        except Exception as ex:  # pylint: disable=broad-exception-caught
            print(f"保存数据库失败：{ex}")
            return 0

    def save_to_json(self, news_list: List[Dict[str, Any]], filename: str) -> str:
        """保存到 JSON 文件"""
        if not news_list:
            return ''

        output_dir = Path('data-pipeline/data/news')
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'collected_at': datetime.datetime.now().isoformat(),
                    'total_count': len(news_list),
                    'monitored_stocks': [s['code'] for s in MONITORED_STOCKS],
                    'keywords': MONITOR_KEYWORDS
                },
                'news': news_list
            }, f, ensure_ascii=False, indent=2)

        return str(output_path)

    def collect_all(self) -> Dict[str, Any]:
        """执行完整采集流程"""
        print("=" * 60)
        print("开始采集重点股票新闻")
        print("=" * 60)
        print(f"时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"监控标的：{', '.join([s['name'] for s in MONITORED_STOCKS])}")
        print()

        self.init_session()

        all_news = []

        # 1. 按关键词搜索
        print("📰 采集关键词相关新闻...")
        for keyword in ['奥瑞金', '易华录', '亚泰集团']:
            news = self.fetch_eastmoney_search(keyword)
            all_news.extend(news)
            time.sleep(0.5)  # 避免请求过快

        # 2. 采集个股新闻
        print("\n📈 采集个股新闻...")
        for stock in MONITORED_STOCKS:
            news = self.fetch_eastmoney_stock_news(stock['code'])
            all_news.extend(news)
            time.sleep(0.5)

        # 去重
        seen = set()
        unique_news = []
        for news in all_news:
            if news['id'] not in seen:
                seen.add(news['id'])
                unique_news.append(news)

        all_news = unique_news

        # 保存
        print("\n" + "=" * 60)
        print("保存数据...")

        db_count = self.save_to_database(all_news)
        json_path = self.save_to_json(all_news, f"stock_monitor_news_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        print(f"✅ 保存 {db_count} 条新闻到数据库")
        print(f"✅ 保存 JSON 文件：{json_path}")

        # 统计
        stock_news_count = {}
        for news in all_news:
            for code in news.get('related_stocks', []):
                stock_news_count[code] = stock_news_count.get(code, 0) + 1

        print("\n" + "=" * 60)
        print("采集完成")
        print("=" * 60)
        print(f"总计采集新闻：{len(all_news)} 条")
        print("按股票统计:")
        for stock in MONITORED_STOCKS:
            count = stock_news_count.get(stock['code'], 0)
            print(f"  {stock['code']} {stock['name']}: {count} 条")

        return {
            'total': len(all_news),
            'by_stock': stock_news_count,
            'json_path': json_path
        }


def main():
    """主函数"""
    collector = StockNewsCollector()
    collector.collect_all()

    print("\n💡 改进建议:")
    print("1. 可接入东方财富个股新闻 API 提高采集成功率")
    print("2. 可添加情感分析功能")
    print("3. 可设置新闻告警阈值")


if __name__ == '__main__':
    main()
