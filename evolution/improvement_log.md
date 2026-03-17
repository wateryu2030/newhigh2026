# 改进日志

## 2026-03-17

### 执行时间
2026-03-17 16:00 (Asia/Shanghai)

### 执行内容

1. **静态分析（pylint）**
   - 初始评分：9.38/10
   - 最终评分：9.59/10
   - 提升：+0.21 分

2. **修复问题分类**

   **strategy-engine 日志 f-string 修复：**
   - `data_fetcher.py`: 修复 5+ 处 logging f-string → lazy % formatting
   - `main.py`: 修复 10+ 处 logging f-string
   - `news_analyzer.py`: 修复 8+ 处 logging f-string
   - `ai_decision.py`: 修复 getLogger f-string
   - `notification.py`: 修复 getLogger f-string

   **wechat_collector.py 代码质量提升：**
   - 修复 7 处 redefined-outer-name 警告（重命名 __main__ 变量）
   - 修复 2 处 line-too-long（User-Agent 字符串、logger 调用）
   - 修复 2 处 unnecessary elif/else after return
   - pylint 评分：9.84 → 9.96/10

   **connector_astock_duckdb.py 格式化：**
   - 使用 autopep8 自动格式化超长行
   - 部分长 SQL 语句已拆分

3. **验证测试**
   - data-engine 测试：4/4 通过
   - strategy-engine 测试：2/2 通过
   - 无破坏性更改

### 遗留问题
- connector_tushare.py: W0407 误报（已使用 `import pandas as pd`）
- connector_astock_duckdb.py: 7 处 C0301（SQL 语句过长，需手动优化）
- wechat_collector.py: 1 处 TODO 注释（降级模式待实现）

### 下一步计划
1. 手动优化 connector_astock_duckdb.py 的超长 SQL 语句
2. 调查 connector_tushare.py 的 pylint 误报原因
3. 实现 wechat_collector.py 的降级模式

---

## 2026-03-15

### 修改内容

1. **修复嵌套过深问题 (R1702)**
   - 重构 `strategy-engine/src/strategy_engine/ai_fusion_strategy.py` 的 `generate_signals` 方法
   - 提取 `_get_candidate_codes_bullish` 和 `_get_candidate_codes_normal` 辅助方法
   - 使用提前返回（early return）减少嵌套层级
   - 嵌套深度：6 层 → 3 层

2. **统一导入别名规范 (W0407)**
   - 修改 10 个文件的 datetime 导入为 `import datetime as dt`
   - 更新所有相关用法：`datetime.now()` → `dt.datetime.now()`, `timezone.utc` → `dt.timezone.utc`
   - 修复变量命名冲突（避免 `dt` 变量遮蔽模块）
   - 受影响文件:
     - `data-engine/src/data_engine/data_pipeline.py`
     - `data-engine/src/data_engine/realtime_stream.py`
     - `data-engine/src/data_engine/connector_tushare.py`
     - `data-engine/src/data_engine/connector_akshare.py`
     - `data-engine/src/data_engine/connector_astock_duckdb.py`
     - `data-engine/src/data_engine/connector_binance.py`
     - `data-engine/src/data_engine/connector_yahoo.py`
     - `data-engine/src/data_engine/clickhouse_storage.py`
     - `core/src/core/types.py`

3. **修复 OHLCV 构造函数调用**
   - 修复 `connector_tushare.py` 中错误的 OHLCV 构造函数调用
   - 移除不存在的参数 (`amount`, `code`)
   - 添加必需参数 (`symbol`, `interval`)
   - 修复变量命名冲突 (`ts` 变量遮蔽 tushare 模块)

4. **清理导入语句**
   - 移除重复导入 (`Any` 重复导入)
   - 移除未使用导入 (`Dict`, `Optional`)
   - 统一导入分组顺序

### 验证结果
- pylint 评分：9.33 → 9.60/10 (+0.28)
- 数据引擎测试：`pytest data-engine/tests/` - 10/10 通过
- 策略引擎测试：`pytest strategy-engine/tests/` - 2/2 通过
- 核心测试：`pytest core/tests/` - 2/2 通过
- 功能正常，无破坏性更改

### 预期改进
- 代码可读性提高（减少嵌套）
- 符合 Python 量化行业规范（统一导入别名）
- 消除潜在 bug（变量命名冲突）
- 为后续重构奠定基础

### 下一步计划
1. 修复剩余 R0917 参数过多问题（需要 API 重构）
2. 修复 C0301 长行问题（使用 black 格式化）
3. 消除 R0801 重复代码（提取公共函数）

---

## 2026-03-16 心跳任务执行记录

### 执行时间
2026-03-16 01:55 (Asia/Shanghai)

### 执行内容

