# Cursor 交接说明 — NewHigh 量化交易平台

> 最后提交: `57f5d21` | 时间: 2026-07-23 | 前手: WorkBuddy (研股股)

## 项目概览

量化交易平台，微服务架构，包含：
- **Gateway** (FastAPI, port 8000) — API 网关，DuckDB 数据层
- **Frontend** (Next.js 14.2, port 3000) — 管理面板
- **Backtest Engine** (Python) — vectorbt 回测
- **Risk Engine** (Python) — 风控规则引擎
- **Execution Engine** (Python) — 信号执行/订单管理
- **Data Pipeline** — K线/财务数据采集
- **Strategy Engine** — AI 融合策略

## 启动方式

### 1. Gateway
```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate
cd gateway && python -m uvicorn gateway.app:app --host 0.0.0.0 --port 8000
```

### 2. Frontend（关键!）
```bash
cd /Users/apple/Ahope/newhigh/frontend

# 生产模式（推荐，稳定）
npx next build && npx next start -p 3000

# 开发模式（必须清空 NODE_OPTIONS）
NODE_OPTIONS='' npx next dev -p 3000
```

## ⚠️ 重要注意事项

### 1. 登录认证已去除
所有路由免登录可直接访问。修改涉及：
- `frontend/src/components/AuthGate.tsx` — 直接 return children
- `frontend/src/components/Sidebar.tsx` / `MobileBottomNav.tsx` / `MobileDrawer.tsx` / `TopBar.tsx` — 免登录显示全量菜单
- `frontend/src/api/client.ts` — redirectToLogin 变空函数

后端 JWT 认证默认关闭 (`JWT_AUTH_REQUIRED` 未设 = 不验证)。

### 2. DuckDB 锁冲突
Gateway 的 health check 和 audit middleware 不能同时用 `read_only=False` 连接。
- `endpoints_health.py` 已改为 `read_only=True`
- 写操作通过 `ensure_tables()` 等单独路径处理

### 3. Python 虚拟环境
```bash
source /Users/apple/Ahope/newhigh/.venv/bin/activate
```
所有 Python 模块均通过 `pip install -e` 以 editable 模式安装。

### 4. .next 缓存
- 已在 `.gitignore` 中排除
- 首次运行需 `next build`
- 如遇 chunk 找不到的错误，`rm -rf .next && next build`

### 5. 远程仓库
```
git@github.com:wateryu2030/newhigh2026.git
main 分支
```

## 当前运行状态（2026-07-23）
- Gateway: localhost:8000 — 正常，health ok，1.7M K线数据
- Frontend: localhost:3000 — 生产模式运行，所有路由 200
- Backtest: 107 只股票回测完成，strategy_market 表有数据
- Scheduler: com.newhigh.scheduler LaunchAgent 需手动 launchctl load

## 遗留问题
- com.newhigh.scheduler LaunchAgent 需要 root 权限手动加载（sandbox 限制）
- 前端路由 `/login` `/register` 仍可访问（页面已降级处理但未删除）
