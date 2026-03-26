"""
红山量化交易平台 - 数据库模型
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, DateTime, Date, 
    Text, Boolean, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base
import uuid

Base = declarative_base()


# ============== Enums ==============

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStyle(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class StrategyStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ============== Models ==============

class User(Base):
    """用户账户表"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    feishu_open_id = Column(String(100), index=True)
    feishu_user_id = Column(String(100))
    
    status = Column(String(20), default=UserStatus.ACTIVE)
    risk_level = Column(String(20), default=RiskLevel.MEDIUM)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    account = relationship("Account", back_populates="user", uselist=False, cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    risk_config = relationship("RiskConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("RiskAlert", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    """账户余额表"""
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    total_assets = Column(Numeric(20, 2), default=0)
    available_cash = Column(Numeric(20, 2), default=0)
    frozen_cash = Column(Numeric(20, 2), default=0)
    market_value = Column(Numeric(20, 2), default=0)
    
    total_profit = Column(Numeric(20, 2), default=0)
    total_profit_rate = Column(Numeric(10, 4), default=0)
    today_profit = Column(Numeric(20, 2), default=0)
    today_profit_rate = Column(Numeric(10, 4), default=0)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="account")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="account", cascade="all, delete-orphan")
    trade_logs = relationship("TradeLog", back_populates="account", cascade="all, delete-orphan")


class Stock(Base):
    """股票信息表"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    
    industry = Column(String(50), index=True)
    sector = Column(String(50))
    list_date = Column(Date)
    total_shares = Column(Numeric(20, 2))
    circulating_shares = Column(Numeric(20, 2))
    
    current_price = Column(Numeric(10, 2))
    pre_close = Column(Numeric(10, 2))
    open_price = Column(Numeric(10, 2))
    high_price = Column(Numeric(10, 2))
    low_price = Column(Numeric(10, 2))
    volume = Column(BigInteger)
    amount = Column(Numeric(20, 2))
    change_percent = Column(Numeric(10, 4))
    
    quote_time = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class StockDailyBar(Base):
    """股票历史行情表 (日线)"""
    __tablename__ = "stock_daily_bars"
    __table_args__ = (
        UniqueConstraint('symbol', 'trade_date'),
        Index('idx_bars_symbol_date', 'symbol', 'trade_date'),
    )
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), ForeignKey("stocks.symbol", ondelete="CASCADE"), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    
    open = Column(Numeric(10, 2), nullable=False)
    high = Column(Numeric(10, 2), nullable=False)
    low = Column(Numeric(10, 2), nullable=False)
    close = Column(Numeric(10, 2), nullable=False)
    pre_close = Column(Numeric(10, 2))
    change = Column(Numeric(10, 2))
    change_percent = Column(Numeric(10, 4))
    volume = Column(BigInteger)
    amount = Column(Numeric(20, 2))
    
    ma5 = Column(Numeric(10, 2))
    ma10 = Column(Numeric(10, 2))
    ma20 = Column(Numeric(10, 2))
    ma60 = Column(Numeric(10, 2))


class Position(Base):
    """持仓记录表"""
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    symbol = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50))
    
    quantity = Column(BigInteger, default=0)
    available_quantity = Column(BigInteger, default=0)
    frozen_quantity = Column(BigInteger, default=0)
    
    cost_price = Column(Numeric(10, 2), nullable=False)
    cost_amount = Column(Numeric(20, 2), nullable=False)
    
    current_price = Column(Numeric(10, 2))
    market_value = Column(Numeric(20, 2))
    
    profit = Column(Numeric(20, 2))
    profit_rate = Column(Numeric(10, 4))
    today_profit = Column(Numeric(20, 2))
    
    status = Column(String(20), default="active")
    
    open_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="positions")
    account = relationship("Account", back_populates="positions")


class Order(Base):
    """交易委托表"""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    symbol = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50))
    order_type = Column(String(20), nullable=False)
    order_style = Column(String(20), default="limit")
    
    order_price = Column(Numeric(10, 2), nullable=False)
    order_quantity = Column(BigInteger, nullable=False)
    filled_quantity = Column(BigInteger, default=0)
    unfilled_quantity = Column(BigInteger)
    
    filled_amount = Column(Numeric(20, 2), default=0)
    total_amount = Column(Numeric(20, 2))
    
    status = Column(String(20), default="pending", index=True)
    
    exchange_order_id = Column(String(50))
    reject_reason = Column(Text)
    
    order_time = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    filled_time = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    account = relationship("Account", back_populates="orders")
    trade_logs = relationship("TradeLog", back_populates="order", cascade="all, delete-orphan")


