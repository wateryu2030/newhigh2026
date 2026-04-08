"""
信号数据服务

提供交易信号、市场信号的数据访问接口。
"""

from __future__ import annotations

from typing import List, Dict, Any
from .base import BaseService


class SignalService(BaseService):
    """信号数据服务"""

    def get_signal_count(self) -> int:
        """获取 trade_signals 表中的记录总数。"""
        row = self.fetchone("SELECT COUNT(*) FROM trade_signals")
        return row[0] if row else 0

    def get_signals(self, code: str, signal_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取指定股票的信号"""
        rows = self.fetchall(
            """
            SELECT code, signal_type, signal_score, confidence, created_at
            FROM trade_signals
            WHERE code = ? AND signal_type = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [code, signal_type, limit],
        )
        return [
            {
                "code": r[0],
                "signal_type": r[1],
                "signal_score": r[2],
                "confidence": r[3],
                "created_at": str(r[4]) if r[4] else None,
            }
            for r in rows
        ]

    def add_signal(self, code: str, signal_type: str, signal_score: float, confidence: float) -> int:
        """添加信号"""
        conn = self.connection
        if not conn:
            return 0

        try:
            conn.execute(
                """
                INSERT INTO trade_signals (code, signal_type, signal_score, confidence)
                VALUES (?, ?, ?, ?)
                """,
                [code, signal_type, signal_score, confidence],
            )
            return 1
        except (ValueError, TypeError, OSError) as e:
            print(f"⚠️  添加信号失败：{e}")
            return 0
