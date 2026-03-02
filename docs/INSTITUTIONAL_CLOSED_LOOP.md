# 机构级闭环：Cursor + OpenClaw 自动实现方案

能自我验证、统计胜率、持续优化、长期运行的闭环：情绪周期回测验证 + 龙虎榜席位胜率统计 + 游资+趋势融合模型 + 每周调度。

---

## 一、情绪周期回测验证模型（Emotion Backtest Engine）

### 目标

- 验证不同情绪周期下策略表现：冰点买入、加速追龙头、高潮减仓等是否有效。
- 输出各阶段平均收益、胜率、盈亏比、最大回撤、夏普比率。

### 模块结构

```
backtest/
    emotion_labeler.py   # 历史情绪标签生成，缓存 emotion_history.csv
    performance_analyzer.py  # 胜率、盈亏比、最大回撤、夏普
    emotion_backtest.py  # 按情绪分组回测，输出报告
```

### 输出

- `data/emotion_history.csv`：每日情绪标签缓存
- `output/emotion_performance_report.json`：按情绪阶段统计的绩效

### Cursor 执行任务文本（复制执行）

```
任务名称：构建情绪周期回测验证系统

任务目标：
1. 生成过去2年每日情绪标签（backtest/emotion_labeler.py），保存 data/emotion_history.csv
2. 将策略/指数收益按情绪分组（backtest/emotion_backtest.py）
3. 计算不同情绪阶段：平均收益、胜率、盈亏比、最大回撤、夏普比率（backtest/performance_analyzer.py）
4. 输出 output/emotion_performance_report.json
5. 可选：输出可视化图表

必须要求：
- 支持多策略（run_multi_strategy_emotion_backtest）
- 支持批量回测
- 运行时间 < 5 分钟
- 自动缓存历史情绪数据（emotion_history.csv）

参考：core/sentiment_engine.get_emotion_state；database.duckdb_backend.get_daily_bars。
```

### OpenClaw 任务文本

```
任务：执行情绪周期回测验证。

步骤：
1. 进入项目根目录 astock，激活虚拟环境。
2. 运行：python -c "
from backtest.emotion_labeler import generate_emotion_history
from backtest.emotion_backtest import run_emotion_backtest_from_bars
from database.duckdb_backend import DuckDBBackend
import json, os
generate_emotion_history(years=2)
backend = DuckDBBackend()
stocks = backend.get_stocks_from_daily_bars()
ob = stocks[0][0] if stocks else '000001.XSHE'
bars = backend.get_daily_bars(ob, '2023-01-01', '2025-12-31')
r = run_emotion_backtest_from_bars(bars, '2023-01-01', '2025-12-31')
os.makedirs('output', exist_ok=True)
with open('output/emotion_performance_report.json','w',encoding='utf-8') as f: json.dump(r, f, ensure_ascii=False, indent=2)
print('done')
"
3. 验证 output/emotion_performance_report.json 存在且含 by_emotion、summary。

参考：docs/INSTITUTIONAL_CLOSED_LOOP.md
```

---

## 二、龙虎榜资金胜率统计系统

### 目标

- 回答：知名游资席位买入后，平均收益是多少？靠统计不靠感觉。
- 统计 +1/+3/+5/+10 日收益、胜率、盈亏比、最大回撤，输出席位排行榜。

### 模块结构

```
analysis/
    seat_database.py   # 知名游资席位库 YZZ_SEATS
    lhb_statistics.py  # 抓龙虎榜、算后续收益、按席位聚合
    lhb_backtest.py    # 调用 run_lhb_statistics 输出报告
```

### 输出

- `data/lhb_cache/lhb_YYYYMMDD.json`：按日缓存的龙虎榜游资净买记录
- `output/lhb_statistics_report.json`：按席位胜率、+N 日收益、高胜率标记

### Cursor 执行任务文本（复制执行）

```
任务名称：构建龙虎榜资金胜率统计系统

任务目标：
1. 抓取近2年龙虎榜数据（analysis/lhb_statistics.fetch_lhb_history），自动缓存到 data/lhb_cache
2. 筛选知名游资席位（analysis/seat_database.YZZ_SEATS），净买入记录
3. 统计席位净买入后的次日、3日、5日、10日收益（compute_forward_returns）
4. 计算胜率、盈亏比、最大回撤（backtest/performance_analyzer.analyze_returns）
5. 输出 output/lhb_statistics_report.json
6. 输出胜率排行榜（report.ranking）
7. 标记高胜率席位（+5日胜率 >= 0.55）

必须要求：
- 支持并发抓取（ThreadPoolExecutor）
- 自动缓存龙虎榜数据
- 支持按席位排名
- 可选可视化

参考：core/lhb_engine.fetch_lhb_detail、YZZ_SEATS；database.duckdb_backend.get_daily_bars。
```

