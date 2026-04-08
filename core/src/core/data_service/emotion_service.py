"""
情绪数据服务

提供市场情绪周期的数据访问接口。
"""

from __future__ import annotations

from typing import List, Dict, Optional
from .base import BaseService


class EmotionService(BaseService):
    """情绪数据服务"""

    def get_latest_emotion(self) -> Optional[Dict]:
        """获取最新情绪状态"""
        row = self.fetchone("""
            SELECT trade_date, emotion_state, snapshot_time, limitup_count, max_height, market_volume
            FROM market_emotion
            ORDER BY trade_date DESC
            LIMIT 1
        """)
        if not row:
            return None

        return {
            "trade_date": row[0],
            "emotion_state": row[1],
            "snapshot_time": row[2],
            "limit_up_count": row[3],
            "max_height": row[4],
            "total_volume": row[5],
        }

    def get_emotion_history(self, days: int = 30) -> List[Dict]:
        """获取历史情绪数据"""
        rows = self.fetchall(f"""
            SELECT trade_date, emotion_state, limit_up_count, max_height
            FROM market_emotion
            ORDER BY trade_date DESC
            LIMIT {days}
        """)

        return [
            {
                "trade_date": r[0],
                "emotion_state": r[1],
                "limit_up_count": r[2],
                "max_height": r[3],
            }
            for r in rows
        ]

    def update_emotion_state(  # pylint: disable=too-many-positional-arguments  # Macro-level parameters needed for emotion state tracking
        self,
        trade_date: str,
        emotion_state: str,
        limit_up_count: int,
        max_height: int,
        total_volume: float,
    ) -> bool:
        """
        更新情绪状态

        Args:
            trade_date: 交易日期
            emotion_state: 情绪状态
            limit_up_count: 涨停数量
            max_height: 连板高度
            total_volume: 总成交额

        Returns:
            是否成功
        """
        conn = self.connection
        if not conn:
            return False

        try:
            conn.execute("""
                INSERT OR REPLACE INTO market_emotion
                (trade_date, emotion_state, limit_up_count, max_height, total_volume)
                VALUES (?, ?, ?, ?, ?)
            """, [trade_date, emotion_state, limit_up_count, max_height, total_volume])
            return True
        except (ValueError, TypeError, OSError) as e:
            print(f"⚠️  更新情绪状态失败：{e}")
            return False

    def get_emotion_state_map(self) -> Dict[str, float]:
        """
        获取情绪状态评分映射

        Returns:
            状态 -> 分数 的字典
        """
        return {
            "冰点": 0.2,
            "启动": 0.4,
            "主升": 0.7,
            "高潮": 0.85,
            "退潮": 0.35,
        }

    def state_to_score(self, state: str) -> float:
        """
        将情绪状态转换为分数

        Args:
            state: 情绪状态

        Returns:
            分数 (0-1)
        """
        score_map = self.get_emotion_state_map()
        return score_map.get(state, 0.5)
