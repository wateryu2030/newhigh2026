"""
新闻数据服务

提供新闻相关的数据访问接口。
"""

from __future__ import annotations

from typing import List, Dict
from .base import BaseService


class NewsService(BaseService):
    """新闻数据服务"""

    def get_latest_news(self, limit: int = 20) -> List[Dict]:
        """获取最新新闻"""
        rows = self.fetchall(f"""
            SELECT id, title, content, source_site, publish_time, sentiment_score, sentiment_label, url
            FROM news_items
            ORDER BY publish_time DESC
            LIMIT {limit}
        """)
        return [
            {
                "id": r[0],
                "title": r[1],
                "content": r[2],
                "source": r[3],
                "publish_time": r[4],
                "sentiment_score": r[5],
                "sentiment_label": r[6],
                "url": r[7],
            }
            for r in rows
        ]

    def get_news_count(self) -> int:
        """获取新闻总数"""
        row = self.fetchone("SELECT COUNT(*) FROM news_items")
        return row[0] if row else 0

    def get_news_sentiment_stats(self) -> Dict:
        """获取情感统计"""
        row = self.fetchone("""
            SELECT
                COUNT(*) as total,
                AVG(sentiment_score) as avg_sentiment,
                SUM(CASE WHEN sentiment_score > 0.5 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN sentiment_score < 0.3 THEN 1 ELSE 0 END) as negative
            FROM news_items
            WHERE sentiment_score IS NOT NULL
        """)
        if not row:
            return {"total": 0, "avg_sentiment": 0, "positive": 0, "negative": 0}

        return {
            "total": row[0],
            "avg_sentiment": row[1] or 0,
            "positive": row[2] or 0,
            "negative": row[3] or 0,
        }

    def insert_news(self, news_items: List[Dict]) -> int:
        """
        批量插入新闻

        Args:
            news_items: 新闻列表

        Returns:
            插入的新闻数量
        """
        conn = self.connection
        if not conn:
            return 0

        count = 0
        for item in news_items:
            try:
                conn.execute("""
                    INSERT INTO news_items (title, content, source_site, publish_time, sentiment_score, sentiment_label, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    item.get("title"),
                    item.get("content"),
                    item.get("source_site"),
                    item.get("publish_time"),
                    item.get("sentiment_score"),
                    item.get("sentiment_label"),
                    item.get("url"),
                ])
                count += 1
            except (ValueError, TypeError, OSError) as e:
                print(f"⚠️  插入新闻失败：{e}")

        return count
