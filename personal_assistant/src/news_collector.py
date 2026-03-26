#!/usr/bin/env python3
"""
新闻采集模块 - 采集和解析财经新闻
数据源：财新、东方财富、同花顺等
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import duckdb

# 添加项目路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data-pipeline/src"))

class NewsCollector:
    """新闻采集器"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(ROOT, "data", "quant_system.duckdb")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_caijin_news(self, days_back: int = 3) -> List[Dict]:
        """
        采集财新新闻

        Args:
            days_back: 回溯天数

        Returns:
            新闻列表
        """
        print(f"  采集财新新闻（近{days_back}天）...", end="")

        try:
            # 财新 API（需要 Tushare Pro 或付费）
            # 这里使用简化版本，实际应该调用财新 API

            # 临时方案：从数据库读取已有新闻
            if os.path.exists(self.db_path):
                conn = duckdb.connect(self.db_path)

                query = """
                SELECT title, content, publish_time, url
                FROM news_items
                WHERE publish_time >= ?
                ORDER BY publish_time DESC
                LIMIT 50
                """

                days_ago = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                news_list = conn.execute(query, [days_ago]).fetchall()
                conn.close()

                print(f" ✅ 获取 {len(news_list)} 条")

                return [
                    {
                        "title": row[0],
                        "content": row[1],
                        "publish_time": row[2],
                        "url": row[3],
                        "source": "财新"
                    }
                    for row in news_list
                ]

            print(" ⚠️ 数据库不存在")
            return []

        except Exception as e:
            print(f" ❌ 失败：{e}")
            return []

    def fetch_dongfangcai_news(self, days_back: int = 3) -> List[Dict]:
        """采集东方财富新闻"""
        print(f"  采集东方财富新闻...", end="")

        try:
            # 东方财富 API
            url = "https://api.eastmoney.com/v1/news/list"
            params = {
                "type": "cj",
                "page": 1,
                "ps": 50
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                news_list = data.get("data", [])

                print(f" ✅ 获取 {len(news_list)} 条")

                return [
                    {
                        "title": news.get("Title", ""),
                        "content": news.get("Content", ""),
                        "publish_time": news.get("CreateTime", ""),
                        "url": news.get("Url", ""),
                        "source": "东方财富"
                    }
                    for news in news_list[:30]
                ]

            print(" ❌ API 请求失败")
            return []

        except Exception as e:
            print(f" ❌ 失败：{e}")
            return []

    def extract_stock_mentions(self, news_list: List[Dict]) -> Dict[str, List[Dict]]:
        """
        提取新闻中提到的股票

        Returns:
            {股票代码：相关新闻列表}
        """
        print("  提取股票提及...", end="")

        # 加载股票列表
        stock_names = self._load_stock_names()

        stock_news = {}

        for news in news_list:
            title = news.get("title", "")
            content = news.get("content", "")
            text = f"{title} {content}"

            # 查找股票名称
            for code, name in stock_names.items():
                if name in text:
                    if code not in stock_news:
                        stock_news[code] = []

                    stock_news[code].append({
                        "title": title,
                        "content": content[:200],  # 截取前 200 字
                        "publish_time": news.get("publish_time"),
                        "url": news.get("url"),
                        "source": news.get("source")
                    })

        print(f" ✅ 覆盖 {len(stock_news)} 只股票")
        return stock_news

    def _load_stock_names(self) -> Dict[str, str]:
        """加载股票代码和名称映射"""
        if not os.path.exists(self.db_path):
            return {}

        try:
            conn = duckdb.connect(self.db_path)
            stocks = conn.execute("SELECT code, name FROM stocks").fetchall()
            conn.close()

            return {code: name for code, name in stocks if name}
        except:
            return {}

    def analyze_news_sentiment(self, stock_news: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        分析新闻情绪

        Returns:
            {股票代码：{positive: 正面数量，negative: 负面数量，neutral: 中性数量，score: 情绪分数}}
        """
        print("  分析新闻情绪...", end="")

        # 简单关键词分析（应该用 AI 分析）
        positive_words = ["增长", "突破", "利好", "上涨", "盈利", "超预期", "签约", "中标"]
        negative_words = ["下跌", "亏损", "风险", "下滑", "违规", "处罚", "减持", "暴雷"]

        sentiment_results = {}

        for code, news_list in stock_news.items():
            positive_count = 0
            negative_count = 0

            for news in news_list:
                text = news.get("title", "") + news.get("content", "")

                for word in positive_words:
                    if word in text:
                        positive_count += 1

                for word in negative_words:
                    if word in text:
                        negative_count += 1

            total = positive_count + negative_count
            score = (positive_count - negative_count) / max(total, 1)

            sentiment_results[code] = {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": len(news_list) - positive_count - negative_count,
                "score": score,
                "news_count": len(news_list)
            }

        print(f" ✅ 分析完成")
        return sentiment_results


def test_news_collector():
    """测试新闻采集"""
    print("=== 测试新闻采集 ===")

    collector = NewsCollector()

    # 采集新闻
    caijin_news = collector.fetch_caijin_news(days_back=3)
    dongfang_news = collector.fetch_dongfangcai_news(days_back=3)

    all_news = caijin_news + dongfang_news

    if all_news:
        # 提取股票提及
        stock_news = collector.extract_stock_mentions(all_news)

        # 分析情绪
        sentiment = collector.analyze_news_sentiment(stock_news)

        print(f"\n情绪分析结果:")
        for code, data in list(sentiment.items())[:5]:
            print(f"  {code}: 正面={data['positive']}, 负面={data['negative']}, 分数={data['score']:.2f}")

    return all_news


if __name__ == "__main__":
    test_news_collector()
