# Hongshan 子栈（与 newhigh 主仓对齐）

本目录由 OpenClaw 工作区 **`hongshan-backend` + `hongshan-quant-platform`** 迁入，与主工程 **共享同一 Git 仓库**，便于统一迭代；运行时与 **newhigh `gateway/`（默认 8000）** 并行，**不占用 8000**。

## 端口（避免冲突）

| 服务 | 宿主机端口 | 说明 |
|------|------------|------|
| Hongshan API | **8010** | FastAPI，`/docs` 为 `http://127.0.0.1:8010/docs` |
| Hongshan Vue（Docker Nginx） | **9080** | `http://127.0.0.1:9080` |
| PostgreSQL | **5433** | 库名 `hongshan_quant` |
| Redis | **6380** | 与 `cache.py` 中 `REDIS_HOST` 在容器内为 `redis` |
| newhigh Gateway | 8000 | 主栈，不在此启动 |
| 政策新闻 API（SQLite + FastAPI） | **8001** | `hongshan-quant-platform/start-news-api.sh`，实现代码在 `policy-news/`；Vue 开发时 `/news` 走 Vite 代理 |

## Docker 一键启动

```bash
cd integrations/hongshan
export HONGSHAN_DB_PASSWORD=your_secret   # 可选，默认 hongshan_dev
docker compose up -d --build
```

- API 文档：<http://127.0.0.1:8010/docs>
- 前端：<http://127.0.0.1:9080>

## 本地开发（与 Next 主前端并存）

1. 启动本目录数据库与 Redis（或仅 `docker compose up -d postgres redis`），再在本机起后端：
   ```bash
   cd hongshan-backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   export DB_HOST=127.0.0.1 DB_PORT=5433 DB_PASSWORD=hongshan_dev REDIS_HOST=127.0.0.1 REDIS_PORT=6380
   uvicorn app.main:app --reload --port 8010
   ```
2. Vue：端口 **5174**，已配置将 `/api`、`/ws` 代理到 **8010**（见 `hongshan-quant-platform/vite.config.js`）。
   ```bash
   cd hongshan-quant-platform
   npm ci
   npm run dev
   ```

## 与主 newhigh 的关系

- **主前端**：`frontend/`（Next.js） continuing 为产品主界面；本 Vue 栈为 **对齐迁入的合规副栈**，可按模块逐步把 API 迁到 `gateway/`（颠覆性合并需单独决策）。
- **OpenClaw 原文档**：`docs/OPENCLAW_WORKSPACE_DELIVERY.md`