### OpenClaw 任务文本

```
任务：执行龙虎榜胜率统计。

步骤：
1. 进入项目根目录 astock，激活虚拟环境。
2. 运行：python -c "
from analysis.lhb_statistics import run_lhb_statistics
r = run_lhb_statistics(years=2)
print('by_seat count', len(r.get('by_seat',{})))
print('ranking', r.get('ranking',[])[:5])
"
3. 验证 output/lhb_statistics_report.json 存在且含 by_seat、ranking。

参考：docs/INSTITUTIONAL_CLOSED_LOOP.md
```

---

## 三、游资+趋势融合模型（Fusion Strategy）

### 目标

- 用趋势过滤降低纯游资信号回撤：龙虎榜共振 + 资金评分 > 60，再叠加价格>MA20、MA20 上行、MACD 不死叉。
- 仅情绪为「启动」或「加速」时允许买入；动态仓位：加速 0.6、启动 0.4、其余 0.2。
- 统一评分 final_score = 0.4*fund + 0.3*lhb + 0.2*trend + 0.1*emotion，筛选 final_score > 75。

### 模块结构

```
strategies/
    yz_strategy.py    # 游资信号：龙虎榜共振 + 资金评分
    trend_filter.py   # 趋势过滤：MA20、MACD
    fusion_strategy.py # 融合 + 情绪匹配 + 仓位 + 评分
```

### Cursor 执行任务文本（复制执行）

```
任务名称：构建游资+趋势融合策略 V1.0

任务目标：
1. 新建/完善 strategies/yz_strategy.py（龙虎榜游资识别、资金评分）
2. 新建/完善 strategies/trend_filter.py（价格>MA20、MA20 上行、MACD 不死叉）
3. 新建/完善 strategies/fusion_strategy.py（融合逻辑、情绪匹配、动态仓位、统一评分）
4. 实现：龙虎榜游资识别、趋势结构过滤、情绪周期匹配、动态仓位控制
5. 构建统一评分模型（final_score > 75 筛选）
6. 接入回测系统（FusionStrategy.generate_signals 或 run_backtest_db 策略插件）
7. 输出回测报告与风险指标（最大回撤等）

必须要求：
- 支持多股票同时运行
- 支持 100 万资金
- 支持组合管理
- 最大回撤统计
- 支持策略权重优化（fusion_score 权重可配置）

参考：core/lhb_engine；core/sentiment_engine；backtest/performance_analyzer。
```

---

## 四、OpenClaw 每周调度闭环

### 流程

每周执行：

1. 运行情绪回测验证 → 更新 emotion_performance_report.json  
2. 运行龙虎榜胜率统计 → 更新 lhb_statistics_report.json、席位权重  
3. 可选：运行融合模型回测 → 更新策略权重  
4. 输出 output/weekly_strategy_report.json  

### 执行脚本

```bash
python scripts/run_weekly_strategy_report.py
```

### OpenClaw 任务文本（复制执行）

```
任务：机构级闭环每周调度。

步骤：
1. 进入项目根目录 astock，激活虚拟环境。
2. 执行：python scripts/run_weekly_strategy_report.py
3. 验证 output/weekly_strategy_report.json 已生成，且包含 emotion_backtest、lhb_statistics（或对应 error 说明）。
4. 可选：将 emotion_performance_report.json、lhb_statistics_report.json 路径写入 weekly 报告。

成功标准：weekly_strategy_report.json 存在且含 generated_at、emotion_backtest 或 emotion_backtest_error、lhb_statistics 或 lhb_statistics_error。

参考：docs/INSTITUTIONAL_CLOSED_LOOP.md
```

### Crontab 示例（每周一 9:00）

```cron
0 9 * * 1 cd /path/to/astock && .venv/bin/python scripts/run_weekly_strategy_report.py
```

### 交易日 22:00 自动执行（推荐）

耗时任务（情绪回测、龙虎榜统计）改为定时执行，白天前端只读报告，避免卡顿。