class TradeLog(Base):
    """交易流水表"""
    __tablename__ = "trade_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    symbol = Column(String(10), nullable=False, index=True)
    trade_type = Column(String(20), nullable=False)
    trade_price = Column(Numeric(10, 2), nullable=False)
    trade_quantity = Column(BigInteger, nullable=False)
    trade_amount = Column(Numeric(20, 2), nullable=False)
    
    commission = Column(Numeric(10, 2), default=0)
    stamp_tax = Column(Numeric(10, 2), default=0)
    transfer_fee = Column(Numeric(10, 2), default=0)
    
    exchange_trade_id = Column(String(50))
    
    trade_time = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    order = relationship("Order", back_populates="trade_logs")
    account = relationship("Account", back_populates="trade_logs")


class Strategy(Base):
    """策略配置表"""
    __tablename__ = "strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    description = Column(Text)
    
    symbols = Column(ARRAY(String(10)))
    
    params = Column(JSONB, default=dict)
    
    status = Column(String(20), default="stopped", index=True)
    
    start_time = Column(DateTime(timezone=True))
    stop_time = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="strategies")
    signals = relationship("StrategySignal", back_populates="strategy", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")


class StrategySignal(Base):
    """策略交易信号表"""
    __tablename__ = "strategy_signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    symbol = Column(String(10), nullable=False)
    signal_type = Column(String(20), nullable=False)
    signal_price = Column(Numeric(10, 2), nullable=False)
    signal_reason = Column(Text)
    
    confidence = Column(Numeric(5, 4), default=0.5)
    
    signal_time = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    strategy = relationship("Strategy", back_populates="signals")


class BacktestResult(Base):
    """回测结果表"""
    __tablename__ = "backtest_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    initial_capital = Column(Numeric(20, 2), nullable=False)
    
    total_return = Column(Numeric(10, 4), nullable=False)
    annual_return = Column(Numeric(10, 4))
    benchmark_return = Column(Numeric(10, 4))
    alpha = Column(Numeric(10, 4))
    beta = Column(Numeric(10, 4))
    
    sharpe_ratio = Column(Numeric(10, 4))
    sortino_ratio = Column(Numeric(10, 4))
    max_drawdown = Column(Numeric(10, 4))
    max_drawdown_duration = Column(Integer)
    
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Numeric(10, 4))
    avg_profit = Column(Numeric(10, 2))
    avg_loss = Column(Numeric(10, 2))
    profit_factor = Column(Numeric(10, 4))
    
    report = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    strategy = relationship("Strategy", back_populates="backtest_results")


class RiskConfig(Base):
    """风控配置表"""
    __tablename__ = "risk_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    max_drawdown_warning = Column(Numeric(10, 4), default=0.10)
    max_drawdown_critical = Column(Numeric(10, 4), default=0.15)
    
    daily_loss_limit = Column(Numeric(10, 4), default=0.05)
    weekly_loss_limit = Column(Numeric(10, 4), default=0.10)
    monthly_loss_limit = Column(Numeric(10, 4), default=0.15)
    
    max_position_ratio = Column(Numeric(10, 4), default=0.80)
    min_position_ratio = Column(Numeric(10, 4), default=0.30)
    
    single_stock_limit = Column(Numeric(10, 4), default=0.35)
    industry_limit = Column(Numeric(10, 4), default=0.50)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="risk_config")


class RiskAlert(Base):
    """风险预警表"""
    __tablename__ = "risk_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    alert_type = Column(String(50), nullable=False)
    alert_level = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    suggestion = Column(Text)
    
    current_value = Column(Numeric(20, 4))
    threshold_value = Column(Numeric(20, 4))
    
    status = Column(String(20), default="unread")
    
    alert_time = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    handled_time = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="alerts")


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True)
    
    log_level = Column(String(20), nullable=False, index=True)
    module = Column(String(50), index=True)
    action = Column(String(100))
    message = Column(Text)
    
    user_id = Column(UUID(as_uuid=True), index=True)
    
    request_method = Column(String(10))
    request_path = Column(String(200))
    request_ip = Column(String(50))
    
    extra_data = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class FeishuMessage(Base):
    """飞书消息队列表"""
    __tablename__ = "feishu_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    message_type = Column(String(50), nullable=False)
    recipient_open_id = Column(String(100), nullable=False)
    content = Column(JSONB, nullable=False)
    
    status = Column(String(20), default="pending", index=True)
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
