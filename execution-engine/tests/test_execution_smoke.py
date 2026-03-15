"""冒烟测试：execution_engine 包可导入且核心 API 存在。"""


def test_execution_engine_import():
    """包可导入且包含预期导出。"""
    import execution_engine

    assert hasattr(execution_engine, "place_order")
    assert hasattr(execution_engine, "cancel_order")
    assert hasattr(execution_engine, "fetch_positions")
