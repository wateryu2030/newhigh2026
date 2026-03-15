"""
AI 融合策略：情绪周期 + 游资席位 + 主线题材 → 交易信号与 signal_score。
signal_score = emotion_score * 0.4 + fund_score * 0.4 + trend_score * 0.2
"""

from __future__ import annotations

import os
from typing import List, Tuple

# Optional imports - handled gracefully if not available
try:
    from ai_models.emotion_cycle_model import EmotionCycleModel

    EMOTION_MODEL_AVAILABLE = True
except ImportError:
    EmotionCycleModel = None  # type: ignore
    EMOTION_MODEL_AVAILABLE = False

try:
    from data_pipeline.storage.duckdb_manager import get_conn, get_db_path, ensure_tables

    DUCKDB_MANAGER_AVAILABLE = True
except ImportError:
    get_conn = None  # type: ignore
    get_db_path = None  # type: ignore
    ensure_tables = None  # type: ignore
    DUCKDB_MANAGER_AVAILABLE = False


def _get_emotion_state() -> dict:
    """最近情绪状态与可用的情绪评分 0~1。"""
    if not EMOTION_MODEL_AVAILABLE:
        return {"state": "—", "emotion_score": 0.5, "raw": {}}

    try:
        model = EmotionCycleModel()
        latest = model.get_latest_state()
        state = (latest.get("emotion_state") or "—").strip()
        # 状态 → 情绪评分
        score_map = {"冰点": 0.2, "启动": 0.4, "主升": 0.7, "高潮": 0.85, "退潮": 0.35}
        emotion_score = score_map.get(state, 0.5)
        return {"state": state, "emotion_score": emotion_score, "raw": latest}
    except Exception:
        return {"state": "—", "emotion_score": 0.5, "raw": {}}


def _get_hotmoney_signals() -> list:
    """游资相关标的/席位信号：(code_or_seat, fund_score)。"""
    if not DUCKDB_MANAGER_AVAILABLE:
        return []

    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return []

        conn = get_conn(read_only=True)
        # top_hotmoney_seats: seat_name, win_rate, avg_return
        seats = conn.execute(
            "SELECT seat_name, win_rate, avg_return FROM top_hotmoney_seats"
        ).fetchdf()
        # hotmoney_signals: code, seat_type, win_rate
        codes = conn.execute("SELECT code, win_rate FROM hotmoney_signals").fetchdf()
        conn.close()
        out = []
        if seats is not None and not seats.empty:
            for _, r in seats.iterrows():
                wr = float(r.get("win_rate") or 0.5)
                ar = float(r.get("avg_return") or 0)
                fund_score = min(1.0, 0.5 + wr * 0.4 + min(ar * 5, 0.2))
                out.append((str(r.get("seat_name", "")), fund_score))
        if codes is not None and not codes.empty:
            for _, r in codes.iterrows():
                code = str(r.get("code", ""))
                if not code or any(x[0] == code for x in out):
                    continue
                wr = float(r.get("win_rate") or 0.5)
                out.append((code, min(1.0, 0.4 + wr * 0.5)))
        return out
    except Exception:
        return []


def _get_main_theme() -> list:
    """主线题材：[(sector, rank), ...]。"""
    if not DUCKDB_MANAGER_AVAILABLE:
        return [("全市场", 1)]

    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return [("全市场", 1)]

        conn = get_conn(read_only=True)
        df = conn.execute("SELECT sector, rank FROM main_themes ORDER BY rank LIMIT 10").fetchdf()
        conn.close()
        if df is None or df.empty:
            return [("全市场", 1)]
        return [(str(r["sector"]), int(r.get("rank", 0))) for _, r in df.iterrows()]
    except Exception:
        return [("全市场", 1)]


def _trend_score_for_code(code: str) -> float:
    """从 market_signals 或涨停/资金流取趋势分 0~1。"""
    if not DUCKDB_MANAGER_AVAILABLE:
        return 0.5

    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return 0.5

        conn = get_conn(read_only=True)
        row = conn.execute(
            "SELECT score FROM market_signals WHERE code = ? ORDER BY snapshot_time DESC LIMIT 1",
            [code],
        ).fetchone()
        conn.close()
        if row and row[0] is not None:
            return min(1.0, max(0, float(row[0]) / 100.0))
        return 0.5
    except Exception:
        return 0.5


