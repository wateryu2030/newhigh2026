"""
股票数据服务

提供股票相关的数据访问接口。
"""

from __future__ import annotations

from typing import List, Dict, Optional
from .base import BaseService


class StockService(BaseService):
    """股票数据服务"""

    def get_all_stocks(self) -> List[Dict]:
        """获取所有股票"""
        rows = self.fetchall("""
            SELECT code, name, sector
            FROM a_stock_basic
            ORDER BY code
        """)
        return [
            {"code": r[0], "name": r[1], "sector": r[2]}
            for r in rows
        ]

    def get_stock_by_code(self, code: str) -> Optional[Dict]:
        """根据代码获取股票"""
        row = self.fetchone("""
            SELECT code, name, sector
            FROM a_stock_basic
            WHERE code = ?
        """, [code])
        if not row:
            return None
        return {"code": row[0], "name": row[1], "sector": row[2]}

    def get_stock_count(self) -> int:
        """获取股票总数"""
        row = self.fetchone("SELECT COUNT(*) FROM a_stock_basic")
        return row[0] if row else 0

    def update_stocks(self, stocks: List[Dict]) -> int:
        """
        批量更新股票信息

        Args:
            stocks: 股票列表 [{"code": "...", "name": "...", "sector": "..."}, ...]

        Returns:
            更新的股票数量
        """
        conn = self.connection
        if not conn:
            return 0

        count = 0
        for stock in stocks:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO a_stock_basic (code, name, sector)
                    VALUES (?, ?, ?)
                """, [
                    stock.get("code"),
                    stock.get("name"),
                    stock.get("sector"),
                ])
                count += 1
            except (ValueError, TypeError, OSError) as e:
                print(f"⚠️  更新股票 {stock.get('code')} 失败：{e}")

        return count