1. **生成改进计划**
   - 创建 `improvement_plan_2026-03-16.md`
   - 识别 6 个改进点 (3 个高优先级，2 个中优先级，1 个低优先级)
   - 最高优先级：修复新闻采集器数据源选择器

2. **系统状态检查**
   - core 模块 pylint 评分：9.88/10
   - 新闻采集系统：21% 数据源覆盖率 (3/14)
   - 定时任务：正常运行

3. **待执行改进**
   - 修复 core/types.py 导入 (pylint 误报，已确认代码正确)
   - 安装 feedparser (已确认安装)
   - 修复失效数据源选择器 (待执行)

### 下一步计划
1. 修复 2-3 个财经新闻数据源选择器
2. 集成多源采集器到定时任务
3. 添加数据源健康监控

---

## 2026-03-12

### 修改内容

1. **自动代码格式化**
   - 使用 `autopep8 --in-place --aggressive --aggressive` 修复了以下文件的代码规范问题：
     - `data-engine/src/data_engine/connector_tushare.py` - 修复尾随空格、导入顺序等问题
     - `data-engine/src/data_engine/connector_akshare.py` - 修复异常处理、参数格式等问题
     - `core/src/core/logging_config.py` - 修复行过长、文档缺失等问题

2. **版本控制备份**
   - 在修改前执行了 `git commit -m "Backup before auto-improvement"` 确保安全

### 验证结果
- 运行核心测试：`python -m pytest core/tests/ -v` - 全部通过 (2/2)
- 代码格式化后功能正常，无破坏性更改

### 预期改进
- pylint评分预计从8.15/10提升
- 代码可读性提高
- 符合PEP8规范

### 下一步计划
1. 运行pylint重新评估代码质量
2. 添加缺失的文档字符串
3. 优化异常处理模式
## 2026-03-14 每日自我进化

### 修改内容

1. **静态分析 (pylint)**
   - 运行 pylint 分析 core/, data-engine/, strategy-engine/ 模块
   - 识别出问题最严重的 3 个文件:
     - `ai_decision.py` (80 issues, 8.22/10)
     - `notification.py` (32 issues, 8.85/10)
     - `ai_fusion_strategy.py` (25 issues, 6.27/10)

2. **日志格式化修复**
   - 修复 `ai_decision.py`:
     - 20+ 处 logging-fstring 问题 → lazy % formatting
     - 移除 trailing whitespace
     - 清理未使用的导入 (List, Optional)
     - 评分：8.22/10 → 9.24/10 (+1.02)
   
   - 修复 `notification.py`:
     - 13 处 logging-fstring 问题 → lazy % formatting
     - 修复 List 导入缺失问题
     - 评分：8.85/10 → 9.71/10 (+0.86)

3. **改进计划更新**
   - 创建 `improvement_plan_2026-03-14-daily.md`
   - 记录 5 个优先级改进点
   - 跟踪上次计划完成情况

### 验证结果
- pylint 评分提升:
  - ai_decision.py: 8.22 → 9.24 (+12.2%)
  - notification.py: 8.85 → 9.71 (+9.7%)
- 日志性能优化 (lazy evaluation)
- 符合 pylint 最佳实践

### 下一步计划
1. 修复 `main.py` 中的成员调用错误 (6.79/10)
2. 优化 `ai_fusion_strategy.py` 的函数复杂度 (6.27/10)
3. 统一导入规范 (datetime → dt, pandas → pd)

### 工具脚本
- `evolution/fix_logging.py` - 自动修复 logging f-string
- `evolution/fix_notification.py` - 修复 notification.py 特定问题
- `evolution/fix_remaining_logging.py` - 修复剩余 logging 问题

---

## 2026-03-14 (下午) - 导入问题修复

### 修改内容

1. **ai_fusion_strategy.py 导入重构**
   - 将所有函数内部导入移至模块顶层
   - 添加可选依赖的优雅降级处理：
     - `EmotionCycleModel` (ai_models)
     - `get_conn, get_db_path, ensure_tables` (data_pipeline)
   - 修复未使用变量警告（fund_s → _fund_s）
   - 消除 15+ 个 C0415 (import-outside-toplevel) 警告
   - 消除 8+ 个 E0401 (import-error) 警告

2. **代码格式化**
   - 运行 autopep8 自动格式化
   - 修复尾随空格问题

### 验证结果
- pylint 评分：6.27 → 9.75/10 (+55.8%)
- 策略引擎测试：`pytest strategy-engine/tests/ -v` - 全部通过 (2/2)
- 功能正常，无破坏性更改

### 经验总结
- 模块级导入使依赖关系更清晰
- 可选依赖使用 try/except + 标志变量是最佳实践
- 导入错误在启动时即可发现，而非运行时

---

## 2026-03-15 代码规范与测试完善

### 修改内容

