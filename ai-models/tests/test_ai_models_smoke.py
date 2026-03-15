"""冒烟测试：ai_models 包可导入且导出符合预期。"""


def test_ai_models_import():
    """包可导入且包含预期导出。"""
    import ai_models

    assert hasattr(ai_models, "run_emotion_cycle")
    assert hasattr(ai_models, "run_hotmoney_detector")
    assert hasattr(ai_models, "run_sector_rotation_ai")
