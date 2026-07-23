"""风控引擎核心功能测试。"""

import pytest
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "risk-engine", "src"))


class TestDrawdownControl:
    """测试回撤控制。"""

    def test_current_drawdown_no_data(self):
        from risk_engine.drawdown_control import current_drawdown
        assert current_drawdown([]) == 0.0

    def test_current_drawdown_from_peak(self):
        from risk_engine.drawdown_control import current_drawdown
        curve = [100, 110, 120, 90, 100]
        dd = current_drawdown(curve)
        # peak=120, current=100, dd=(120-100)/120=0.1667
        assert abs(dd - 0.1667) < 0.01

    def test_current_drawdown_at_peak(self):
        from risk_engine.drawdown_control import current_drawdown
        curve = [100, 110, 120, 130]
        dd = current_drawdown(curve)
        assert dd == 0.0

    def test_max_drawdown(self):
        from risk_engine.drawdown_control import max_drawdown
        curve = [100, 110, 80, 120, 90]
        md = max_drawdown(curve)
        # peak=110 after 100→110, then drops to 80: (110-80)/110=0.2727
        assert abs(md - 0.2727) < 0.01

    def test_drawdown_ok_within_limit(self):
        from risk_engine.drawdown_control import drawdown_ok
        curve = [100, 110, 108]
        assert drawdown_ok(curve, max_drawdown_pct=0.10) is True

    def test_drawdown_ok_breached(self):
        from risk_engine.drawdown_control import drawdown_ok
        curve = [100, 110, 80]
        assert drawdown_ok(curve, max_drawdown_pct=0.10) is False

    def test_should_disable_strategy(self):
        from risk_engine.drawdown_control import should_disable_strategy_drawdown
        curve = [100, 110, 80]
        assert should_disable_strategy_drawdown(curve, max_drawdown_pct=0.10) is True


class TestExposureLimit:
    """测试敞口限制。"""

    def test_total_exposure_notional(self):
        from risk_engine.exposure_limit import total_exposure_notional
        positions = {"600519": 100, "000858": 200}
        prices = {"600519": 1300, "000858": 180}
        total = total_exposure_notional(positions, prices)
        assert abs(total - (130000 + 36000)) < 1

    def test_exposure_ok(self):
        from risk_engine.exposure_limit import exposure_ok
        positions = {"600519": 100}
        prices = {"600519": 1300}
        assert exposure_ok(positions, prices, max_exposure=200000) is True
        assert exposure_ok(positions, prices, max_exposure=100000) is False


class TestVolatilityFilter:
    """测试波动率过滤。"""

    def test_volatility_annualized_empty(self):
        from risk_engine.volatility_filter import volatility_annualized
        assert volatility_annualized([]) == 0.0

    def test_volatility_annualized_zero(self):
        from risk_engine.volatility_filter import volatility_annualized
        returns = [0.01, 0.01, 0.01]  # constant
        vol = volatility_annualized(returns)
        assert vol == 0.0

    def test_volatility_annualized_normal(self):
        from risk_engine.volatility_filter import volatility_annualized
        returns = np.random.randn(252) * 0.02
        vol = volatility_annualized(returns, periods_per_year=252)
        assert 0.10 < vol < 0.50  # should be around 0.32

    def test_volatility_ok(self):
        from risk_engine.volatility_filter import volatility_ok
        returns = [0.001] * 100  # near zero vol
        assert volatility_ok(returns, max_volatility=0.50) is True

    def test_volatility_breach(self):
        from risk_engine.volatility_filter import volatility_ok
        returns = np.random.randn(252) * 0.05  # ~0.79 annualized
        assert volatility_ok(returns, max_volatility=0.30) is False


class TestRules:
    """测试风控规则评估。"""

    def test_evaluate_no_positions(self):
        from risk_engine.rules import evaluate
        result = evaluate(positions=[], total_assets=1000000, conn=None)
        assert result["pass"] is True

    def test_evaluate_single_position_within_limit(self):
        from risk_engine.rules import evaluate
        positions = [{"code": "600519", "qty": 100, "avg_price": 1300}]
        # position notional = 130k, total = 1M, pct = 13%
        # no rules configured in DB, should pass
        result = evaluate(positions=positions, total_assets=1000000, conn=None)
        assert result["pass"] is True

    def test_save_rule_no_db(self):
        """save_rule 在无 DB 时应返回 False 而不崩溃。"""
        from risk_engine.rules import save_rule
        result = save_rule("max_drawdown_pct", 0.10)
        assert isinstance(result, bool)


class TestDailyLossLimit:
    """测试日亏损限额。"""

    def test_daily_loss_ok_no_db(self):
        """无 DB 时应默认通过。"""
        from risk_engine.daily_loss_limit import daily_loss_ok
        assert daily_loss_ok(max_daily_loss_pct=0.02) is True

    def test_should_not_disable_no_db(self):
        from risk_engine.daily_loss_limit import should_disable_strategy_daily_loss
        assert should_disable_strategy_daily_loss() is False


class TestIndustryConcentration:
    """测试行业集中度。"""

    def test_get_industry_map_empty(self):
        from risk_engine.industry_concentration import get_industry_map
        result = get_industry_map([], conn=None)
        assert result == {}

    def test_get_industry_map_no_db(self):
        from risk_engine.industry_concentration import get_industry_map
        result = get_industry_map(["600519", "000858"], conn=None)
        assert isinstance(result, dict)

    def test_industry_exposure_empty(self):
        from risk_engine.industry_concentration import industry_exposure
        result = industry_exposure([], conn=None)
        assert result == {}

    def test_industry_concentration_ok_no_assets(self):
        from risk_engine.industry_concentration import industry_concentration_ok
        ok, violations = industry_concentration_ok(
            [{"code": "600519", "qty": 100, "avg_price": 1300}],
            total_assets=0,
            conn=None,
        )
        assert ok is True


class TestRiskMonitor:
    """测试风控监控。"""

    def test_evaluate_current_no_db(self):
        """无 DB 时应默认通过。"""
        from unittest import mock
        from risk_engine.risk_monitor import evaluate_current

        with mock.patch("risk_engine.risk_monitor._get_conn", return_value=None):
            result = evaluate_current()
        assert result["pass"] is True
        assert result["violations"] == []


class TestRiskActions:
    """测试风控动作。"""

    def test_execute_action_dry_run(self):
        from risk_engine.risk_actions import execute_action
        violation = {"rule_type": "single_position_pct_max", "value": 0.20, "message": "test"}
        result = execute_action(violation, {"dry_run": True})
        assert result["action"] == "reduce_position"
        assert result["done"] is False

    def test_execute_action_drawdown(self):
        from risk_engine.risk_actions import execute_action
        violation = {"rule_type": "max_drawdown_pct", "value": 0.10, "message": "drawdown"}
        result = execute_action(violation, {"dry_run": True})
        assert result["action"] == "alert"

    def test_apply_risk_actions(self):
        from risk_engine.risk_actions import apply_risk_actions
        violations = [
            {"rule_type": "single_position_pct_max", "value": 0.20, "message": "test"},
            {"rule_type": "max_drawdown_pct", "value": 0.10, "message": "drawdown"},
        ]
        results = apply_risk_actions(violations, {"dry_run": True})
        assert len(results) == 2
        assert results[0]["action"] == "reduce_position"
        assert results[1]["action"] == "alert"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
