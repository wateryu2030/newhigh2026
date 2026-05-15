"""配额计数（内存）单元测试。"""
from gateway.quota_limits import (
    check_and_increment,
    default_quota_payload,
    reset_counters_for_tests,
)


def setup_function() -> None:
    reset_counters_for_tests()


def test_check_and_increment_respects_daily_limit(monkeypatch) -> None:
    monkeypatch.setenv("FREE_STOCK_QA_PER_DAY", "2")
    reset_counters_for_tests()
    ok1, _, _, _ = check_and_increment("u1", "stock_qa")
    ok2, _, _, _ = check_and_increment("u1", "stock_qa")
    ok3, msg, _, _ = check_and_increment("u1", "stock_qa")
    assert ok1 and ok2
    assert not ok3
    assert "上限" in msg


def test_default_quota_payload_shape() -> None:
    p = default_quota_payload("anon")
    assert "day" in p and "stock_qa" in p and "backtest" in p
    assert p.get("user_level") == "trial"


def test_trial_level_uses_quota_trial_env(monkeypatch) -> None:
    monkeypatch.setenv("QUOTA_TRIAL_STOCK_QA", "2")
    reset_counters_for_tests()
    ok1, _, _, _ = check_and_increment("u1", "stock_qa", "trial")
    ok2, _, _, _ = check_and_increment("u1", "stock_qa", "trial")
    ok3, msg, _, _ = check_and_increment("u1", "stock_qa", "trial")
    assert ok1 and ok2 and not ok3
    assert "上限" in msg
