"""将 market_signals 聚合为 trade_signals（code, signal, confidence, target_price, stop_loss）。"""
from __future__ import annotations

def aggregate_market_signals_to_trade_signals(
    market_signals: list[dict],
    top_n: int = 20,
    min_score: float = 50.0,
) -> list[tuple[str, str, float, float, float]]:
    """
    market_signals: [{"code", "signal_type", "score"}, ...]
    返回: [(code, signal, confidence, target_price, stop_loss), ...]
    """
    from core import Signal
    out = []
    sorted_s = sorted(
        [s for s in market_signals if float(s.get("score") or 0) >= min_score],
        key=lambda x: -float(x.get("score") or 0),
    )
    for s in sorted_s[:top_n]:
        code = str(s.get("code", ""))
        if not code:
            continue
        score = float(s.get("score") or 0)
        confidence = min(0.99, score / 100.0)
        # 占位：target/stop 由后续策略或风控填
        target_price = 0.0
        stop_loss = 0.0
        out.append((code, Signal.BUY.value, confidence, target_price, stop_loss))
    return out
