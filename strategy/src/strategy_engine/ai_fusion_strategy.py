"""
AI 融合策略：情绪周期 + 游资席位 + 主线题材 → 交易信号与 signal_score。
signal_score = emotion_score * 0.4 + fund_score * 0.4 + trend_score * 0.2
"""

from __future__ import annotations

import os
from typing import List, Tuple

from strategy_engine.price_reference import buy_target_stop_from_last, get_last_price

# Optional imports - handled gracefully if not available
try:
    from ai_models.emotion_cycle_model import EmotionCycleModel

    EMOTION_MODEL_AVAILABLE = True
except ImportError:
    EmotionCycleModel = None  # type: ignore
    EMOTION_MODEL_AVAILABLE = False

try:
    from lib.database import get_connection, get_db_path, ensure_core_tables

    LIB_DATABASE_AVAILABLE = True
    DUCKDB_MANAGER_AVAILABLE = True  # 别名，保持向后兼容
    GET_CONN = get_connection  # pylint: disable=invalid-name  # Alias for backward compatibility
except ImportError:
    get_connection = None  # type: ignore
    get_db_path = None  # type: ignore
    ensure_core_tables = None  # type: ignore
    LIB_DATABASE_AVAILABLE = False
    DUCKDB_MANAGER_AVAILABLE = False
    GET_CONN = None  # type: ignore


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
    except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
        return {"state": "—", "emotion_score": 0.5, "raw": {}}


def _get_hotmoney_signals() -> list:
    """游资相关标的/席位信号：(code_or_seat, fund_score)。"""
    if not LIB_DATABASE_AVAILABLE:
        return []

    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return []

        conn = get_connection(read_only=True)
        if not conn:
            return []
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
    except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
        return []


def _get_main_theme() -> list:
    """主线题材：[(sector, rank), ...]。"""
    if not DUCKDB_MANAGER_AVAILABLE:
        return [("全市场", 1)]

    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return [("全市场", 1)]

        conn = GET_CONN(read_only=True)
        df = conn.execute("SELECT sector, rank FROM main_themes ORDER BY rank LIMIT 10").fetchdf()
        conn.close()
        if df is None or df.empty:
            return [("全市场", 1)]
        return [(str(r["sector"]), int(r.get("rank", 0))) for _, r in df.iterrows()]
    except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
        return [("全市场", 1)]


def _trend_score_for_code(code: str) -> float:
    """从 market_signals 或涨停/资金流取趋势分 0~1。"""
    if not DUCKDB_MANAGER_AVAILABLE:
        return 0.5

    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return 0.5

        conn = GET_CONN(read_only=True)
        row = conn.execute(
            "SELECT score FROM market_signals WHERE code = ? ORDER BY snapshot_time DESC LIMIT 1",
            [code],
        ).fetchone()
        conn.close()
        if row and row[0] is not None:
            return min(1.0, max(0, float(row[0]) / 100.0))
        return 0.5
    except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
        return 0.5


def _regime_config(state: str) -> dict:
    """
    情绪档位 → 最低信号分、因子权重、输出条数系数。
    冰点/退潮抬高门槛、略增技术权；主升更偏资金与数量。
    """
    base = {
        "min_signal_score": 0.4,
        "emotion_weight": 0.4,
        "fund_weight": 0.4,
        "trend_weight": 0.2,
        "top_n_mult": 1.0,
    }
    if state in ("冰点", "退潮"):
        base.update(
            min_signal_score=0.52,
            emotion_weight=0.35,
            fund_weight=0.35,
            trend_weight=0.30,
            top_n_mult=0.55,
        )
    elif state == "高潮":
        base.update(
            min_signal_score=0.45,
            emotion_weight=0.45,
            fund_weight=0.35,
            trend_weight=0.20,
            top_n_mult=0.75,
        )
    elif state == "主升":
        base.update(
            min_signal_score=0.38,
            emotion_weight=0.35,
            fund_weight=0.45,
            trend_weight=0.20,
            top_n_mult=1.0,
        )
    return base


