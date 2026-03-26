# 红山量化交易平台 - 后端开发指南

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库初始化

```bash
# 启动 PostgreSQL
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql

# 创建数据库
createdb hongshan_quant

# 或者使用 psql
psql -U postgres
CREATE DATABASE hongshan_quant;
\q
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，配置数据库和飞书信息
```

### 4. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 用户
- `POST /api/users/register` - 用户注册
- `GET /api/users/{user_id}` - 获取用户信息

### 股票行情
- `GET /api/stocks/quote/{symbol}` - 实时行情
- `GET /api/stocks/quotes?symbols=600519,000858` - 批量行情
- `GET /api/stocks/{symbol}/history` - 历史行情
- `GET /api/stocks/{symbol}/kline` - K 线数据
- `GET /api/stocks/{symbol}/info` - 股票信息
- `GET /api/stocks/search?keyword=茅台` - 搜索股票

### 交易委托
- `POST /api/orders/orders?user_id=xxx` - 创建委托
- `GET /api/orders/orders?user_id=xxx` - 委托列表
- `GET /api/orders/orders/{order_id}` - 委托详情
- `POST /api/orders/orders/{order_id}/cancel` - 撤销委托

### 持仓
- `GET /api/positions/positions?user_id=xxx` - 持仓列表
- `GET /api/positions/positions/{symbol}?user_id=xxx` - 单个持仓
- `GET /api/positions/account?user_id=xxx` - 账户信息

### 策略
- `POST /api/strategies/strategies?user_id=xxx` - 创建策略
- `GET /api/strategies/strategies?user_id=xxx` - 策略列表
- `POST /api/strategies/strategies/{id}/start` - 启动策略
- `POST /api/strategies/strategies/{id}/stop` - 停止策略
- `POST /api/strategies/strategies/{id}/backtest` - 执行回测

### 风控
- `GET /api/risk/config?user_id=xxx` - 风控配置
- `PUT /api/risk/config?user_id=xxx` - 更新配置
- `GET /api/risk/alerts?user_id=xxx` - 预警列表
- `POST /api/risk/alerts/{id}/handle` - 处理预警
- `GET /api/risk/metrics?user_id=xxx` - 风险指标

## 数据库模型

详见 `app/models/database.py`

### 核心表
- `users` - 用户账户
- `accounts` - 资金账户
- `stocks` - 股票信息
- `stock_daily_bars` - 历史行情
- `positions` - 持仓记录
- `orders` - 交易委托
- `trade_logs` - 成交记录
- `strategies` - 策略配置
- `backtest_results` - 回测结果
- `risk_configs` - 风控配置
- `risk_alerts` - 风险预警

## 策略开发

### 双均线策略

```python
from app.services.backtest_engine import run_ma_cross_backtest
from datetime import date

result = run_ma_cross_backtest(
    symbols=['600519'],
    start_date=date(2025, 1, 1),
    end_date=date(2026, 3, 26),
    initial_capital=500000,
    params={'short_window': 5, 'long_window': 20}
)

print(f"总收益：{result['total_return']}%")
print(f"夏普比率：{result['sharpe_ratio']}")
```

## 飞书集成

### 发送交易通知

```python
from app.services.feishu_sender import feishu_sender

feishu_sender.send_trade_notification(
    symbol='600519',
    name='贵州茅台',
    order_type='buy',
    price=1688.00,
    quantity=100,
    status='filled'
)
```

### 发送风险预警

```python
feishu_sender.send_risk_alert(
    alert_type='drawdown',
    title='最大回撤预警',
    message='当前回撤达到 8.5%，接近预警线 10%',
    level='warning'
)
```

## 测试回测引擎

```bash
cd hongshan-backend
python app/services/backtest_engine.py
```

## 项目结构

```
hongshan-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── db.py                # 数据库连接
│   ├── models/
│   │   └── database.py      # SQLAlchemy 模型
│   ├── routes/
│   │   ├── users.py         # 用户 API
│   │   ├── stocks.py        # 行情 API
│   │   ├── orders.py        # 交易 API
│   │   ├── positions.py     # 持仓 API
│   │   ├── strategies.py    # 策略 API
│   │   └── risk.py          # 风控 API
│   └── services/
│       ├── backtest_engine.py  # 回测引擎
│       └── feishu_sender.py    # 飞书推送
├── database/
│   └── schema.sql           # 数据库建表脚本
├── .env.example             # 环境变量示例
├── requirements.txt         # Python 依赖
└── README.md               # 本文档
```

## 下一步

1. ✅ 数据库设计 - PostgreSQL 表结构
2. ✅ 后端 API - FastAPI + SQLAlchemy
3. ✅ 行情数据 - akshare 集成
4. ✅ 回测引擎 - 双均线策略
5. ✅ 飞书集成 - 交易通知、风险预警
6. ⏳ 前端联调 - Vue3 + Element Plus
7. ⏳ 实盘模拟 - 模拟交易测试

---

*newhigh-01 🚀*
