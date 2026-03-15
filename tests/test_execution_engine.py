"""Integration tests for execution engine (order lifecycle, simulated)."""

import pytest


def test_order_state_enum():
    from execution_engine.order_lifecycle import OrderState

    assert OrderState.NEW.value == "new"
    assert OrderState.FILLED.value == "filled"


def test_path_to_stage():
    try:
        from gateway.metrics import path_to_stage
    except ImportError:
        pytest.skip("gateway not installed")
    assert path_to_stage("/api/data/incremental") == "data"
    assert path_to_stage("/api/market/emotion") == "scan"
    assert path_to_stage("/api/ai/decision") == "ai"
    assert path_to_stage("/api/simulated/step") == "trade"
    assert path_to_stage("/api/execution/equity_curve") == "trade"