1. **connector_akshare.py**
   - `split(".")[0]` 全部改为 `split(".", maxsplit=1)[0]`（3 处）
   - 抽取 `_fetch_bse_stock_list()` 降低 `get_stock_list_akshare` 嵌套，消除 R1702

2. **全库 split 规范（C0207）**
   - backtest_engine/data_loader.py、connector_tushare.py、connector_astock_duckdb.py
   - ensure_ashare_data_completeness.py、daily_kline.py、market_service.py、gateway/endpoints.py
   - social_analyzer.py、ashare_daily_kline.py 等共 10+ 处统一使用 maxsplit=1

3. **pyproject.toml 与 run_tests.sh**
   - testpaths 与脚本一致：补全 strategy/portfolio/risk/scheduler/gateway、evolution 各模块、openclaw_engine、ai-models、backtest-engine、execution-engine、market-scanner
   - run_tests.sh 增加 openclaw_engine 与四模块分轮次冒烟测试

4. **新增冒烟测试**
   - ai-models/tests/test_ai_models_smoke.py
   - backtest-engine/tests/test_backtest_smoke.py
   - execution-engine/tests/test_execution_smoke.py
   - market-scanner/tests/test_market_scanner_smoke.py

### 验证结果
- `bash scripts/run_tests.sh` 全量通过（含四模块冒烟测试）
- 无破坏性更改，data-engine 等原有测试均通过

### 下一步计划
- 继续按 improvement_plan.md 做中低优先级：统一导入别名（W0407）、长行优化（C0301）
- 目标 pylint 9.5/10+

---

## 2026-03-15（下午）自动化规范与长行

### 修改内容

1. **W0407 统一导入别名（import datetime as dt）**
   - data-pipeline 采集器：caixin_news.py, longhubang.py, fund_flow.py, limit_up.py, realtime_quotes.py, official_news.py
   - data-pipeline 数据源：ashare_longhubang.py
   - 所有 `datetime.datetime` / `datetime.timedelta` 改为 `dt.datetime` / `dt.timedelta`

2. **C0301 长行**
   - autopep8 --aggressive --max-line-length 100 处理 data-engine、strategy-engine
   - black --line-length 100 格式化 ai_fusion_strategy.py 等

3. **自动化脚本**
   - `scripts/run_quality_automation.sh`：依次执行格式化 → pylint 抽检 → 全量测试，可定期或 CI 运行

### 验证结果
- data-engine 关键文件 pylint：9.15/10（connector_akshare/tushare/astock_duckdb）
- `bash scripts/run_tests.sh` 全量通过
- 无破坏性更改

### 一键执行
```bash
bash scripts/run_quality_automation.sh
```

---

## 2026-03-16 特征计算修复与带数据进化

### 1. 特征计算 96831 错误成因与修复

**现象**：`compute_features_to_duckdb.py` 输出 `Written: 0 Symbols: 200 Errors: 96831`。

**原因**：
- `features_daily` 表若由旧逻辑创建或不存在，可能**没有 PRIMARY KEY**。
- DuckDB 的 `ON CONFLICT (symbol, trade_date) DO UPDATE` 要求冲突列上有 UNIQUE/PRIMARY KEY，否则报 `Binder Error: ... are not referenced by a UNIQUE/PRIMARY KEY CONSTRAINT`，导致每条 INSERT 都失败。

**修复**（`scripts/compute_features_to_duckdb.py`）：
1. 写入前执行 `CREATE TABLE IF NOT EXISTS features_daily (..., PRIMARY KEY (symbol, trade_date))`。
2. 若首次 INSERT 仍报上述 Binder 错误，则 **DROP TABLE features_daily** 后按带主键的 schema 重新 **CREATE TABLE**，再重试该条插入；后续插入正常。
3. `sym.split(".")` 改为 `sym.split(".", maxsplit=1)`（C0207）。
4. 可选：`DEBUG_FEATURES=1` 时打印首条 INSERT 异常，便于排查。

**验证**：同轮进化中特征计算输出 **Written: 96838 Symbols: 200 Errors: 0**，全量测试通过。

### 2. 带数据补全的进化一轮

- 执行：`python scripts/openclaw_evolution_cycle.py`（未加 `--no-ensure-data`）。
- 数据：A 股/北交所补全 Filled 224、Skipped 285、Errors 0；market 表更新；特征计算 96838 行写入、0 错误。
- 测试：全模块通过。
- 策略循环：generate_strategies → backtest_strategies → score_alpha → evolve_population → deploy_top_strategies 已跑完。

### 3. improvement_plan 小进化

- **core/data_service/db.py**：将 `import duckdb` 从 `get_conn()` 内移到模块顶部（C0415），并用 `try/except ImportError` 赋 `duckdb = None`，避免函数内导入。