class AIFusionStrategy:
    """融合情绪、资金、题材，生成带 signal_score 的交易信号。"""

    def __init__(self, conn=None):
        self._connection = conn

    def generate_signals(
        self,
        top_n: int = 20,
        min_signal_score: float = 0.4,
        emotion_weight: float = 0.4,
        fund_weight: float = 0.4,
        trend_weight: float = 0.2,
    ) -> List[Tuple[str, str, float, float, float, float]]:
        """
        返回：[(code, signal, confidence, target_price, stop_loss, signal_score), ...]
        """
        emotion = _get_emotion_state()
        hotmoney = _get_hotmoney_signals()
        emotion_score = emotion["emotion_score"]
        state = emotion["state"]

        # 主升期才大量出信号；其他阶段也可出但数量收紧
        if state == "主升":
            candidate_codes = set()
            for code_or_seat, _fund_s in hotmoney:
                if len(code_or_seat) == 6 and code_or_seat.isdigit():
                    candidate_codes.add(code_or_seat)

            if DUCKDB_MANAGER_AVAILABLE:
                try:
                    db_path = get_db_path()
                    if db_path and os.path.isfile(db_path):
                        conn = get_conn(read_only=True)
                        ms = conn.execute(
                            "SELECT code, score FROM market_signals "
                            "ORDER BY score DESC NULLS LAST LIMIT 200"
                        ).fetchdf()
                        conn.close()
                        if ms is not None and not ms.empty:
                            for _, r in ms.iterrows():
                                candidate_codes.add(str(r.get("code", "")))
                except Exception:
                    pass
            candidate_codes = [c for c in candidate_codes if c]
        else:
            candidate_codes = []
            for code_or_seat, _ in hotmoney:
                if len(code_or_seat) == 6 and code_or_seat.isdigit():
                    candidate_codes.append(code_or_seat)

            if not candidate_codes and DUCKDB_MANAGER_AVAILABLE:
                try:
                    db_path = get_db_path()
                    if db_path and os.path.isfile(db_path):
                        conn = get_conn(read_only=True)
                        ms = conn.execute(
                            "SELECT code FROM market_signals "
                            "ORDER BY snapshot_time DESC LIMIT 50"
                        ).fetchdf()
                        conn.close()
                        if ms is not None and not ms.empty:
                            candidate_codes = [
                                str(r.get("code", "")) for _, r in ms.iterrows() if r.get("code")
                            ]
                except Exception:
                    pass

        fund_map = {code: s for code, s in hotmoney if len(code) == 6 and code.isdigit()}
        scored = []
        for code in candidate_codes:
            fund_score = fund_map.get(code, 0.5)
            trend_score = _trend_score_for_code(code)
            signal_score = (
                emotion_score * emotion_weight
                + fund_score * fund_weight
                + trend_score * trend_weight
            )
            if signal_score < min_signal_score:
                continue
            confidence = min(0.99, signal_score)
            scored.append((code, "BUY", confidence, 0.0, 0.0, signal_score))

        scored.sort(key=lambda x: -x[5])
        return scored[:top_n]

    def save_signals(self, signals: List[Tuple[str, str, float, float, float, float]]) -> int:
        """写入 trade_signals 表（含 signal_score）。"""
        if not signals:
            return 0

        if not DUCKDB_MANAGER_AVAILABLE:
            return 0

        try:
            conn = get_conn(read_only=False)
            ensure_tables(conn)
            conn.execute("DELETE FROM trade_signals")
            for code, signal, confidence, target_price, stop_loss, signal_score in signals:
                conn.execute(
                    """INSERT INTO trade_signals
                       (code, signal, confidence, target_price, stop_loss, strategy_id, signal_score)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    [code, signal, confidence, target_price, stop_loss, "ai_fusion", signal_score],
                )
            n = len(signals)
            conn.close()
            return n
        except Exception:
            return 0


def run_ai_fusion() -> int:
    """入口：生成并保存融合信号。"""
    strategy = AIFusionStrategy()
    signals = strategy.generate_signals()
    return strategy.save_signals(signals)
