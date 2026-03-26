-- 红山量化交易平台数据库设计
-- PostgreSQL 14+

-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================
-- 1. 用户账户表
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    feishu_open_id VARCHAR(100),
    feishu_user_id VARCHAR(100),
    
    -- 账户状态
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'frozen')),
    
    -- 风险等级
    risk_level VARCHAR(20) DEFAULT 'medium' CHECK (risk_level IN ('low', 'medium', 'high')),
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ,
    
    -- 索引
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_feishu (feishu_open_id)
);

-- 账户余额表
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 资金信息
    total_assets DECIMAL(20, 2) DEFAULT 0,
    available_cash DECIMAL(20, 2) DEFAULT 0,
    frozen_cash DECIMAL(20, 2) DEFAULT 0,
    market_value DECIMAL(20, 2) DEFAULT 0,
    
    -- 盈亏统计
    total_profit DECIMAL(20, 2) DEFAULT 0,
    total_profit_rate DECIMAL(10, 4) DEFAULT 0,
    today_profit DECIMAL(20, 2) DEFAULT 0,
    today_profit_rate DECIMAL(10, 4) DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE (user_id)
);

-- ============================================
-- 2. 股票信息表
-- ============================================
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    exchange VARCHAR(10) NOT NULL, -- SH, SZ, BJ
    
    -- 基本信息
    industry VARCHAR(50),
    sector VARCHAR(50),
    list_date DATE,
    total_shares DECIMAL(20, 2),
    circulating_shares DECIMAL(20, 2),
    
    -- 实时行情
    current_price DECIMAL(10, 2),
    pre_close DECIMAL(10, 2),
    open_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    volume BIGINT,
    amount DECIMAL(20, 2),
    change_percent DECIMAL(10, 4),
    
    -- 更新时间
    quote_time TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_stocks_symbol (symbol),
    INDEX idx_stocks_name (name),
    INDEX idx_stocks_industry (industry)
);

-- 历史行情表 (日线)
CREATE TABLE stock_daily_bars (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    
    -- OHLCV
    open DECIMAL(10, 2) NOT NULL,
    high DECIMAL(10, 2) NOT NULL,
    low DECIMAL(10, 2) NOT NULL,
    close DECIMAL(10, 2) NOT NULL,
    pre_close DECIMAL(10, 2),
    change DECIMAL(10, 2),
    change_percent DECIMAL(10, 4),
    volume BIGINT,
    amount DECIMAL(20, 2),
    
    -- 技术指标 (可选)
    ma5 DECIMAL(10, 2),
    ma10 DECIMAL(10, 2),
    ma20 DECIMAL(10, 2),
    ma60 DECIMAL(10, 2),
    
    -- 约束
    UNIQUE (symbol, trade_date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_bars_symbol_date (symbol, trade_date DESC),
    INDEX idx_bars_date (trade_date)
);

-- ============================================
-- 3. 持仓记录表
-- ============================================
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    
    -- 股票信息
    symbol VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    
    -- 持仓信息
    quantity BIGINT NOT NULL DEFAULT 0,
    available_quantity BIGINT NOT NULL DEFAULT 0,
    frozen_quantity BIGINT NOT NULL DEFAULT 0,
    
    -- 成本信息
    cost_price DECIMAL(10, 2) NOT NULL,
    cost_amount DECIMAL(20, 2) NOT NULL,
    
    -- 当前市值
    current_price DECIMAL(10, 2),
    market_value DECIMAL(20, 2),
    
    -- 盈亏
    profit DECIMAL(20, 2),
    profit_rate DECIMAL(10, 4),
    today_profit DECIMAL(20, 2),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    
    -- 时间戳
    open_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE (user_id, symbol),
    
    -- 索引
    INDEX idx_positions_user (user_id),
    INDEX idx_positions_symbol (symbol)
);

