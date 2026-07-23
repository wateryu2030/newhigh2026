"""策略引擎核心功能测试。"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "strategy", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data-pipeline", "src"))


class TestAIFusionStrategy:
    """测试 AI 融合策略。"""

    def test_regime_config_ice(self):
        """冰点档位配置。"""
        from strategy_engine.ai_fusion_strategy import _regime_config

        cfg = _regime_config("冰点")
        assert cfg["min_signal_score"] == 0.52
        assert cfg["emotion_weight"] == 0.35
        assert cfg["top_n_mult"] == 0.55

    def test_regime_config_bull(self):
        """主升档位配置。"""
        from strategy_engine.ai_fusion_strategy import _regime_config

        cfg = _regime_config("主升")
        assert cfg["min_signal_score"] == 0.38
        assert cfg["fund_weight"] == 0.45

    def test_regime_config_default(self):
        """未知档位应返回默认配置。"""
        from strategy_engine.ai_fusion_strategy import _regime_config

        cfg = _regime_config("未知")
        assert cfg["min_signal_score"] == 0.4

    def test_regime_config_ebbing(self):
        """退潮档位配置。"""
        from strategy_engine.ai_fusion_strategy import _regime_config

        cfg = _regime_config("退潮")
        assert cfg["min_signal_score"] == 0.52

    def test_regime_config_climax(self):
        """高潮档位配置。"""
        from strategy_engine.ai_fusion_strategy import _regime_config

        cfg = _regime_config("高潮")
        assert cfg["min_signal_score"] == 0.45
        assert cfg["top_n_mult"] == 0.75

    def test_emotion_state_no_model(self):
        """无模型时应安全返回默认值。"""
        from strategy_engine.ai_fusion_strategy import _get_emotion_state

        result = _get_emotion_state()
        assert "state" in result
        assert "emotion_score" in result

    def test_global_fund_view(self):
        """游资视图不应抛异常。"""
        from strategy_engine.ai_fusion_strategy import _get_hotmoney_signals

        result = _get_hotmoney_signals()
        assert isinstance(result, list)

    def test_top_themes(self):
        """主线题材不应抛异常。"""
        from strategy_engine.ai_fusion_strategy import _get_main_theme

        result = _get_main_theme()
        assert isinstance(result, list)

    def test_trend_score(self):
        """趋势分应返回 0~1。"""
        from strategy_engine.ai_fusion_strategy import _trend_score_for_code

        score = _trend_score_for_code("600519")
        assert 0 <= score <= 1

    def test_sniper_codes(self):
        """狙击池不应抛异常。"""
        from strategy_engine.ai_fusion_strategy import _sniper_priority_codes

        result = _sniper_priority_codes()
        assert isinstance(result, set)

    def test_strategy_init(self):
        """策略初始化。"""
        from strategy_engine.ai_fusion_strategy import AIFusionStrategy

        strategy = AIFusionStrategy()
        assert strategy is not None

    def test_generate_signals(self):
        """generate_signals 应返回信号列表。"""
        from strategy_engine.ai_fusion_strategy import AIFusionStrategy

        strategy = AIFusionStrategy()
        signals = strategy.generate_signals(top_n=10)
        assert isinstance(signals, list)

    def test_save_signals_empty(self):
        """空信号不应写 DB。"""
        from strategy_engine.ai_fusion_strategy import AIFusionStrategy

        strategy = AIFusionStrategy()
        n = strategy.save_signals([])
        assert n == 0


class TestPriceReference:
    """测试价格参考工具。"""

    def test_get_last_price_returns_float(self):
        """get_last_price 应返回 float。"""
        from strategy_engine.price_reference import get_last_price

        price = get_last_price("600519")
        assert isinstance(price, (int, float, type(None)))

    def test_buy_target_stop(self):
        """止盈止损应返回合理范围。"""
        from strategy_engine.price_reference import buy_target_stop_from_last

        tp, sl = buy_target_stop_from_last(100.0)
        assert tp > 100.0, "target should be above entry"
        assert sl < 100.0, "stop should be below entry"
        assert tp - 100.0 > 0
        assert 100.0 - sl > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
