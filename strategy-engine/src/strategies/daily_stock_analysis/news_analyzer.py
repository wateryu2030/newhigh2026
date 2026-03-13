"""
新闻分析模块
负责获取和分析新闻数据
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .config import DailyStockConfig


class NewsAnalyzer:
    """新闻分析器"""
    
    def __init__(self, config: DailyStockConfig):
        self.config = config
        self.logger = logging.getLogger(f"daily_stock_analysis.news_analyzer")
        
        # 新闻源映射
        self.news_source_handlers = {
            "xinhua": self._fetch_from_xinhua,
            "caixin": self._fetch_from_caixin,
            "government": self._fetch_from_government,
        }
    
    async def fetch_news(self, markets: List[str]) -> Dict[str, Any]:
        """
        获取新闻数据
        
        Args:
            markets: 市场列表
            
        Returns:
            新闻数据字典
        """
        self.logger.info(f"开始获取新闻数据: markets={markets}")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "markets": markets,
            "news_sources_used": self.config.news_sources,
            "articles": [],
            "sentiment_analysis": {},
            "status": "success"
        }
        
        try:
            # 从每个新闻源获取新闻
            all_articles = []
            
            for source in self.config.news_sources:
                if source in self.news_source_handlers:
                    try:
                        self.logger.debug(f"从 {source} 获取新闻")
                        articles = await self.news_source_handlers[source](markets)
                        all_articles.extend(articles)
                        self.logger.info(f"从 {source} 获取到 {len(articles)} 条新闻")
                    except Exception as e:
                        self.logger.warning(f"从 {source} 获取新闻失败: {e}")
            
            # 分析新闻情感
            results["articles"] = all_articles
            results["article_count"] = len(all_articles)
            
            if all_articles:
                sentiment_results = await self.analyze_sentiment(all_articles)
                results["sentiment_analysis"] = sentiment_results
            
            self.logger.info(f"新闻获取完成，共获取 {len(all_articles)} 条新闻")
            return results
            
        except Exception as e:
            self.logger.error(f"获取新闻数据失败: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)
            return results
    
    async def _fetch_from_xinhua(self, markets: List[str]) -> List[Dict[str, Any]]:
        """从新华社获取新闻（模拟）"""
        
        await asyncio.sleep(0.2)
        
        articles = []
        topics = ["经济政策", "金融市场", "宏观经济", "国际贸易", "科技创新"]
        
        for i in range(5):  # 模拟5条新闻
            articles.append({
                "source": "xinhua",
                "title": f"新华社：{topics[i % len(topics)]}最新动态",
                "content": f"这是关于{topics[i % len(topics)]}的新闻报道内容...",
                "url": f"https://xinhua.com/news/{datetime.now().strftime('%Y%m%d')}_{i}",
                "publish_time": (datetime.now() - timedelta(hours=i)).isoformat(),
                "related_markets": markets[:2] if markets else ["A"],
                "keywords": [topics[i % len(topics)], "经济", "政策"],
                "category": "财经"
            })
        
        return articles
    
    async def _fetch_from_caixin(self, markets: List[str]) -> List[Dict[str, Any]]:
        """从财新网获取新闻（模拟）"""
        
        await asyncio.sleep(0.15)
        
        articles = []
        topics = ["股市分析", "公司财报", "行业趋势", "投资策略", "市场展望"]
        
        for i in range(5):
            articles.append({
                "source": "caixin",
                "title": f"财新网：{topics[i % len(topics)]}深度报道",
                "content": f"财新网对{topic}进行了深入分析...",
                "url": f"https://caixin.com/article/{datetime.now().strftime('%Y%m%d')}_{i}",
                "publish_time": (datetime.now() - timedelta(hours=i*2)).isoformat(),
                "related_markets": markets,
                "keywords": [topics[i % len(topics)], "分析", "深度"],
                "category": "深度分析"
            })
        
        return articles
    
    async def _fetch_from_government(self, markets: List[str]) -> List[Dict[str, Any]]:
        """从政府网站获取新闻（模拟）"""
        
        await asyncio.sleep(0.25)
        
        articles = []
        departments = ["国务院", "发改委", "证监会", "央行", "财政部"]
        
        for i in range(3):
            articles.append({
                "source": "government",
                "title": f"{departments[i % len(departments)]}发布重要政策通知",
                "content": f"{departments[i % len(departments)]}发布了关于金融市场的重要政策...",
                "url": f"https://gov.cn/policy/{datetime.now().strftime('%Y%m%d')}_{i}",
                "publish_time": (datetime.now() - timedelta(days=i)).isoformat(),
                "related_markets": ["A"],  # 政府政策主要影响A股
                "keywords": ["政策", departments[i % len(departments)], "通知"],
                "category": "政策法规"
            })
        
        return articles
    
    async def analyze_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析新闻情感（模拟）"""
        
        await asyncio.sleep(0.1)
        
        if not articles:
            return {"overall_sentiment": "neutral", "score": 0.0, "details": {}}
        
        # 模拟情感分析
        positive_keywords = ["增长", "利好", "上涨", "积极", "优化", "创新", "发展"]
        negative_keywords = ["下跌", "风险", "挑战", "压力", "下滑", "困难", "调整"]
        
        sentiment_scores = []
        article_sentiments = []
        
        for article in articles:
            content = f"{article.get('title', '')} {article.get('content', '')}"
            
            # 简单关键词分析
            positive_count = sum(1 for keyword in positive_keywords if keyword in content)
            negative_count = sum(1 for keyword in negative_keywords if keyword in content)
            
            if positive_count > negative_count:
                sentiment = "positive"
                score = 0.5 + (positive_count - negative_count) * 0.1
            elif negative_count > positive_count:
                sentiment = "negative"
                score = -0.5 - (negative_count - positive_count) * 0.1
            else:
                sentiment = "neutral"
                score = 0.0
            
            article_sentiments.append({
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "sentiment": sentiment,
                "score": min(max(score, -1.0), 1.0),
                "positive_keywords": positive_count,
                "negative_keywords": negative_count
            })
            sentiment_scores.append(score)
        
        # 计算总体情感
        if sentiment_scores:
            avg_score = sum(sentiment_scores) / len(sentiment_scores)
            if avg_score > 0.2:
                overall_sentiment = "positive"
            elif avg_score < -0.2:
                overall_sentiment = "negative"
            else:
                overall_sentiment = "neutral"
        else:
            avg_score = 0.0
            overall_sentiment = "neutral"
        
        return {
            "overall_sentiment": overall_sentiment,
            "average_score": avg_score,
            "article_count": len(articles),
            "positive_count": sum(1 for a in article_sentiments if a["sentiment"] == "positive"),
            "negative_count": sum(1 for a in article_sentiments if a["sentiment"] == "negative"),
            "neutral_count": sum(1 for a in article_sentiments if a["sentiment"] == "neutral"),
            "article_details": article_sentiments
        }
    
    async def filter_news_by_market(self, articles: List[Dict[str, Any]], market: str) -> List[Dict[str, Any]]:
        """按市场过滤新闻"""
        
        filtered = []
        for article in articles:
            related_markets = article.get("related_markets", [])
            if market in related_markets or not related_markets:
                filtered.append(article)
        
        return filtered