-- ============================================
-- 4. 交易委托表
-- ============================================
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    
    -- 委托信息
    symbol VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('buy', 'sell')),
    order_style VARCHAR(20) DEFAULT 'limit' CHECK (order_style IN ('limit', 'market')),
    
    -- 价格数量
    order_price DECIMAL(10, 2) NOT NULL,
    order_quantity BIGINT NOT NULL,
    filled_quantity BIGINT DEFAULT 0,
    unfilled_quantity BIGINT,
    
    -- 金额
    filled_amount DECIMAL(20, 2) DEFAULT 0,
    total_amount DECIMAL(20, 2),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'partial_filled', 'filled', 'cancelled', 'rejected')
    ),
    
    -- 交易所返回
    exchange_order_id VARCHAR(50),
    reject_reason TEXT,
    
    -- 时间戳
    order_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    filled_time TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_orders_user (user_id),
    INDEX idx_orders_symbol (symbol),
    INDEX idx_orders_status (status),
    INDEX idx_orders_time (order_time DESC)
);

-- 交易流水表
CREATE TABLE trade_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    
    -- 成交信息
    symbol VARCHAR(10) NOT NULL,
    trade_type VARCHAR(20) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    trade_price DECIMAL(10, 2) NOT NULL,
    trade_quantity BIGINT NOT NULL,
    trade_amount DECIMAL(20, 2) NOT NULL,
    
    -- 费用
    commission DECIMAL(10, 2) DEFAULT 0,
    stamp_tax DECIMAL(10, 2) DEFAULT 0,
    transfer_fee DECIMAL(10, 2) DEFAULT 0,
    
    -- 交易所返回
    exchange_trade_id VARCHAR(50),
    
    -- 时间戳
    trade_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_trades_order (order_id),
    INDEX idx_trades_user (user_id),
    INDEX idx_trades_symbol (symbol),
    INDEX idx_trades_time (trade_time DESC)
);

-- ============================================
-- 5. 策略配置表
-- ============================================
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 策略信息
    name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL, -- 双均线，MACD, RSI, 布林带等
    description TEXT,
    
    -- 交易标的
    symbols TEXT[], -- 股票代码数组
    
    -- 策略参数 (JSON)
    params JSONB DEFAULT '{}',
    
    -- 运行状态
    status VARCHAR(20) DEFAULT 'stopped' CHECK (status IN ('running', 'stopped', 'paused')),
    
    -- 运行时间
    start_time TIMESTAMPTZ,
    stop_time TIMESTAMPTZ,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_strategies_user (user_id),
    INDEX idx_strategies_status (status)
);

-- 策略交易信号表
CREATE TABLE strategy_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- 信号信息
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('buy', 'sell', 'hold')),
    signal_price DECIMAL(10, 2) NOT NULL,
    signal_reason TEXT,
    
    -- 信号强度
    confidence DECIMAL(5, 4) DEFAULT 0.5,
    
    -- 时间戳
    signal_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_signals_strategy (strategy_id),
    INDEX idx_signals_time (signal_time DESC)
);

-- 回测结果表
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 回测区间
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- 初始资金
    initial_capital DECIMAL(20, 2) NOT NULL,
    
    -- 收益指标
    total_return DECIMAL(10, 4) NOT NULL,
    annual_return DECIMAL(10, 4),
    benchmark_return DECIMAL(10, 4),
    alpha DECIMAL(10, 4),
    beta DECIMAL(10, 4),
    
    -- 风险指标
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    max_drawdown_duration INT, -- 最大回撤持续天数
    
    -- 交易统计
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    win_rate DECIMAL(10, 4),
    avg_profit DECIMAL(10, 2),
    avg_loss DECIMAL(10, 2),
    profit_factor DECIMAL(10, 4),
    
    -- 回测报告 (JSON)
    report JSONB,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_backtest_strategy (strategy_id),
    INDEX idx_backtest_user (user_id)
);

