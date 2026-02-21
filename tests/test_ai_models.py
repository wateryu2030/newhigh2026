# -*- coding: utf-8 -*-
"""
AI 选股模块单元测试：因子生成、模型训练、预测输出格式。
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_feature_engineering():
    """因子生成：单标的生成特征与 label 列。"""
    from ai_models.feature_engineering import build_features_for_symbol, build_features_multi

    np.random.seed(42)
    n = 120
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="D")
    close = 100 * np.cumprod(1 + np.random.randn(n) * 0.02)
    high = close * 1.01
    low = close * 0.99
    vol = np.random.randint(1_000_000, 5_000_000, n)
    df = pd.DataFrame({
        "date": dates,
        "open": close * 0.99, "high": high, "low": low, "close": close, "volume": vol,
    })
    fe = build_features_for_symbol(df, "000001", label_forward_days=5)
    assert isinstance(fe, pd.DataFrame)
    assert "date" in fe.columns and "symbol" in fe.columns and "label" in fe.columns
    assert "ma5" in fe.columns and "rsi_14" in fe.columns
    assert len(fe) > 0 and fe["symbol"].iloc[0] == "000001"

    multi = build_features_multi({"000001.XSHE": df}, label_forward_days=5)
    assert isinstance(multi, pd.DataFrame)
    assert multi.empty or ("label" in multi.columns and "symbol" in multi.columns)


def test_dataset_builder():
    """数据集构建：X, y 形状与无 NaN。"""
    from ai_models.dataset_builder import build_dataset, get_feature_columns

    cols = get_feature_columns()
    n = 100
    df = pd.DataFrame({c: np.random.randn(n) for c in cols})
    df["label"] = np.random.randn(n) * 0.1
    X, y = build_dataset(df, use_binary_label=True, binary_label_threshold=0.0)
    assert X.shape[0] == n and X.shape[1] == len(cols)
    assert y.shape == (n,) and np.isin(y, [0, 1]).all()


def test_model_trainer():
    """模型训练：能训练并保存。"""
    try:
        import xgboost  # noqa: F401
    except ImportError:
        print("  skip test_model_trainer (xgboost not installed)")
        return
    from ai_models.dataset_builder import build_dataset, get_feature_columns
    from ai_models.model_trainer import ModelTrainer
    import tempfile

    cols = get_feature_columns()
    n = 200
    np.random.seed(42)
    X = np.random.randn(n, len(cols)).astype(np.float64) * 0.1
    y = (np.random.rand(n) > 0.5).astype(np.float64)
    path = os.path.join(tempfile.gettempdir(), "test_xgb_astock.pkl")
    trainer = ModelTrainer(model_path=path, feature_cols=cols, use_binary=True)
    trainer.train(X, y)
    metrics = trainer.evaluate(X[:50], y[:50])
    assert "auc" in metrics
    trainer.save_model()
    assert os.path.exists(path)
    try:
        os.remove(path)
    except Exception:
        pass


def test_model_predictor():
    """预测：加载模型后输出 symbol, score 格式。"""
    try:
        import xgboost  # noqa: F401
    except ImportError:
        print("  skip test_model_predictor (xgboost not installed)")
        return
    from ai_models.dataset_builder import build_dataset, get_feature_columns
    from ai_models.model_trainer import ModelTrainer
    from ai_models.model_predictor import ModelPredictor
    import tempfile

    cols = get_feature_columns()
    n = 150
    np.random.seed(42)
    X = np.random.randn(n, len(cols)).astype(np.float64) * 0.1
    y = (np.random.rand(n) > 0.5).astype(np.float64)
    path = os.path.join(tempfile.gettempdir(), "test_xgb_pred_astock.pkl")
    trainer = ModelTrainer(model_path=path, feature_cols=cols, use_binary=True)
    trainer.train(X, y)
    trainer.save_model()

    pred = ModelPredictor(path)
    pred.load_model()
    scores = pred.predict_proba(X[:10])
    assert scores.shape == (10,) and scores.min() >= 0 and scores.max() <= 1

    feature_df = pd.DataFrame(X[:10], columns=cols)
    feature_df["symbol"] = [f"00{i:04d}" for i in range(10)]
    out = pred.score_symbols_from_features(feature_df)
    assert "symbol" in out.columns and "score" in out.columns and len(out) == 10
    try:
        os.remove(path)
    except Exception:
        pass


def test_signal_ranker():
    """信号排序：合并 AI 分与策略分，输出含 final_score。"""
    from ai_models.signal_ranker import rank_signals, top_n_symbols

    ai = pd.DataFrame({"symbol": ["A", "B", "C"], "score": [0.9, 0.5, 0.3]})
    st = pd.DataFrame({"symbol": ["A", "B", "C"], "score": [0.5, 0.8, 0.2]})
    ranked = rank_signals(ai, strategy_scores=st, ai_weight=0.6, strategy_weight=0.4)
    assert "final_score" in ranked.columns and "ai_score" in ranked.columns
    top = top_n_symbols(ranked, n=2)
    assert len(top) == 2 and top[0] == "A"


if __name__ == "__main__":
    test_feature_engineering()
    test_dataset_builder()
    test_model_trainer()
    test_model_predictor()
    test_signal_ranker()
    print("All tests passed.")
