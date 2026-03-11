# newhigh — AI Hedge Fund 新项目

本仓库为 **从零按架构执行** 的 AI 交易操作系统，与旧项目（量化研究工具）分离，避免架构冲突。

## 为何独立新项目

| 维度     | 旧项目     | 本系统       |
|----------|------------|--------------|
| 架构     | 单体应用   | 微服务       |
| 数据     | 本地分析   | 实时数据流   |
| AI       | 辅助分析   | 主导决策     |
| 交易     | 手动/模拟  | 自动执行     |
| 目标形态 | 工具       | AI 基金经理 |

旧项目保留作研究/回测/UI 参考；execution、AI、scheduler 在本项目中重新实现。

## 目录结构

```
newhigh/
  core/
  data-engine/
  feature-engine/
  strategy-engine/
  backtest-engine/
  portfolio-engine/
  risk-engine/
  execution-engine/
  ai-lab/
  evolution-engine/    # 策略进化：Alpha 评分、策略池、达尔文淘汰
  ai-fund-manager/     # AI 基金经理：策略选择、风控、资金配置
  alpha-factory/       # 第二阶段：策略工厂（大量生成候选）
  alpha-scoring/      # Alpha 评分引擎（top 10% 入池）
  strategy-evolution/ # 遗传进化（elite + crossover + mutate）
  simulation-world/   # 市场模拟环境（RL 训练）
  meta-fund-manager/  # AI 基金经理大脑（选策略、分配、监控）
  scheduler/
  gateway/
  frontend/
  infra/
  docs/
```

**架构图（七层 + 进化引擎）：** 见 `docs/ARCHITECTURE.md`。

**Cursor 接续开发：** 读 `docs/vision.md`、`docs/roadmap.md`、`tasks/current_task.md` 即可接力开发；角色提示词在 `ai/prompts/`，说明见 `docs/CURSOR_RELAY.md`。

每个模块含：`src/` `tests/` `Dockerfile` `README.md`。

## OpenClaw 控制文件

**开发控制：**
- **OPENCLAW_PLAN.md** — 系统蓝图
- **OPENCLAW_AUTONOMOUS_DEV.yaml** — 自动开发控制器
- **OPENCLAW_TASK_TREE.yaml** — 任务拆解树

**系统总控与四循环（长期自主运行/进化）：**
- **OPENCLAW_MASTER_SYSTEM.yaml** — 系统总控：数据/策略/交易/AI 开发四循环、模块列表
- **OPENCLAW_DATA_PIPELINE.yaml** — 数据自动生成：行情源、存储、更新频率
- **OPENCLAW_ALPHA_FACTORY.yaml** — 策略进化：生成→回测→评分→进化→部署
- **OPENCLAW_META_FUND.yaml** — AI 基金经理：策略选择、资金配置、监控、换仓
- **OPENCLAW_AI_DEV_AGENT.yaml** — AI 开发代理：自主改代码、跑测、提交
- **FRONTEND_DATA_BINDING.yaml** — 前端数据绑定：页面 ↔ API 映射

**规范说明：** 见 **docs/OPENCLAW_SYSTEM.md**（四循环、API/WebSocket、启动方式）。

**让 Cursor 开始自动开发：** 在 Cursor 中输入：
```
Read all OPENCLAW configuration files.
Initialize autonomous development mode.
Implement missing modules.
Connect database, backend APIs, and frontend data bindings.
Ensure the system generates real data automatically.
Start autonomous strategy evolution loop.
Enable AI development agent for continuous improvement.
```

## 开发顺序（必须按此顺序）

1. data-engine  
2. feature-engine  
3. backtest-engine  
4. strategy-engine  
5. portfolio-engine  
6. risk-engine  
7. execution-engine  
8. ai-lab  
9. scheduler  
10. gateway  
11. frontend  

## 在 Cursor 中执行

```
Read OPENCLAW_PLAN.md
Create project structure.
Follow OPENCLAW_TASK_TREE.yaml
Generate modules sequentially.
```

或由 OpenClaw：`read PLAN → load AUTONOMOUS_DEV → execute()`，循环：生成 → 测试 → 修 bug → 提交 → 下一模块。

## 运行与构建

**本地 Python（从仓库根目录）：**
```bash
# 创建并激活虚拟环境（推荐，避免与系统 Python 冲突）
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖并运行网关
pip install -r requirements.txt
uvicorn gateway.app:app --host 0.0.0.0 --port 8000
```
浏览器访问 http://127.0.0.1:8000/health 和 http://127.0.0.1:8000/api/strategies  
若端口被占用：换端口 `--port 8001` 或执行 `lsof -i :8000 -t | xargs kill` 后重试。

**测试（需先激活 venv）：**
```bash
source .venv/bin/activate
bash scripts/run_tests.sh
# 或分别运行： pytest core/tests/ -v && pytest data-engine/tests/ -v && pytest evolution-engine/tests/ -v
```

**前端：**
```bash
cd frontend && npm install && npm run dev
```

**AI 交易数据与全量执行（保证分析有足够数据）：**
```bash
source .venv/bin/activate
# 安装 data-pipeline / akshare 等依赖后
python scripts/ensure_market_data.py              # 填充 market.duckdb：股票池 + 日K(250日/800只) + 涨停/龙虎榜/资金流
python scripts/run_full_cycle.py                   # 一键：先填数据，再跑扫描→情绪/游资/主线→融合信号
# 快速试跑：python scripts/run_full_cycle.py --quick-data
# 仅生成信号（不拉数据）：python scripts/run_full_cycle.py --skip-data
```
详见 `docs/AI_TRADING_TERMINAL.md` 第八节（定时 cron 示例）。**数据不全、新闻单薄、自进化**：见 `docs/DATA_AND_EVOLUTION.md`。

**A 股数据（与 astock 独立，复制到本仓库）：**
```bash
# 将 astock 的 DuckDB 全量复制到 newhigh/data/quant.duckdb，两套目录互不依赖
python scripts/copy_astock_duckdb_to_newhigh.py
# 可选：指定源/目标
python scripts/copy_astock_duckdb_to_newhigh.py --source /Users/apple/astock/data/quant.duckdb --dest ./data/quant.duckdb
```
复制后 Gateway 的 A 股 K 线、标的列表、新闻接口会从 `data/quant.duckdb` 读。

**Docker（需先启动 Docker  daemon）：**
```bash
# 一键启动 clickhouse / postgres / redis / api
docker compose up --build

# 或单独构建网关
docker build -f gateway/Dockerfile -t newhigh-gateway .
docker run -p 8000:8000 newhigh-gateway
```

## 目标形态

- AI 发现策略 / AI 验证策略 / AI 自动交易 / AI 淘汰策略  
- 人负责：风险限制、资金规模  
- 终点：自进化的红山量化平台核心。
