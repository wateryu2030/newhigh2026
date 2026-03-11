# 红山量化 / newhigh 文档

**A 股量化 + 情绪/游资/主线 AI 分析 + 统一调度 + 回测/策略市场/资金曲线/决策解释** 的前后端一体平台；目标演进为「AI 生成策略 → 回测评估 → 自动交易」的 AI 基金经理系统。

## 快速开始

- **统一调度**：`python -m system_core.system_runner`（或 `--once`）
- **API**：`uvicorn gateway.app:app --host 0.0.0.0 --port 8000`
- **前端**：`cd frontend && npm run dev`
- **Docker**：`docker compose up`（redis + api + frontend）

## 文档索引

| 文档 | 说明 |
|------|------|
| [架构](ARCHITECTURE.md) | 系统架构与数据流 |
| [改进计划](OPENCLAW_IMPROVEMENT_PLAN.md) | OpenClaw 阶段 0–3 任务分解 |
| [数据与进化](DATA_AND_EVOLUTION.md) | 数据管道与进化引擎 |
| [交接说明](PROJECT_HANDOFF_FOR_AI.md) | 供 AI 接力的状态与建议维度 |
| [项目状态](../PROJECT_STATUS.md) | 详细模块与目录说明 |
| [监控](monitoring.md) | Prometheus / Grafana |

## 构建本站

```bash
pip install mkdocs mkdocs-material
mkdocs build
mkdocs serve
```
