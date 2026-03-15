"""因子构建：基于 a_stock_daily 计算简单因子，可扩展对接 feature-engine。"""

from __future__ import annotations


def build_factors(code: str | None = None, lookback: int = 60) -> int:
    """
    基于日线计算动量/波动等因子，写入 features_daily 或单独因子表（当前为占位，可对接 feature-engine）。
    code: 单只标的；None 表示全表。
    lookback: 计算窗口。
    返回处理条数。
    """
    from ..storage.duckdb_manager import get_conn

    conn = get_conn()
    # 占位：仅统计日线条数；后续可在此调用 feature_engine.build_feature_matrix 并落库
    if code:
        r = conn.execute("SELECT COUNT(*) FROM a_stock_daily WHERE code = ?", [code]).fetchone()
    else:
        r = conn.execute("SELECT COUNT(*) FROM a_stock_daily").fetchone()
    n = int(r[0]) if r else 0
    conn.close()
    return n
