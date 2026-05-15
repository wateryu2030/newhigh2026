"""Execution API endpoints."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py ---

from .endpoints_helpers import (  # noqa: E402
    _execution_broker_module,
    _simulated_module,
)


# --- Execution Routes ---


@router.get("/execution/mode")
def get_execution_mode() -> dict:
    """当前执行模式：simulated（模拟盘）或 live（实盘）。"""
    try:
        execution_mode, _, _ = _execution_broker_module()
        return {"mode": execution_mode()}
    except Exception as e:
        return {"mode": "simulated", "error": str(e)}


@router.post("/execution/mode")
def post_execution_mode(mode: str = "simulated") -> dict:
    """设置执行模式（仅当前进程/请求生效；持久化需配置 EXECUTION_MODE 环境变量）。"""
    try:
        _, set_execution_mode, _ = _execution_broker_module()
        set_execution_mode(mode)
        return {"ok": True, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulated/step")
def post_simulated_step(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    lot_size: int = 100,
    max_buys: int = 10,
    max_sells: int = 10,
    risk_check: bool = True,
) -> dict:
    """
    执行一步模拟盘：根据 trade_signals 生成模拟订单，更新持仓与资金快照。
    risk_check=True（默认）时先走 risk-engine，不通过则返回 risk_violations。
    """
    try:
        step_simulated, _, _, _ = _simulated_module()
        return step_simulated(
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            lot_size=lot_size,
            max_buys=max_buys,
            max_sells=max_sells,
            risk_check=risk_check,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/positions")
def get_simulated_positions(limit: int = 100) -> dict:
    """模拟盘当前持仓列表。"""
    try:
        _, sim_get_positions, _, _ = _simulated_module()
        positions = sim_get_positions(limit=limit)
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/orders")
def get_simulated_orders(limit: int = 100, status: Optional[str] = None) -> dict:
    """模拟盘订单列表；status 可选 pending/filled。"""
    try:
        _, _, sim_get_orders, _ = _simulated_module()
        orders = sim_get_orders(limit=limit, status=status)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/account_snapshots")
def get_simulated_account_snapshots(limit: int = 100) -> dict:
    """模拟盘资金快照历史。"""
    try:
        _, _, _, sim_get_account_snapshots = _simulated_module()
        snapshots = sim_get_account_snapshots(limit=limit)
        return {"snapshots": snapshots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/equity_curve")
def get_execution_equity_curve(limit: int = 200) -> dict:
    """执行层资金曲线：从 sim_account_snapshots 聚合，供前端资金曲线图。"""
    try:
        _, _, _, sim_get_account_snapshots = _simulated_module()
        snapshots = sim_get_account_snapshots(limit=limit)
        curve = []
        for s in reversed(snapshots):
            ts = s.get("snapshot_time")
            v = s.get("total_assets")
            if ts is not None and v is not None:
                dt = ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
                curve.append({"date": dt, "value": float(v)})
        return {"equity_curve": curve}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
def get_positions() -> dict:
    """Current positions (stub)."""
    return {"positions": []}
