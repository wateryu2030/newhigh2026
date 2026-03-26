"""
持仓 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
import akshare as ak

from app.db import get_db
from sqlalchemy.orm import Session
from app.models.database import Position, Account, Stock

router = APIRouter()


@router.get("/positions")
async def get_positions(
    user_id: str = Query(...),
    show_closed: bool = Query(False),
    db: Session = Depends(get_db)
):
    """获取持仓列表"""
    query = db.query(Position).filter(
        Position.user_id == user_id,
        Position.status == "active"
    )
    
    if show_closed:
        query = db.query(Position).filter(Position.user_id == user_id)
    
    positions = query.all()
    
    # 更新当前价格和盈亏
    result = []
    for pos in positions:
        try:
            # 获取实时行情
            quote = ak.stock_zh_a_spot_em()
            stock_data = quote[quote['代码'] == pos.symbol]
            if not stock_data.empty:
                row = stock_data.iloc[0]
                pos.current_price = float(row['最新价'])
                pos.market_value = pos.current_price * pos.quantity
                pos.profit = pos.market_value - pos.cost_amount
                pos.profit_rate = (pos.profit / pos.cost_amount * 100) if pos.cost_amount > 0 else 0
        except:
            pass
        
        result.append({
            "id": str(pos.id),
            "symbol": pos.symbol,
            "stock_name": pos.stock_name,
            "quantity": pos.quantity,
            "available_quantity": pos.available_quantity,
            "cost_price": float(pos.cost_price),
            "current_price": float(pos.current_price) if pos.current_price else 0,
            "market_value": float(pos.market_value) if pos.market_value else 0,
            "profit": float(pos.profit) if pos.profit else 0,
            "profit_rate": float(pos.profit_rate) if pos.profit_rate else 0,
            "today_profit": float(pos.today_profit) if pos.today_profit else 0
        })
    
    return result


@router.get("/positions/{symbol}")
async def get_position(symbol: str, user_id: str = Query(...), db: Session = Depends(get_db)):
    """获取单个持仓"""
    position = db.query(Position).filter(
        Position.user_id == user_id,
        Position.symbol == symbol
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")
    
    return {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "cost_price": float(position.cost_price),
        "current_price": float(position.current_price) if position.current_price else 0,
        "profit": float(position.profit) if position.profit else 0,
        "profit_rate": float(position.profit_rate) if position.profit_rate else 0
    }


@router.get("/account")
async def get_account_info(user_id: str = Query(...), db: Session = Depends(get_db)):
    """获取账户信息"""
    account = db.query(Account).filter(Account.user_id == user_id).first()
    
    if not account:
        # 创建默认账户
        account = Account(
            user_id=user_id,
            available_cash=500000,
            total_assets=500000
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    
    return {
        "user_id": user_id,
        "total_assets": float(account.total_assets),
        "available_cash": float(account.available_cash),
        "frozen_cash": float(account.frozen_cash),
        "market_value": float(account.market_value),
        "total_profit": float(account.total_profit),
        "total_profit_rate": float(account.total_profit_rate),
        "today_profit": float(account.today_profit),
        "today_profit_rate": float(account.today_profit_rate)
    }
