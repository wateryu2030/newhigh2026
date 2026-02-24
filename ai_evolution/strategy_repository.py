# -*- coding: utf-8 -*-
"""
策略仓库：保存最佳策略、历史策略及参数。存储使用 DuckDB 或 JSON。
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSON_DIR = os.path.join(_ROOT, "output", "ai_evolution")
DEFAULT_DUCKDB_PATH = os.path.join(_ROOT, "data", "evolution_strategies.duckdb")


class StrategyRepository:
    """存储与读取进化产生的策略（优先 DuckDB，可选 JSON 备份）。"""

    def __init__(
        self,
        use_duckdb: bool = True,
        duckdb_path: Optional[str] = None,
        json_dir: Optional[str] = None,
    ) -> None:
        self.use_duckdb = use_duckdb
        self.duckdb_path = duckdb_path or DEFAULT_DUCKDB_PATH
        self.json_dir = json_dir or DEFAULT_JSON_DIR
        os.makedirs(self.json_dir, exist_ok=True)
        if self.use_duckdb:
            self._ensure_schema()

    def _ensure_schema(self) -> None:
        """确保 DuckDB 表存在。"""
        try:
            import duckdb
            os.makedirs(os.path.dirname(self.duckdb_path), exist_ok=True)
            conn = duckdb.connect(self.duckdb_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_strategies (
                    id INTEGER PRIMARY KEY,
                    created_at VARCHAR,
                    strategy_id VARCHAR,
                    strategy_type VARCHAR,
                    params VARCHAR,
                    score DOUBLE,
                    return_rate DOUBLE,
                    sharpe DOUBLE,
                    drawdown DOUBLE,
                    meta VARCHAR
                )
            """)
            conn.close()
        except Exception as e:
            logger.warning("DuckDB schema init failed, fallback to JSON only: %s", e)
            self.use_duckdb = False

    def save(
        self,
        strategy_id: str,
        strategy_type: str,
        params: Dict[str, Any],
        score: float,
        return_rate: float = 0.0,
        sharpe: float = 0.0,
        drawdown: float = 0.0,
        meta: Optional[Dict[str, Any]] = None,
    ) -> int:
        """保存一条策略记录，返回自增 id。"""
        created = datetime.now().isoformat()[:19]
        params_str = json.dumps(params, ensure_ascii=False)
        meta_str = json.dumps(meta or {}, ensure_ascii=False) if meta else "{}"

        if self.use_duckdb:
            try:
                import duckdb
                conn = duckdb.connect(self.duckdb_path)
                r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM evolution_strategies").fetchone()
                next_id = int(r[0]) if r else 1
                conn.execute(
                    """
                    INSERT INTO evolution_strategies
                    (id, created_at, strategy_id, strategy_type, params, score, return_rate, sharpe, drawdown, meta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [next_id, created, strategy_id, strategy_type, params_str, score, return_rate, sharpe, drawdown, meta_str],
                )
                conn.close()
                logger.info("Saved strategy id=%s to DuckDB", next_id)
                return int(next_id)
            except Exception as e:
                logger.warning("DuckDB save failed: %s", e)

        # JSON 追加
        record = {
            "created_at": created,
            "strategy_id": strategy_id,
            "strategy_type": strategy_type,
            "params": params,
            "score": score,
            "return_rate": return_rate,
            "sharpe": sharpe,
            "drawdown": drawdown,
            "meta": meta or {},
        }
        path = os.path.join(self.json_dir, "strategies.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return -1

    def get_best(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """返回评分最高的 top_n 条策略。"""
        if self.use_duckdb:
            try:
                import duckdb
                conn = duckdb.connect(self.duckdb_path, read_only=True)
                rows = conn.execute("""
                    SELECT id, created_at, strategy_id, strategy_type, params, score, return_rate, sharpe, drawdown, meta
                    FROM evolution_strategies ORDER BY score DESC LIMIT ?
                """, [top_n]).fetchall()
                conn.close()
                return [
                    {
                        "id": r[0],
                        "created_at": r[1],
                        "strategy_id": r[2],
                        "strategy_type": r[3],
                        "params": json.loads(r[4]) if isinstance(r[4], str) else r[4],
                        "score": r[5],
                        "return_rate": r[6],
                        "sharpe": r[7],
                        "drawdown": r[8],
                        "meta": json.loads(r[9]) if isinstance(r[9], str) else {},
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.warning("DuckDB get_best failed: %s", e)

        # JSON 行文件
        path = os.path.join(self.json_dir, "strategies.jsonl")
        if not os.path.exists(path):
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
        records.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
        return records[:top_n]

    def list_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """列出最近 limit 条历史记录。"""
        best = self.get_best(top_n=limit)
        return best
