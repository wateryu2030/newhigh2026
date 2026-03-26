"""
交易委托 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from app.db import get_db
from sqlalchemy.orm import Session
from app.models.database import Order, TradeLog, Account, Position, Stock
from pydantic import BaseModel, Field

router = APIRouter()


# ============== Schemas ==============

class OrderCreate(BaseModel):
    symbol: str
    order_type: str  # buy, sell
    order_style: str = "limit"  # limit, market
    order_price: Decimal
    order_quantity: int


class OrderResponse(BaseModel):
    id: str
    symbol: str
    stock_name: Optional[str]
    order_type: str
    order_style: str
    order_price: Decimal
    order_quantity: int
    filled_quantity: int
    status: str
    order_time: datetime
    
    class Config:
        from_attributes = True


# ============== 委托下单 ==============

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    创建交易委托
    
    - user_id: 用户 ID
    - symbol: 股票代码
    - order_type: 买入/卖出
    - order_style: 限价/市价
    - order_price: 委托价格
    - order_quantity: 委托数量
    """
    # 验证用户账户
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="用户账户不存在")
    
    # 验证股票
    stock = db.query(Stock).filter(Stock.symbol == order_data.symbol).first()
    if not stock:
        # 尝试从 akshare 获取股票信息并创建记录
        try:
            import akshare as ak
            stock_info = ak.stock_zh_a_spot_em()
            stock_data = stock_info[stock_info['代码'] == order_data.symbol]
            if not stock_data.empty:
                row = stock_data.iloc[0]
                stock = Stock(
                    symbol=order_data.symbol,
                    name=row['名称'],
                    exchange="SH" if order_data.symbol.startswith('6') else "SZ",
                    current_price=float(row['最新价'])
                )
                db.add(stock)
                db.commit()
        except:
            pass
    
    # 检查资金/持仓
    if order_data.order_type == "buy":
        required_amount = order_data.order_price * order_data.order_quantity
        if account.available_cash < required_amount:
            raise HTTPException(
                status_code=400, 
                detail=f"资金不足，需要 {required_amount}，可用 {account.available_cash}"
            )
        # 冻结资金
        account.available_cash -= required_amount
        account.frozen_cash += required_amount
        
    elif order_data.order_type == "sell":
        position = db.query(Position).filter(
            Position.user_id == user_id,
            Position.symbol == order_data.symbol
        ).first()
        
        if not position or position.available_quantity < order_data.order_quantity:
            raise HTTPException(
                status_code=400, 
                detail="持仓不足"
            )
        # 冻结持仓
        position.available_quantity -= order_data.order_quantity
        position.frozen_quantity += order_data.order_quantity
    
    # 创建委托
    order = Order(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account.id,
        symbol=order_data.symbol,
        stock_name=stock.name if stock else None,
        order_type=order_data.order_type,
        order_style=order_data.order_style,
        order_price=order_data.order_price,
        order_quantity=order_data.order_quantity,
        unfilled_quantity=order_data.order_quantity,
        total_amount=order_data.order_price * order_data.order_quantity,
        status="pending"
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # TODO: 发送到交易所（模拟撮合）
    # 这里简化处理，直接标记为已成交
    await simulate_order_fill(db, order, account)
    
    return order


async def simulate_order_fill(db: Session, order: Order, account: Account):
    """模拟委托成交（实盘需对接交易所）"""
    # 简化：假设立即成交
    order.status = "filled"
    order.filled_quantity = order.order_quantity
    order.filled_amount = order.order_price * order.order_quantity
    order.filled_time = datetime.utcnow()
    
    # 创建成交记录
    trade = TradeLog(
        id=uuid.uuid4(),
        order_id=order.id,
        user_id=order.user_id,
        account_id=order.account_id,
        symbol=order.symbol,
        trade_type=order.order_type,
        trade_price=order.order_price,
        trade_quantity=order.order_quantity,
        trade_amount=order.filled_amount,
        commission=order.filled_amount * Decimal('0.0003'),  # 万分之三佣金
        stamp_tax=order.filled_amount * Decimal('0.001') if order.order_type == "sell" else Decimal('0')  # 印花税
    )
    db.add(trade)
    
    # 更新账户
    if order.order_type == "buy":
        account.frozen_cash -= order.filled_amount
        # 更新或创建持仓
        position = db.query(Position).filter(
            Position.user_id == order.user_id,
            Position.symbol == order.symbol
        ).first()
        
        if position:
            # 加仓
            total_cost = position.cost_amount + order.filled_amount
            total_qty = position.quantity + order.order_quantity
            position.cost_price = total_cost / total_qty
            position.quantity = total_qty
            position.available_quantity += order.order_quantity
            position.cost_amount = total_cost
        else:
            # 新建持仓
            position = Position(
                user_id=order.user_id,
                account_id=account.id,
                symbol=order.symbol,
                cost_price=order.order_price,
                cost_amount=order.filled_amount,
                quantity=order.order_quantity,
                available_quantity=order.order_quantity
            )
            db.add(position)
            
    else:  # sell
        account.available_cash += order.filled_amount - trade.commission - trade.stamp_tax
        # 更新持仓
        position = db.query(Position).filter(
            Position.user_id == order.user_id,
            Position.symbol == order.symbol
        ).first()
        if position:
            position.quantity -= order.order_quantity
            position.available_quantity -= order.order_quantity
            position.frozen_quantity = 0
            if position.quantity == 0:
                position.status = "closed"
    
    # 更新账户市值
    account.market_value = db.query(
        db.query(Position).filter(
            Position.user_id == order.user_id,
            Position.status == "active"
        ).sum(Position.market_value)
    ).scalar() or 0
    
    account.total_assets = account.available_cash + account.market_value
    account.total_profit = account.total_assets - 500000  # 假设初始资金 50 万
    
    db.commit()


# ============== 委托查询 ==============

@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    user_id: str = Query(...),
    status: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """查询委托列表"""
    query = db.query(Order).filter(Order.user_id == user_id)
    
    if status:
        query = query.filter(Order.status == status)
    if symbol:
        query = query.filter(Order.symbol == symbol)
    
    orders = query.order_by(Order.order_time.desc()).limit(limit).all()
    return orders


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """查询单个委托"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="委托不存在")
    return order


# ============== 委托操作 ==============

@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, db: Session = Depends(get_db)):
    """撤销委托"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="委托不存在")
    
    if order.status not in ["pending", "partial_filled"]:
        raise HTTPException(status_code=400, detail="委托状态不可撤销")
    
    # 解冻资金/持仓
    account = db.query(Account).filter(Account.id == order.account_id).first()
    if order.order_type == "buy":
        unfilled_amount = order.order_price * order.unfilled_quantity
        account.frozen_cash -= unfilled_amount
        account.available_cash += unfilled_amount
    else:
        position = db.query(Position).filter(
            Position.user_id == order.user_id,
            Position.symbol == order.symbol
        ).first()
        if position:
            position.frozen_quantity -= order.unfilled_quantity
            position.available_quantity += order.unfilled_quantity
    
    order.status = "cancelled"
    db.commit()
    
    return {"message": "委托已撤销"}
