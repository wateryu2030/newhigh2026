# OpenClaw 执行方案 — 完成情况检查

对照「Cursor + OpenClaw 可执行阶段」控制包逐项核对。

---

## 一、创建项目（第一步）

| 要求 | 当前状态 |
|------|----------|
| 项目目录 | ✅ 已有 `newhigh`（等同 ai-hedge-fund） |
| git init | ✅ 已有 .git |
| 基础结构 docs / frontend / gateway / data-engine / feature-engine / backtest-engine / strategy-engine / portfolio-engine / risk-engine / execution-engine / ai-lab / scheduler / infra | ✅ 全部存在；另多出 core、evolution-engine、ai-fund-manager |

---

## 二、OpenClaw 控制文件

| 要求 | 当前状态 |
|------|----------|
| OPENCLAW_SYSTEM.md | ✅ 已创建（系统蓝图，与执行方案一致） |
| OPENCLAW_AUTONOMOUS_DEV.yaml | ✅ 已有（含 workflow/loop、development_order、rules、validation） |
| OPENCLAW_TASKS.yaml | ✅ 已创建（与执行方案任务命名一致） |
| OPENCLAW_PLAN.md | ✅ 已有（更细的规划，可作补充） |
| OPENCLAW_TASK_TREE.yaml | ✅ 已有（与 TASKS 对应，含 evolution / ai-fund-manager） |

---

## 三、按模块开发（OPENCLAW_TASKS / TASK_TREE）

| 模块 | 任务 | 状态 |
|------|------|------|
| data-engine | create_binance_connector, build_data_pipeline, implement_clickhouse_storage | ✅ 已实现 |
| data-engine | create_yahoo_connector | ⚠️ 未实现（仅 Binance；可后续补） |
| feature-engine | implement_rsi/macd/vwap/atr, build_feature_pipeline | ✅ 已实现 |
| backtest-engine | integrate_vectorbt, implement_backtest_runner, compute_metrics | ✅ 已实现 |
| strategy-engine | trend_following, mean_reversion, breakout | ✅ 已实现 |
| portfolio-engine | equal_weight, risk_parity, kelly_allocation | ✅ 已实现 |
| risk-engine | drawdown_control, exposure_limit, volatility_filter | ✅ 已实现 |
| execution-engine | binance_orders, order_manager | ✅ 已实现 |
| ai-lab | strategy_generator, optuna_optimizer, rl_trader | ✅ 已实现 |
| scheduler | task_scheduler, connect_strategy_pipeline | ✅ 已实现（connect_pipeline） |
| gateway | build_fastapi_api, create_endpoints | ✅ 已实现 |
| frontend | dashboard, strategy_center, backtest_ui, portfolio_ui | ✅ 已实现（含 ai_lab_ui） |

---

## 四、自动循环开发直到系统可运行

| 要求 | 当前状态 |
|------|----------|
| 生成项目代码 | ✅ 各模块已有 src、入口与导出 |
| 依赖 | ✅ requirements.txt + 各模块 pyproject.toml |
| 测试 | ✅ core / data-engine / evolution-engine 有测试，`scripts/run_tests.sh` 可跑 |
| 自动修错 | ✅ 已修 datetime 弃用等 |
| 系统可运行 | ✅ `source .venv/bin/activate && uvicorn gateway.app:app --port 8000` 可启动 API；前端 `npm run dev` 可起 |

---

## 五、第一次运行（docker compose up）

| 要求 | 当前状态 |
|------|----------|
| docker-compose.yml | ✅ 已添加（clickhouse, postgres, redis, api） |
| clickhouse | ✅ 已配置 |
| postgres | ✅ 已配置 |
| redis | ✅ 已配置 |
| api | ✅ 使用 gateway Dockerfile 构建并启动 |
| workers | ⚠️ 未在 compose 中（可后续加 scheduler 等） |

运行方式：

```bash
docker compose up --build
```

---

## 六、第一阶段完成标志

| 能力 | 状态 |
|------|------|
| 下载行情 | ✅ data-engine（Binance + pipeline + ClickHouse） |
| 生成指标 | ✅ feature-engine（RSI/MACD/VWAP/ATR + pipeline） |
| 运行回测 | ✅ backtest-engine（vectorbt + metrics） |
| 生成策略 | ✅ ai-lab（strategy_generator + optuna + rl_trader） |
| 展示 UI | ✅ frontend（Dashboard / Strategy Center / Backtest / Portfolio / AI Lab） |

---

## 七、Cursor 中执行指令（已满足）

以下指令在当前仓库中可直接使用：

```
Read OPENCLAW_SYSTEM.md
Follow OPENCLAW_AUTONOMOUS_DEV.yaml
Use OPENCLAW_TASKS.yaml to generate modules.
Start implementing modules sequentially.
Generate code for each module and ensure tests pass.
```

- 读系统蓝图：OPENCLAW_SYSTEM.md ✅  
- 遵循自动开发流程：OPENCLAW_AUTONOMOUS_DEV.yaml ✅  
- 按任务拆解：OPENCLAW_TASKS.yaml（及 OPENCLAW_TASK_TREE.yaml）✅  
- 按模块顺序实现、补测试：已完成主体实现与部分测试 ✅  

---

## 未完成 / 可后续补

1. **create_yahoo_connector**：data-engine 仅实现 Binance，Yahoo 可在 OPENCLAW_TASKS 下单独加任务补。
2. **workers 服务**：docker-compose 中未起 workers（如 scheduler），需要时可加一 service 调用 scheduler。
3. **commit_each_module**：规则已写在 OPENCLAW_AUTONOMOUS_DEV，需由你在本地执行 git commit。

---

## 总结

- **项目结构、控制文件、按模块开发、系统可运行、第一阶段能力** 均已完成或基本完成。  
- **OPENCLAW_SYSTEM.md、OPENCLAW_TASKS.yaml、docker-compose.yml** 已按你的执行方案补全，可直接进入「Cursor + OpenClaw 可执行阶段」。  
- 可选后续：Yahoo connector、compose 中 workers、以及你提到的「AI Alpha Factory 模块」升级。