def _sniper_priority_codes() -> set:
    """游资狙击池高分标的，用于融合加分。"""
    if not DUCKDB_MANAGER_AVAILABLE:
        return set()
    try:
        db_path = get_db_path()
        if not db_path or not os.path.isfile(db_path):
            return set()
        conn = GET_CONN(read_only=True)
        df = conn.execute(
            "SELECT code FROM sniper_candidates ORDER BY sniper_score DESC NULLS LAST LIMIT 100"
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return set()
        return {
            str(r.get("code", "") or "")
            for _, r in df.iterrows()
            if r.get("code")
        }
    except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
        return set()


class AIFusionStrategy:
    """融合情绪、资金、题材，生成带 signal_score 的交易信号。"""

    def __init__(self, conn=None):
        self._connection = conn

    def generate_signals(  # pylint: disable=too-many-positional-arguments
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

        if os.environ.get("AI_FUSION_REGIME", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        ):
            rc = _regime_config(state)
            min_signal_score = rc["min_signal_score"]
            emotion_weight = rc["emotion_weight"]
            fund_weight = rc["fund_weight"]
            trend_weight = rc["trend_weight"]
            top_n = max(5, int(top_n * rc["top_n_mult"]))

        sniper_codes = _sniper_priority_codes()
        try:
            sniper_boost = float(os.environ.get("AI_FUSION_SNIPER_BOOST", "0.07") or 0.07)
        except ValueError:
            sniper_boost = 0.07
        sniper_boost = max(0.0, min(0.2, sniper_boost))

        # 主升期才大量出信号；其他阶段也可出但数量收紧
        if state == "主升":
            candidate_codes = self._get_candidate_codes_bullish(hotmoney)
        else:
            candidate_codes = self._get_candidate_codes_normal(hotmoney)

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
            if code in sniper_codes:
                signal_score = min(0.99, signal_score + sniper_boost)
            if signal_score < min_signal_score:
                continue
            confidence = min(0.99, signal_score)
            last = get_last_price(code)
            tp, sl = buy_target_stop_from_last(last or 0.0)
            scored.append((code, "BUY", confidence, tp, sl, signal_score))

        scored.sort(key=lambda x: -x[5])
        return scored[:top_n]

    def _get_candidate_codes_bullish(self, hotmoney: list) -> List[str]:
        """主升期获取候选标的（宽松筛选）。"""
        candidate_codes = set()
        for code_or_seat, _fund_s in hotmoney:
            if len(code_or_seat) == 6 and code_or_seat.isdigit():
                candidate_codes.add(code_or_seat)

        if not DUCKDB_MANAGER_AVAILABLE:
            return [c for c in candidate_codes if c]

        try:
            db_path = get_db_path()
            if not db_path or not os.path.isfile(db_path):
                return [c for c in candidate_codes if c]

            conn = GET_CONN(read_only=True)
            ms = conn.execute(
                "SELECT code, score FROM market_signals ORDER BY score DESC NULLS LAST LIMIT 200"
            ).fetchdf()
            conn.close()

            if ms is not None and not ms.empty:
                for _, r in ms.iterrows():
                    candidate_codes.add(str(r.get("code", "")))
        except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
            pass

        return [c for c in candidate_codes if c]

    def _get_candidate_codes_normal(self, hotmoney: list) -> List[str]:
        """非主升期获取候选标的（收紧筛选）。"""
        candidate_codes = []
        for code_or_seat, _ in hotmoney:
            if len(code_or_seat) == 6 and code_or_seat.isdigit():
                candidate_codes.append(code_or_seat)

        if candidate_codes or not DUCKDB_MANAGER_AVAILABLE:
            return candidate_codes

        try:
            db_path = get_db_path()
            if not db_path or not os.path.isfile(db_path):
                return candidate_codes

            conn = GET_CONN(read_only=True)
            ms = conn.execute(
                "SELECT code FROM market_signals ORDER BY snapshot_time DESC LIMIT 50"
            ).fetchdf()
            conn.close()

            if ms is not None and not ms.empty:
                candidate_codes = [
                    str(r.get("code", "")) for _, r in ms.iterrows() if r.get("code")
                ]
        except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
            pass

        return candidate_codes

    def save_signals(self, signals: List[Tuple[str, str, float, float, float, float]]) -> int:
        """写入 trade_signals 表（含 signal_score）。"""
        if not signals:
            return 0

        if not DUCKDB_MANAGER_AVAILABLE:
            return 0

        try:
            conn = GET_CONN(read_only=False)
            ensure_core_tables(conn)
            # 仅清空本策略，保留 shareholder_chip / market_agg 等其它 strategy_id
            conn.execute("DELETE FROM trade_signals WHERE strategy_id = ?", ["ai_fusion"])
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
        except Exception:  # pylint: disable=broad-exception-caught  # strategy fusion logic
            return 0


def run_ai_fusion() -> int:
    """入口：生成并保存融合信号。"""
    strategy = AIFusionStrategy()
    signals = strategy.generate_signals()
    return strategy.save_signals(signals)