**crontab（推荐）**

```cron
0 22 * * 1-5 cd /path/to/astock && .venv/bin/python scripts/run_closed_loop_nightly.py --once
```

将 `/path/to/astock` 换成项目根目录；无 venv 时用 `python3`。

**常驻进程（无 crontab 时）**

```bash
cd /path/to/astock && .venv/bin/python scripts/run_closed_loop_nightly.py
```

进程常驻，每到交易日 22:00 自动跑闭环；前端「刷新报告」即可查看。

---

## 五、闭环验收点

- 情绪周期自验证：emotion_history.csv + emotion_performance_report.json  
- 龙虎榜席位胜率统计：lhb_statistics_report.json + 排行榜 + 高胜率标记  
- 游资+趋势融合模型：yz_strategy + trend_filter + fusion_strategy，final_score > 75  
- 自动权重优化：每周报告汇总各模块结果  
- 自动风险评估：各报告含 max_drawdown、sharpe、win_rate  

### 前端与 API 自动化（平台内一键执行）

- **前端**：导航栏「机构闭环」→ `/closed-loop`，三个 Tab 可「刷新报告」或「执行 xxx」。建议耗时任务用下方定时在 22:00 跑，白天只刷新查看。
- **后端 API**（供前端或 OpenClaw 调用）：
  - `GET /api/closed_loop/emotion_report`：读取 emotion_performance_report.json
  - `GET /api/closed_loop/lhb_report`：读取 lhb_statistics_report.json
  - `GET /api/closed_loop/weekly_report`：读取 weekly_strategy_report.json
  - `POST /api/closed_loop/run/emotion`：执行情绪回测并写回报告
  - `POST /api/closed_loop/run/lhb`：执行龙虎榜胜率统计
  - `POST /api/closed_loop/run/weekly`：执行每周闭环脚本（约 10 分钟超时）

## 六、模块与路径速查

| 模块           | 路径 | 说明 |
|----------------|------|------|
| 情绪标签       | backtest/emotion_labeler.py | generate_emotion_history, emotion_history.csv |
| 绩效分析       | backtest/performance_analyzer.py | win_rate, profit_factor, max_drawdown, sharpe |
| 情绪回测       | backtest/emotion_backtest.py | run_emotion_backtest_from_bars, run_multi_strategy_emotion_backtest |
| 席位库         | analysis/seat_database.py | YZZ_SEATS, is_yz_seat |
| 龙虎榜胜率     | analysis/lhb_statistics.py | run_lhb_statistics, fetch_lhb_history |
| 趋势过滤       | strategies/trend_filter.py | trend_score_and_pass |
| 游资信号       | strategies/yz_strategy.py | yz_signal_for_date |
| 融合策略       | strategies/fusion_strategy.py | fusion_signal, FusionStrategy |
| 每周调度       | scripts/run_weekly_strategy_report.py | 输出 weekly_strategy_report.json |
| 定时任务（22:00） | scripts/run_closed_loop_nightly.py | 交易日 22:00 执行闭环，支持 --once（crontab）或常驻 |

---

## 七、现实提醒

不追求单一策略爆发，追求长期稳定 + 小回撤。三套系统都跑通后，系统可达 A 股中上游量化水平。

---

## 八、开发完成验证

以下命令在项目根目录、使用 `.venv/bin/python`（或已激活的 venv）执行。

| 步骤 | 命令 | 说明 |
|------|------|------|
| 1 | `python scripts/run_closed_loop_nightly.py --once` | 跑通情绪回测 + 龙虎榜统计 + 每周报告，生成 `output/weekly_strategy_report.json` |
| 2 | `python -c "from web_platform import app; c=app.test_client(); print(c.get('/api/closed_loop/weekly_report').status_code)"` | 应输出 `200` |
| 3 | `python -c "from web_platform import app; c=app.test_client(); r=c.post('/api/closed_loop/run/weekly', json={}); print(r.status_code, r.get_json().get('success'))"` | 应输出 `200 True` |
| 4 | `cd frontend && npm run build` | 前端构建成功 |
| 5 | 启动 `python web_platform.py`，浏览器打开 `http://127.0.0.1:5050/closed-loop` | 三个 Tab 可刷新报告、执行情绪回测/龙虎榜/每周闭环 |

依赖：`pip install -r requirements-web.txt`（含 duckdb、pandas、akshare 等）。
