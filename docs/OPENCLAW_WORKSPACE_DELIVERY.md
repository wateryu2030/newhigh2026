# OpenClaw 工作区交付清单（纳入 newhigh 文档索引）

本文件用于在 **newhigh 主仓库** 内索引机器人（OpenClaw）在另一目录完成的交付说明，避免误以为「只有一个代码树」。

| 路径 | 定位 |
|------|------|
| **`/Users/apple/Ahope/newhigh`** | **主工程**：Next.js `frontend/`、`gateway/`、`data-pipeline/`、DuckDB 统一库等（日常迭代以这里为准）。 |
| **`newhigh/integrations/hongshan/`** | **已与主仓对齐的 Hongshan 子栈**：从 OpenClaw 迁入的 `hongshan-backend` + `hongshan-quant-platform`，见该目录 `README.md` 与 `docker-compose.yml`（API **8010**，与主 Gateway **8000** 并存）。 |
| **`/Users/apple/.openclaw/workspace`** | **OpenClaw 原工作区**：独立 Git 仓库；历史提交（如 `2aaa6d1`）仍在该目录 `git log`。后续以 **integrations/hongshan** 为准做统一修改，必要时可再从该目录 rsync 同步。 |

**如何将 OpenClaw 交付「整合进项目」**：

1. **文档**：已把交付清单抄录在下方（与 `PROJECT_DELIVERY.md` 对齐），主仓即可检索。
2. **代码**：两套栈并存；若要把某 API/页面迁入 newhigh，需按模块单独移植（例如对照 Gateway 路由与 Vue 页面），**不会**自动替换现有 `frontend/` / `gateway/`。

---

以下为 OpenClaw 工作区 **`PROJECT_DELIVERY.md`** 原文（更新时间见文末）。

---

# 红山量化交易平台 - 项目交付清单

## 📁 项目结构

```
/Users/apple/.openclaw/workspace/
├── hongshan-backend/              # 后端项目
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 入口
│   │   ├── config.py             # 配置管理
│   │   ├── db.py                 # 数据库连接
│   │   ├── models/
│   │   │   └── database.py       # SQLAlchemy 模型 (15 张表)
│   │   ├── routes/
│   │   │   ├── auth.py           # 用户认证 (JWT)
│   │   │   ├── users.py          # 用户 API
│   │   │   ├── stocks.py         # 行情 API (含 Redis 缓存)
│   │   │   ├── orders.py         # 交易 API
│   │   │   ├── positions.py      # 持仓 API
│   │   │   ├── strategies.py     # 策略 API
│   │   │   ├── risk.py           # 风控 API
│   │   │   └── websocket.py      # WebSocket 实时推送
│   │   └── services/
│   │       ├── backtest_engine.py    # 双均线回测
│   │       ├── macd_strategy.py      # MACD 回测
│   │       ├── rsi_strategy.py       # RSI 回测
│   │       ├── cache.py              # Redis 缓存服务
│   │       └── feishu_sender.py      # 飞书推送
│   ├── database/
│   │   └── schema.sql            # 数据库建表脚本
│   ├── .env.example              # 环境变量模板
│   ├── .env.production           # 生产环境配置
│   ├── Dockerfile                # 后端 Docker 镜像
│   ├── requirements.txt          # Python 依赖
│   └── README.md                 # 后端开发指南
│
├── hongshan-quant-platform/       # 前端项目
│   ├── src/
│   │   ├── api/
│   │   ├── views/                # Login, Market, Trade, ...
│   │   ├── services/
│   │   ├── App.vue
│   │   └── main.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── scripts/
├── memory/
├── docker-compose.yml
├── DEPLOYMENT.md
└── README.md
```

（下列表格与原文一致，略去重复层级以缩短篇幅；完整树见 OpenClaw 目录内原文件。）

## ✅ 核心功能清单

### 后端 API (25 个端点)

| 模块 | 端点 | 说明 |
|------|------|------|
| **用户认证** | POST /api/auth/register | 用户注册 |
| | POST /api/auth/login | 用户登录 (JWT) |
| | GET /api/auth/me | 获取当前用户 |
| **股票行情** | GET /api/stocks/quote/{symbol} | 实时行情 |
| | GET /api/stocks/quotes | 批量行情 |
| | GET /api/stocks/{symbol}/history | 历史行情 |
| | GET /api/stocks/{symbol}/kline | K 线数据 |
| | GET /api/stocks/{symbol}/info | 股票信息 |
| | GET /api/stocks/search | 股票搜索 |
| **交易委托** | POST /api/orders/orders | 创建委托 |
| | GET /api/orders/orders | 委托列表 |
| | GET /api/orders/orders/{id} | 委托详情 |
| | POST /api/orders/orders/{id}/cancel | 撤销委托 |
| **持仓管理** | GET /api/positions/positions | 持仓列表 |
| | GET /api/positions/account | 账户信息 |
| **策略管理** | POST /api/strategies/strategies | 创建策略 |
| | GET /api/strategies/strategies | 策略列表 |
| | POST /api/strategies/{id}/start | 启动策略 |
| | POST /api/strategies/{id}/stop | 停止策略 |
| | POST /api/strategies/{id}/backtest | 执行回测 |
| **风控管理** | GET /api/risk/config | 风控配置 |
| | PUT /api/risk/config | 更新配置 |
| | GET /api/risk/alerts | 预警列表 |
| | GET /api/risk/metrics | 风险指标 |
| **WebSocket** | WS /ws | 实时推送 |

### 前端页面 (6 个)

| 页面 | 路由 | 功能 |
|------|------|------|
| Login.vue | /login | 登录/注册 |
| Market.vue | /market | 行情展示 |
| Trade.vue | /trade | 股票交易 |
| Position.vue | /position | 持仓管理 |
| Strategy.vue | /strategy | 策略管理 |
| Risk.vue | /risk | 风控监控 |

### 量化策略 (3 个)

| 策略 | 文件 | 说明 |
|------|------|------|
| 双均线 | backtest_engine.py | 回测服务内 |
| MACD | macd_strategy.py | 回测服务内 |
| RSI | rsi_strategy.py | 回测服务内 |

## 🚀 快速启动（在 OpenClaw 工作区目录内）

```bash
cd /Users/apple/.openclaw/workspace
docker-compose up -d --build
```

详见该目录下 `DEPLOYMENT.md`、`PROJECT_DELIVERY.md`。

## 📝 Git

在 **OpenClaw 工作区** 内执行：

```bash
cd /Users/apple/.openclaw/workspace
git log --oneline -10
```

机器人曾记录示例提交：`2aaa6d1 docs: 添加项目交付清单`（以该目录实际 `git log` 为准）。

---

*原文更新时间：2026-03-26；抄录进 newhigh 便于与主工程文档一并管理。*
