"""
行业集中度控制：限制单一行业的持仓占比。
依赖 a_stock_list 中的 industry 字段（由 data_pipeline 写入）。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)


def _get_conn():
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return None
        return get_conn(read_only=True)
    except Exception:
        return None


def get_industry_map(codes: List[str], conn: Any = None) -> Dict[str, str]:
    """返回 code → industry 的映射。"""
    close_conn = conn is None
    if conn is None:
        conn = _get_conn()
    if conn is None or not codes:
        return {}

    try:
        placeholders = ",".join(["?"] * len(codes))
        rows = conn.execute(
            f"SELECT code, industry FROM a_stock_list WHERE code IN ({placeholders})",
            codes,
        ).fetchall()
        return {str(r[0]): str(r[1] or "未分类") for r in rows}
    except Exception:
        _log.exception("Failed to load industry map")
        return {}
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def industry_exposure(
    positions: List[Dict[str, Any]],
    prices: Optional[Dict[str, float]] = None,
    conn: Any = None,
) -> Dict[str, float]:
    """
    计算各行业的名义敞口。
    positions: [{"code": str, "qty": float, "avg_price": float}, ...]
    返回: {"行业名": 名义市值, ...}
    """
    if not positions:
        return {}

    codes = [p.get("code", "") for p in positions]
    industry_map = get_industry_map(codes, conn=conn)

    if prices is None:
        prices = {p.get("code", ""): float(p.get("avg_price") or 0) for p in positions}

    exposure: Dict[str, float] = defaultdict(float)
    for p in positions:
        code = p.get("code", "")
        qty = float(p.get("qty") or 0)
        px = prices.get(code, float(p.get("avg_price") or 0))
        ind = industry_map.get(code, "未分类")
        exposure[ind] += qty * px

    return dict(exposure)


def industry_concentration_ok(
    positions: List[Dict[str, Any]],
    max_single_industry_pct: float = 0.30,
    total_assets: Optional[float] = None,
    prices: Optional[Dict[str, float]] = None,
    conn: Any = None,
) -> tuple[bool, List[Dict[str, Any]]]:
    """
    检查单一行业集中度是否超标。
    返回: (通过, 违规详情列表)

    违规详情: {"industry": str, "exposure_pct": float, "limit_pct": float}
    """
    if total_assets is None or total_assets <= 0:
        return True, []

    exposures = industry_exposure(positions, prices=prices, conn=conn)
    violations = []
    for ind, val in exposures.items():
        pct = val / total_assets
        if pct > max_single_industry_pct:
            violations.append(
                {
                    "industry": ind,
                    "exposure_pct": round(pct, 4),
                    "limit_pct": max_single_industry_pct,
                    "message": f"行业[{ind}]集中度 {pct:.2%} > {max_single_industry_pct:.2%}",
                }
            )
    if violations:
        _log.warning("Industry concentration violations: %s", violations)
    return len(violations) == 0, violations


def should_disable_strategy_concentration(
    positions: List[Dict[str, Any]],
    max_single_industry_pct: float = 0.30,
    total_assets: Optional[float] = None,
    prices: Optional[Dict[str, float]] = None,
    conn: Any = None,
) -> bool:
    """行业集中度超标则建议停止策略。"""
    ok, _ = industry_concentration_ok(
        positions, max_single_industry_pct, total_assets, prices, conn
    )
    return not ok
