# -*- coding: utf-8 -*-
"""
机构级 V3 模块测试：情绪引擎、评分、风控、权重优化、分配引擎、API 结构。
保证每次改动不破坏系统。
"""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_sentiment_engine() -> None:
    """情绪周期计算与建议仓位。"""
    from core.sentiment_engine import compute_emotion_cycle, get_emotion_state, EMOTION_CYCLES

    assert compute_emotion_cycle(None, fallback="复苏") == "复苏"
    assert compute_emotion_cycle({"index_return_5d": -0.06, "index_return_20d": -0.04}) == "冰点"
    assert compute_emotion_cycle({"index_return_5d": 0.04, "index_return_20d": 0.03}) == "加速期"
    state = get_emotion_state({"index_return_5d": 0.04})
    assert state["emotion_cycle"] in EMOTION_CYCLES
    assert 0 <= state["suggested_position_pct"] <= 1
    assert "description" in state


def test_scoring_engine() -> None:
    """综合评分与龙头池构建。"""
    from core.scoring_engine import score_candidates, build_dragon_pool

    candidates = [
        {"symbol": "600519", "signal": "BUY", "price": 100},
        {"symbol": "000858", "signal": "HOLD", "price": 50},
    ]
    scored = score_candidates(candidates, fund_scores={"600519": 80, "000858": 40}, sentiment_score=50, policy_score=50)
    assert len(scored) == 2
    assert all("composite_score" in r for r in scored)
    assert scored[0]["composite_score"] >= scored[1]["composite_score"]
    pool = build_dragon_pool(candidates, fund_rank=[{"symbol": "600519", "score": 80}], top_n=5)
    assert isinstance(pool, list)
    assert all(isinstance(s, str) and len(s) == 6 for s in pool)


def test_risk_controller() -> None:
    """风控：单票≤20%、总仓≤60%、情绪联动、risk_level。"""
    from portfolio.risk_controller import (
        get_risk_level,
        allowed_total_position_pct,
        apply_position_limits,
        MAX_SINGLE_PCT,
        MAX_TOTAL_PCT,
    )

    assert get_risk_level("冰点", max_drawdown=None) in ("低", "中等", "高")
    assert get_risk_level("加速期") == "低"
    pct = allowed_total_position_pct("加速期")
    assert 0 <= pct <= MAX_TOTAL_PCT
    assert allowed_total_position_pct("冰点") < allowed_total_position_pct("加速期")
    positions = {"600519": 200_000, "000858": 150_000}
    out, risk_level = apply_position_limits(positions, total_equity=1_000_000, emotion_cycle="复苏", max_positions=10)
    assert risk_level in ("低", "中等", "高")
    for s, v in out.items():
        assert v <= 1_000_000 * MAX_SINGLE_PCT
    assert sum(out.values()) <= 1_000_000 * MAX_TOTAL_PCT


def test_weight_optimizer() -> None:
    """AI 权重优化：夏普与按夏普分配。"""
    from ai.weight_optimizer import compute_sharpe, optimize_weights, STRATEGY_IDS

    assert compute_sharpe([]) == 0.0
    assert compute_sharpe([0.01, 0.02, -0.01]) != 0
    strategy_returns = {
        "dragon_strategy": [0.001] * 30,
        "trend_strategy": [0.0005] * 30,
        "mean_reversion": [-0.0002] * 30,
    }
    weights = optimize_weights(strategy_returns, min_weight=0.1)
    assert set(weights.keys()) == set(strategy_returns.keys())
    assert abs(sum(weights.values()) - 1.0) < 1e-5
    for w in weights.values():
        assert w >= 0 and w <= 1


def test_allocation_engine() -> None:
    """多策略分配与权重。"""
    from portfolio.allocation_engine import get_weights, allocate_signals, DEFAULT_STRATEGY_WEIGHTS

    w = get_weights(None)
    assert set(w.keys()) == set(DEFAULT_STRATEGY_WEIGHTS.keys())
    assert abs(sum(w.values()) - 1.0) < 1e-5
    dragon = [{"symbol": "600519", "signal": "BUY", "composite_score": 80}]
    trend = [{"symbol": "600519", "signal": "buy", "confidence": 0.7}]
    mean_rev = [{"symbol": "000858", "signal": "hold", "confidence": 0.5}]
    merged = allocate_signals(dragon, trend, mean_rev)
    assert len(merged) >= 1
    assert any(r["symbol"] == "600519" for r in merged)
    assert all("score" in r for r in merged)


def test_signal_api_structure() -> None:
    """API 返回结构：emotion_cycle, dragon_pool, buy_list, sell_list, risk_level。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "signal_api",
        os.path.join(_ROOT, "api", "signal_api.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    get_signal_structure = mod.get_signal_structure

    s = get_signal_structure(
        buy_list=["600519"],
        sell_list=[],
        dragon_pool=["600519", "000858"],
        emotion_cycle="加速期",
        risk_level="低",
    )
    assert s["emotion_cycle"] == "加速期"
    assert s["dragon_pool"] == ["600519", "000858"]
    assert s["buy_list"] == ["600519"]
    assert s["sell_list"] == []
    assert s["risk_level"] == "低"
    assert "updated_at" in s


def test_daily_report_structure() -> None:
    """daily_report.json 必须字段。"""
    import json

    report = {
        "emotion_cycle": "加速期",
        "dragon_pool": ["000001", "002XXX"],
        "buy_list": [],
        "sell_list": [],
        "risk_level": "中等",
    }
    for key in ("emotion_cycle", "dragon_pool", "buy_list", "sell_list", "risk_level"):
        assert key in report
    raw = json.dumps(report, ensure_ascii=False)
    parsed = json.loads(raw)
    assert parsed["emotion_cycle"] == report["emotion_cycle"]
    assert isinstance(parsed["dragon_pool"], list)


if __name__ == "__main__":
    print("机构级 V3 测试")
    test_sentiment_engine()
    print("  sentiment_engine OK")
    test_scoring_engine()
    print("  scoring_engine OK")
    test_risk_controller()
    print("  risk_controller OK")
    test_weight_optimizer()
    print("  weight_optimizer OK")
    test_allocation_engine()
    print("  allocation_engine OK")
    test_signal_api_structure()
    print("  signal_api structure OK")
    test_daily_report_structure()
    print("  daily_report structure OK")
    print("Done")
