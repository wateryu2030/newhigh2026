# Cursor + OpenClaw 可执行任务

以下命令可由 Cursor 或本地终端直接执行，用于进化开发循环与状态查看。

## 1. OpenClaw 策略进化全流程

```bash
bash scripts/cursor_evolution_cycle.sh
```

- **前置**：Gateway 已启动（`uvicorn gateway.app:app --host 127.0.0.1 --port 8000`）
- **步骤**：触发进化任务 → 轮询直至完成 → 代码检查（black/isort）→ 前后端联调检查 → 刷新 system_core 状态
- **完成后**：访问 http://localhost:3000/system-monitor 查看 OpenClaw 进化任务与 Skill 统计

## 2. 查看系统状态（含进化与 Skill）

```bash
curl -s http://127.0.0.1:8000/api/system/status | python3 -m json.tool
```

或仅查看最近进化任务与 Skill 统计：

```bash
curl -s http://127.0.0.1:8000/api/evolution/tasks?limit=5
curl -s http://127.0.0.1:8000/api/skill/stats
```

## 3. 仅触发进化（不轮询）

```bash
curl -s -X POST "http://127.0.0.1:8000/api/evolution/trigger?task_type=strategy_generation"
```

返回 `task_id`，可用 `GET /api/evolution/status/{task_id}` 轮询。

## 4. 前后端联调检查

```bash
bash scripts/check_frontend_backend.sh
```

需 Gateway 已启动；可选环境变量 `API_BASE` 指定其他地址。

## 5. OpenClaw 设计检查

```bash
bash scripts/openclaw_check_design.sh
```

或重启 Gateway 并检查：

```bash
bash scripts/restart_and_check.sh
```
