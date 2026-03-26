"""
策略管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import uuid
import json

from app.db import get_db
from sqlalchemy.orm import Session
from app.models.database import Strategy, StrategySignal, BacktestResult, StockDailyBar
from pydantic import BaseModel

router = APIRouter()


class StrategyCreate(BaseModel):
    name: str
    strategy_type: str
    symbols: List[str]
    params: Dict[str, Any] = {}
    description: Optional[str] = None


class BacktestRequest(BaseModel):
    start_date: date
    end_date: date
    initial_capital: Decimal = 500000


@router.post("/strategies")
async def create_strategy(
    strategy_data: StrategyCreate,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """创建策略"""
    strategy = Strategy(
        id=uuid.uuid4(),
        user_id=user_id,
        name=strategy_data.name,
        strategy_type=strategy_data.strategy_type,
        symbols=strategy_data.symbols,
        params=strategy_data.params,
        description=strategy_data.description,
        status="stopped"
    )
    
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    return {"id": str(strategy.id), "message": "策略创建成功"}


@router.get("/strategies")
async def get_strategies(user_id: str = Query(...), db: Session = Depends(get_db)):
    """获取策略列表"""
    strategies = db.query(Strategy).filter(Strategy.user_id == user_id).all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "strategy_type": s.strategy_type,
            "symbols": s.symbols,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in strategies
    ]


@router.post("/strategies/{strategy_id}/start")
async def start_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """启动策略"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    strategy.status = "running"
    strategy.start_time = datetime.utcnow()
    db.commit()
    
    return {"message": "策略已启动"}


@router.post("/strategies/{strategy_id}/stop")
async def stop_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """停止策略"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    strategy.status = "stopped"
    strategy.stop_time = datetime.utcnow()
    db.commit()
    
    return {"message": "策略已停止"}


@router.post("/strategies/{strategy_id}/backtest")
async def run_backtest(
    strategy_id: str,
    backtest_data: BacktestRequest,
    db: Session = Depends(get_db)
):
    """执行回测"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 根据策略类型选择回测引擎
    strategy_type = strategy.strategy_type
    
    if strategy_type == '双均线':
        from app.services.backtest_engine import run_ma_cross_backtest
        result = run_ma_cross_backtest(
            symbols=strategy.symbols,
            start_date=backtest_data.start_date,
            end_date=backtest_data.end_date,
            initial_capital=float(backtest_data.initial_capital),
            params=strategy.params
        )
    elif strategy_type == 'MACD':
        from app.services.macd_strategy import run_macd_backtest
        result = run_macd_backtest(
            symbols=strategy.symbols,
            start_date=backtest_data.start_date,
            end_date=backtest_data.end_date,
            initial_capital=float(backtest_data.initial_capital),
            params=strategy.params
        )
    elif strategy_type == 'RSI':
        from app.services.rsi_strategy import run_rsi_backtest
        result = run_rsi_backtest(
            symbols=strategy.symbols,
            start_date=backtest_data.start_date,
            end_date=backtest_data.end_date,
            initial_capital=float(backtest_data.initial_capital),
            params=strategy.params
        )
    else:
        # 默认使用双均线
        from app.services.backtest_engine import run_ma_cross_backtest
        result = run_ma_cross_backtest(
            symbols=strategy.symbols,
            start_date=backtest_data.start_date,
            end_date=backtest_data.end_date,
            initial_capital=float(backtest_data.initial_capital),
            params=strategy.params
        )
    
    # 保存回测结果
    backtest_result = BacktestResult(
        id=uuid.uuid4(),
        strategy_id=strategy_id,
        user_id=strategy.user_id,
        start_date=backtest_data.start_date,
        end_date=backtest_data.end_date,
        initial_capital=backtest_data.initial_capital,
        total_return=result['total_return'],
        annual_return=result['annual_return'],
        sharpe_ratio=result['sharpe_ratio'],
        max_drawdown=result['max_drawdown'],
        total_trades=result['total_trades'],
        win_rate=result['win_rate'],
        report=result
    )
    
    db.add(backtest_result)
    db.commit()
    
    return {
        "backtest_id": str(backtest_result.id),
        "total_return": result['total_return'],
        "sharpe_ratio": result['sharpe_ratio'],
        "max_drawdown": result['max_drawdown'],
        "total_trades": result['total_trades']
    }