-- ============================================
-- 6. 风控配置表
-- ============================================
CREATE TABLE risk_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 回撤控制
    max_drawdown_warning DECIMAL(10, 4) DEFAULT 0.10, -- 10%
    max_drawdown_critical DECIMAL(10, 4) DEFAULT 0.15, -- 15%
    
    -- 亏损控制
    daily_loss_limit DECIMAL(10, 4) DEFAULT 0.05, -- 5%
    weekly_loss_limit DECIMAL(10, 4) DEFAULT 0.10, -- 10%
    monthly_loss_limit DECIMAL(10, 4) DEFAULT 0.15, -- 15%
    
    -- 仓位控制
    max_position_ratio DECIMAL(10, 4) DEFAULT 0.80, -- 80%
    min_position_ratio DECIMAL(10, 4) DEFAULT 0.30, -- 30%
    
    -- 集中度控制
    single_stock_limit DECIMAL(10, 4) DEFAULT 0.35, -- 35%
    industry_limit DECIMAL(10, 4) DEFAULT 0.50, -- 50%
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 风险预警表
CREATE TABLE risk_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 预警信息
    alert_type VARCHAR(50) NOT NULL, -- drawdown, loss, concentration, var, etc.
    alert_level VARCHAR(20) NOT NULL CHECK (alert_level IN ('info', 'warning', 'critical')),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    suggestion TEXT,
    
    -- 相关数据
    current_value DECIMAL(20, 4),
    threshold_value DECIMAL(20, 4),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'unread' CHECK (status IN ('unread', 'read', 'handled')),
    
    -- 时间戳
    alert_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    handled_time TIMESTAMPTZ,
    
    -- 索引
    INDEX idx_alerts_user (user_id),
    INDEX idx_alerts_level (alert_level),
    INDEX idx_alerts_status (status),
    INDEX idx_alerts_time (alert_time DESC)
);

-- ============================================
-- 7. 系统日志表
-- ============================================
CREATE TABLE system_logs (
    id BIGSERIAL PRIMARY KEY,
    
    -- 日志信息
    log_level VARCHAR(20) NOT NULL, -- DEBUG, INFO, WARNING, ERROR
    module VARCHAR(50),
    action VARCHAR(100),
    message TEXT,
    
    -- 用户信息
    user_id UUID,
    
    -- 请求信息
    request_method VARCHAR(10),
    request_path VARCHAR(200),
    request_ip VARCHAR(50),
    
    -- 额外数据 (JSON)
    extra_data JSONB,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_logs_level (log_level),
    INDEX idx_logs_module (module),
    INDEX idx_logs_time (created_at DESC),
    INDEX idx_logs_user (user_id)
);

-- ============================================
-- 8. 飞书消息队列表
-- ============================================
CREATE TABLE feishu_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 消息信息
    message_type VARCHAR(50) NOT NULL, -- trade_notification, risk_alert, daily_report
    recipient_open_id VARCHAR(100) NOT NULL,
    content JSONB NOT NULL,
    
    -- 发送状态
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_messages_status (status),
    INDEX idx_messages_time (created_at DESC)
);

-- ============================================
-- 初始化数据
-- ============================================

-- 默认风控配置
INSERT INTO risk_configs (user_id, max_drawdown_warning, max_drawdown_critical)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 0.10, 0.15);

-- 评论
COMMENT ON TABLE users IS '用户账户表';
COMMENT ON TABLE accounts IS '账户余额表';
COMMENT ON TABLE stocks IS '股票信息表';
COMMENT ON TABLE stock_daily_bars IS '股票历史行情表 (日线)';
COMMENT ON TABLE positions IS '持仓记录表';
COMMENT ON TABLE orders IS '交易委托表';
COMMENT ON TABLE trade_logs IS '交易流水表';
COMMENT ON TABLE strategies IS '策略配置表';
COMMENT ON TABLE strategy_signals IS '策略交易信号表';
COMMENT ON TABLE backtest_results IS '回测结果表';
COMMENT ON TABLE risk_configs IS '风控配置表';
COMMENT ON TABLE risk_alerts IS '风险预警表';
COMMENT ON TABLE system_logs IS '系统日志表';
COMMENT ON TABLE feishu_messages IS '飞书消息队列表';
