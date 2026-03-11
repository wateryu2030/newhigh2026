# A股 AI 交易终端 — 完整生产级方案

**目标**：能持续运行、能产生策略、能交易、能自进化的红山量化平台系统。

---

## 一、六大能力与最终结构

| 能力 | 说明 | 对应模块 |
|------|------|----------|
| 数据能力 | 股票池、K线、实时、资金流、涨停、龙虎榜 | data-pipeline |
| 扫描能力 | 实时监控涨停/资金流/量价/板块/趋势 | market-scanner |
| 分析能力 | 情绪周期、游资识别、资金轮动 | ai-models |
| 策略能力 | 游资/趋势/情绪/轮动策略 → 交易信号 | strategy-engine |
| 回测能力 | 策略回测、绩效分析 | backtest-engine |
| 交易能力 | 信号执行、仓位与风控 | execution-engine + risk-engine |

**数据流**：

```
A股市场(AkShare)
    ↓
Data Pipeline (data-pipeline)
    ↓
DuckDB (data/market.duckdb)
    ↓
Market Scanner (market-scanner) → market_signals
    ↓
AI Models (ai-models) → market_emotion_state, hotmoney_signals, sector_strength
    ↓
Strategy Engine (strategy-engine) → trade_signals
    ↓
Backtest (backtest-engine) / Auto Trader (execution-engine)
    ↓
API (gateway) → Frontend (frontend)
```

---

## 二、仓库模块映射（newhigh 统一方案）

