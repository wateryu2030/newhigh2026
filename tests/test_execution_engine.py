"""执行引擎核心功能测试。"""

import pytest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "execution-engine", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data-pipeline", "src"))


class TestSignalExecutor:
    """测试信号执行器。"""

    @patch("execution_engine.signal_executor.get_actionable_signals")
    def test_run_signal_executor_dry_run(self, mock_signals):
        """dry_run 模式不应实际下单。"""
        from execution_engine.signal_executor import run_signal_executor

        mock_signals.return_value = (
            [{"code": "600519", "signal_score": 0.85, "signal": "BUY", "confidence": 0.85, "target_price": 1400, "stop_loss": 1200}],
            [],
        )
        result = run_signal_executor(dry_run=True)
        assert result["dry_run"] is True
        assert len(result["actions"]) == 0
        assert len(result["buy_candidates"]) == 1

    @patch("execution_engine.signal_executor.get_actionable_signals")
    def test_run_signal_executor_live(self, mock_signals):
        """非 dry_run 应生成真实 actions。"""
        from execution_engine.signal_executor import run_signal_executor

        mock_signals.return_value = (
            [{"code": "600519", "signal_score": 0.85, "signal": "BUY", "confidence": 0.85, "target_price": 1400, "stop_loss": 1200}],
            [{"code": "000858", "signal_score": 0.2, "signal": "SELL", "confidence": 0.2, "target_price": 0, "stop_loss": 100}],
        )
        result = run_signal_executor(dry_run=False, lot_size=100)
        assert result["dry_run"] is False
        assert len(result["buy_candidates"]) == 1
        assert len(result["sell_candidates"]) == 1

    @patch("execution_engine.signal_executor.get_actionable_signals")
    def test_execute_buy_dry_run(self, mock_signals):
        """execute_buy dry_run: 只返回意向。"""
        from execution_engine.signal_executor import execute_buy

        result = execute_buy("600519", quantity=100, dry_run=True)
        assert result["ok"] is True
        assert result["action"] == "BUY"
        assert "dry_run" in result["message"]

    def test_execute_sell_dry_run(self):
        """execute_sell dry_run: 只返回意向。"""
        from execution_engine.signal_executor import execute_sell

        result = execute_sell("000858", quantity=100, dry_run=True)
        assert result["ok"] is True
        assert result["action"] == "SELL"


class TestBrokers:
    """测试经纪商抽象层。"""

    def test_base_broker_abc(self):
        """BaseBroker 是抽象类，不可直接实例化。"""
        from execution_engine.brokers.base import BaseBroker

        with pytest.raises(TypeError):
            BaseBroker()  # type: ignore

    def test_order_result_dataclass(self):
        """OrderResult 数据类基本功能。"""
        from execution_engine.brokers.base import OrderResult

        r = OrderResult(ok=True, order_id="12345", message="filled")
        assert r.ok is True
        assert r.order_id == "12345"

    def test_position_info_dataclass(self):
        """PositionInfo 数据类基本功能。"""
        from execution_engine.brokers.base import PositionInfo

        p = PositionInfo(symbol="600519", side="LONG", quantity=100, avg_price=1300.0)
        assert p.symbol == "600519"
        assert p.quantity == 100

    def test_registry_default_simulated(self):
        """默认模式应返回 SimulatedBroker。"""
        os.environ["EXECUTION_MODE"] = "simulated"
        from execution_engine.brokers.registry import get_broker, SimulatedBroker

        broker = get_broker()
        from execution_engine.brokers.registry import LiveBroker
        assert isinstance(broker, SimulatedBroker)
        assert not isinstance(broker, LiveBroker)

    def test_simulated_broker_cancel(self):
        """SimulatedBroker 撤单为 no-op。"""
        from execution_engine.brokers.simulated_broker import SimulatedBroker

        broker = SimulatedBroker()
        result = broker.cancel_order("600519", "123")
        assert result.ok is True


class TestExecutionRunner:
    """测试执行引擎主 Runner。"""

    def test_execution_config_defaults(self):
        """默认配置应使用安全值。"""
        from execution_engine.runner import ExecutionConfig

        cfg = ExecutionConfig()
        assert cfg.dry_run is True
        assert cfg.enable_risk_check is True
        assert cfg.lot_size == 100
        assert cfg.initial_cash == 1_000_000.0

    def test_execution_result_dataclass(self):
        """ExecutionResult 默认值。"""
        from execution_engine.runner import ExecutionResult

        result = ExecutionResult(ok=True, dry_run=True)
        assert result.ok is True
        assert result.orders_placed == 0
        assert result.risk_blocked is False

    @patch("execution_engine.runner.ExecutionRunner._risk_check")
    @patch("execution_engine.signal_executor.get_actionable_signals")
    def test_runner_risk_blocked(self, mock_signals, mock_risk):
        """风控不通过应阻止执行。"""
        from execution_engine.runner import ExecutionRunner, ExecutionConfig

        mock_risk.return_value = (False, [{"rule_type": "max_drawdown_pct", "message": "drawdown breach"}])

        runner = ExecutionRunner(ExecutionConfig(dry_run=True))
        result = runner.step()

        assert result.ok is False
        assert result.risk_blocked is True
        assert len(result.risk_violations) > 0

    def test_runner_get_status(self):
        """get_status 不应抛异常。"""
        from execution_engine.runner import ExecutionRunner

        runner = ExecutionRunner()
        status = runner.get_status()
        assert "mode" in status


class TestPaperTrading:
    """测试纸面交易增强层。"""

    def test_paper_config_defaults(self):
        """默认纸面交易配置。"""
        from execution_engine.paper_trading import PaperTradingConfig

        cfg = PaperTradingConfig()
        assert cfg.latency_ms == 50
        assert cfg.partial_fill_prob == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
