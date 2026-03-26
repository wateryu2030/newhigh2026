"""
风控 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional
from decimal import Decimal
import uuid
from datetime import datetime

from app.db import get_db
from sqlalchemy.orm import Session
from app.models.database import RiskConfig, RiskAlert, Account, Position
from pydantic import BaseModel

router = APIRouter()


class RiskConfigUpdate(BaseModel):
    max_drawdown_warning: Optional[Decimal] = None
    max_drawdown_critical: Optional[Decimal] = None
    daily_loss_limit: Optional[Decimal] = None
    single_stock_limit: Optional[Decimal] = None
    industry_limit: Optional[Decimal] = None
    max_position_ratio: Optional[Decimal] = None


@router.get("/config")
async def get_risk_config(user_id: str = Query(...), db: Session = Depends(get_db)):
    """获取风控配置"""
    config = db.query(RiskConfig).filter(RiskConfig.user_id == user_id).first()
    
    if not config:
        # 创建默认配置
        config = RiskConfig(user_id=user_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return {
        "max_drawdown_warning": float(config.max_drawdown_warning),
        "max_drawdown_critical": float(config.max_drawdown_critical),
        "daily_loss_limit": float(config.daily_loss_limit),
        "single_stock_limit": float(config.single_stock_limit),
        "industry_limit": float(config.industry_limit),
        "max_position_ratio": float(config.max_position_ratio)
    }


@router.put("/config")
async def update_risk_config(
    config_data: RiskConfigUpdate,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """更新风控配置"""
    config = db.query(RiskConfig).filter(RiskConfig.user_id == user_id).first()
    
    if not config:
        config = RiskConfig(user_id=user_id)
        db.add(config)
    
    update_data = config_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return {"message": "风控配置已更新"}


@router.get("/alerts")
async def get_risk_alerts(
    user_id: str = Query(...),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """获取风险预警列表"""
    query = db.query(RiskAlert).filter(RiskAlert.user_id == user_id)
    
    if status:
        query = query.filter(RiskAlert.status == status)
    
    alerts = query.order_by(RiskAlert.alert_time.desc()).limit(limit).all()
    
    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "alert_level": a.alert_level,
            "title": a.title,
            "message": a.message,
            "suggestion": a.suggestion,
            "alert_time": a.alert_time.isoformat() if a.alert_time else None,
            "status": a.status
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/handle")
async def handle_alert(alert_id: str, db: Session = Depends(get_db)):
    """处理预警"""
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    
    alert.status = "handled"
    alert.handled_time = datetime.utcnow()
    db.commit()
    
    return {"message": "预警已处理"}


@router.get("/metrics")
async def get_risk_metrics(user_id: str = Query(...), db: Session = Depends(get_db)):
    """获取风险指标"""
    # 获取账户信息
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    # 获取持仓
    positions = db.query(Position).filter(
        Position.user_id == user_id,
        Position.status == "active"
    ).all()
    
    # 计算持仓集中度
    total_market_value = sum(p.market_value for p in positions if p.market_value)
    max_single_position = max((p.market_value for p in positions if p.market_value), default=0)
    
    single_concentration = (max_single_position / total_market_value * 100) if total_market_value > 0 else 0
    
    # 计算仓位
    position_ratio = (total_market_value / account.total_assets * 100) if account.total_assets > 0 else 0
    
    return {
        "var_95": float(account.total_assets * Decimal('0.05')),  # 简化 VaR 计算
        "max_drawdown": float(account.total_profit_rate) if account.total_profit else 0,
        "position_ratio": position_ratio,
        "single_stock_concentration": single_concentration,
        "industry_concentration": 0,  # TODO: 按行业计算
        "alert_count": db.query(RiskAlert).filter(
            RiskAlert.user_id == user_id,
            RiskAlert.status == "unread"
        ).count()
    }