| 方案中的模块 | newhigh 实现 | 说明 |
|--------------|--------------|------|
| data_pipeline | data-pipeline/ | 采集、ETL、调度、storage |
| database | data/market.duckdb + data/quant.duckdb | 管道表 + 标的/日线/特征/回测结果 |
| market_scanner | market-scanner/ | limit_up/fund_flow/volume_spike/sector/trend 扫描 → market_signals；hotmoney_sniper → sniper_candidates |
| ai_models | ai-models/ | emotion_cycle, hotmoney_detector, sector_rotation_ai |
| strategy_engine | strategy-engine/ | trend/hotmoney/emotion/rotation 策略 → trade_signals |
| backtest | backtest-engine/ | 回测引擎、绩效分析 |
| auto_trader | execution-engine/ + risk-engine/ | 信号执行、仓位、风控、订单路由 |
| api | gateway/ | FastAPI，/market/*, /strategy/signals, /market/emotion |
| frontend | frontend/ | Next.js，Dashboard/Market/Signals/Strategy/Backtest 等 |
| ai_optimizer | scheduler/ + evolution-engine/ | 参数优化、策略淘汰、OpenClaw 自进化 |

---

## 三、数据表（market.duckdb）

| 表 | 用途 |
|----|------|
| a_stock_basic | 股票池 |
| a_stock_daily | 日K |
| a_stock_realtime | 实时行情 |
| a_stock_fundflow | 资金流 |
| a_stock_limitup | 涨停池 |
| a_stock_longhubang | 龙虎榜 |
| market_signals | 扫描信号（signal_type: limitup/fundflow/volume/trend/sector） |
| market_emotion_state | 情绪周期状态（启动/主升/高潮/退潮/冰点） |
| market_emotion | 情绪周期每日指标（trade_date, limitup_count, max_height, market_volume, emotion_state） |
| hotmoney_signals | 游资席位信号 |
| top_hotmoney_seats | 顶级游资席位（席位名、胜率、平均收益） |
| sector_strength | 板块强度 |
| main_themes | 主线题材（sector, total_volume, rank） |
| trade_signals | 交易信号（code, signal, confidence, target_price, stop_loss, signal_score） |
| sniper_candidates | 游资狙击候选（code, theme, sniper_score, confidence），Sniper Score > 0.7 |

---

## 四、运行流程

**交易日盘中**：

1. 实时行情更新（data-pipeline scheduler，每 30s）
2. 市场扫描（market-scanner 读 a_stock_*，写 market_signals）
3. AI 分析（ai-models 读 pipeline/scan 数据，写 emotion/hotmoney/sector）
4. 策略生成（strategy-engine 读 signals，写 trade_signals）
5. 信号推送 / 自动交易（execution-engine + risk-engine）

**收盘后**：

- 回测、模型训练、参数优化（backtest-engine + ai_optimizer）
- OpenClaw 进化循环：策略池 → 评分 → 淘汰/进化

---

## 五、API 清单

| 接口 | 说明 |
|------|------|
| GET /api/market/realtime | 实时行情 |
| GET /api/market/limitup | 涨停池 |
| GET /api/market/fundflow | 资金流 |
| GET /api/market/emotion | 情绪周期状态 |
| GET /api/market/hotmoney | 游资席位胜率 |
| GET /api/market/main-themes | 主线题材 |
| GET /api/market/sniper-candidates | 游资狙击候选池（Sniper Score） |
| GET /api/strategy/signals | 交易信号 |
| GET /api/dashboard | 控制台聚合 |
| GET /api/stocks | 股票列表 |

---

## 六、前端页面结构

Dashboard | Market | Signals | Hotmoney | Strategy | Backtest | News | Settings

---

## 七、自进化（ai_optimizer）

- 策略参数自动优化（贝叶斯/遗传/强化学习）
- AI 阈值自动调整
- 策略淘汰机制（evolution-engine + alpha-scoring + darwin）

入口：`scripts/openclaw_evolution_cycle.py`，可与数据管道、扫描、策略串联为单日/单轮流程。

---

## 八、一键运行顺序与自动化数据

**保证数据量（首次或定期执行）：**

- **全量填充 market.duckdb**（股票池 + 约 250 日日K + 涨停/龙虎榜/资金流）：
  ```bash
  python scripts/ensure_market_data.py
  ```
  可选：`--days 250 --max-symbols 800`；快速试跑：`--days 60 --max-symbols 300`；仅更新池与涨停/龙虎榜：`--skip-kline`。

- **一键：数据 + 终端单轮**（先填数据再跑扫描 → AI → 融合信号）：
  ```bash
  python scripts/run_full_cycle.py
  ```
  可选：`--skip-data` 只跑终端单轮；`--quick-data` 用 60 日/300 只做快速数据。

**日常顺序：**

1. **数据**（每日一次或首次）：`python scripts/ensure_market_data.py`；或盘中实时：data-pipeline 的 realtime_scheduler。
2. **终端单轮**（扫描 → AI → 策略信号）：`python scripts/run_terminal_loop.py`；或直接 `python scripts/run_full_cycle.py`（含数据步骤）。
3. **服务与检查**：`bash scripts/start_services.sh`（若存在）；或 `uvicorn gateway.app:app --reload --port 8000`。
4. **前端**：`cd frontend && npm run dev`，打开 http://localhost:3000，AI 交易页查看情绪/游资/主线/信号。
5. **自进化**：`python scripts/openclaw_evolution_cycle.py`。

**定时执行（推荐：launchd，锁屏也会跑）：**

- 一键安装（每周一至五 18:30）：`bash scripts/schedule/install_scheduled_run.sh`  
  详见 **scripts/schedule/README.md**。默认执行 `run_full_cycle.py --skip-data`，日志在 `logs/full_cycle.log`。
- 若用 cron（需登录且未休眠）：  
  - 每日 18:30 全量：`30 18 * * 1-5 cd /path/to/newhigh && .venv/bin/python scripts/run_full_cycle.py >> logs/full_cycle.log 2>&1`  
  - 仅数据：`0 18 * * 1-5 cd /path/to/newhigh && .venv/bin/python scripts/ensure_market_data.py >> logs/ensure_market.log 2>&1`

**游资狙击与回测：**

- 终端单轮已包含游资狙击（`run_sniper`），输出写入 `sniper_candidates`，前端 AI 交易页展示「游资狙击」表。
- 回测（T+1 买、T+3 卖）：`python scripts/sniper_backtest.py`，输出胜率、平均收益、成交笔数。

**数据不全与自进化**：见 **docs/DATA_AND_EVOLUTION.md**（改进清单、新闻增强、OpenClaw 数据健康与 ensure_market_data）。

**统一运行核心**：使用 **system_core** 可一键循环「数据 → 扫描 → AI → 策略 → 监控」：`python -m system_core.system_runner`（或 `--once` 单轮）。见 **system_core/README.md**。
