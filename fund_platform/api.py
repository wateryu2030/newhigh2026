# -*- coding: utf-8 -*-
"""
基金管理平台 API：NAV、AUM、投资者份额、申赎接口，可挂载到 FastAPI。
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from .fund_manager import FundManager

router = APIRouter(prefix="/fund", tags=["fund"])

# 全局 FundManager 实例，由主应用或脚本注入
_fund_manager: Optional[FundManager] = None


def set_fund_manager(mgr: FundManager) -> None:
    global _fund_manager
    _fund_manager = mgr


def get_fund_manager() -> Optional[FundManager]:
    return _fund_manager


@router.get("/nav")
def get_nav():
    if _fund_manager is None:
        return {"nav": 0.0}
    return {"nav": _fund_manager.get_nav()}


@router.get("/aum")
def get_aum():
    if _fund_manager is None:
        return {"aum": 0.0}
    return {"aum": _fund_manager.get_aum()}


@router.get("/summary")
def summary():
    if _fund_manager is None:
        return {"nav": 0.0, "aum": 0.0, "total_units": 0.0}
    return _fund_manager.to_dict()


@router.post("/subscribe")
def subscribe(investor_id: str, amount: float, date: str = ""):
    if _fund_manager is None:
        raise HTTPException(503, "Fund manager not initialized")
    if amount <= 0:
        raise HTTPException(400, "amount must be positive")
    return _fund_manager.subscribe(investor_id, amount, date=date)


@router.post("/redeem")
def redeem(investor_id: str, units: float, date: str = ""):
    if _fund_manager is None:
        raise HTTPException(503, "Fund manager not initialized")
    if units <= 0:
        raise HTTPException(400, "units must be positive")
    return _fund_manager.redeem(investor_id, units, date=date)


