# 量化平台模块与接口说明

本文档描述完整量化平台新增/修改的模块、目录结构及 HTTP/编程接口。

---

## 一、新增文件列表

| 路径 | 说明 |
|------|------|
| `optimizer/ga_config.py` | 遗传算法配置（种群大小、代数、交叉/变异率等） |
| `optimizer/ga_optimizer.py` | 生产级遗传算法（选择、交叉、变异、精英保留）+ **GeneticOptimizer** 类 |
| `data/__init__.py` | A 股股票池数据接口包入口 |
| `data/stock_universe.py` | 股票池统一结构 `StockUniverse`，支持数据库/CSV 加载 |
| `data/stock_pool.py` | **get_a_share_list()**（AKShare 全 A 列表）、**load_kline(symbol, period)**（AKShare K 线） |
| `data/data_loader.py` | **load_kline** 统一入口（database / akshare） |
| `core/tv_kline.py` | TradingView 级 K 线（TvKlineBar、TvKlineSeries、**convert_to_tv(df)**） |
| `portfolio/__init__.py` | 多策略组合包入口 |
| `portfolio/portfolio.py` | 多策略组合回测（权重聚合净值曲线与信号） |
| `portfolio/portfolio_engine.py` | **PortfolioEngine**（多策略信号融合、combine_signal、run） |
| `api/__init__.py` | API 层包入口 |
| `api/routes.py` | 组合回测、TradingView K 线、股票池等路由注册 |
| `docs/PLATFORM_SPEC.md` | 本说明文档 |

---

## 二、修改文件列表

| 路径 | 修改内容 |
|------|----------|
| `optimizer/__init__.py` | 导出 `GAConfig`、`optimize_strategy_simple`、**GeneticOptimizer** |
| `optimizer/ga_optimizer.py` | 新增 **GeneticOptimizer** 类：optimize(strategy_class, df, param_space, backtest_fn, score_fn) |
| `data/__init__.py` | 导出 **get_a_share_list**、**load_kline_akshare**、**load_kline_unified** |
| `core/tv_kline.py` | 新增 **convert_to_tv(df, ...)** 返回 `{ candles, markers, indicators }` |
| `portfolio/__init__.py` | 导出 **PortfolioEngine** |
| `scanner/__init__.py` | 导出 **scan_market_portfolio** |
| `scanner/scanner.py` | 新增 **scan_market_portfolio(strategies, timeframe, ...)** 组合策略版扫描 |
| `web_platform.py` | `/api/scan` 支持 body **strategies** 时走组合扫描；新增 **组合策略** 按钮 |
| `static/app.js` | **runPortfolioBacktest()**、组合策略按钮 onclick |

---

## 三、目录结构（与平台模块对应）

```
core/           # 核心逻辑
  signals.py
  scoring.py
  prediction.py
  timeframe.py
  tv_kline.py   # TradingView K 线数据结构

strategies/     # 策略插件
  base.py
  ma_cross.py
  rsi_strategy.py
  macd_strategy.py
  breakout.py

scanner/        # 股票扫描器
  scanner.py
  universe.py

optimizer/      # 参数优化（遗传算法）
  ga_config.py
  ga_optimizer.py

portfolio/      # 多策略组合
  portfolio.py

data/           # A 股股票池数据接口
  stock_universe.py

api/            # HTTP API 层
  routes.py

database/       # 数据库（已有）
web_platform    # Flask 主应用（已有）
```

---

## 四、接口说明

### 4.1 遗传算法优化（optimizer）

- **`optimize_strategy(...)`**  
  - 返回：`(best_params, best_score, history)`；`history`: 每代最优。
- **`optimize_strategy_simple(...)`**  
  - 返回：`(best_params, best_score)`，兼容原有调用。
- **`random_params(space)`**  
  - 在 `{param: [min, max]}` 内随机采样。
- **`GAConfig`**  
  - 字段：population_size, generations, elite_count, crossover_rate, mutation_rate, mutation_strength, tournament_size。
- **`GeneticOptimizer`**（生产级类）  
  - 构造：`population_size=30, generations=20, mutation_rate=0.1, crossover_rate=0.7, elite_count=5`  
  - **`optimize(strategy_class, df, param_space, backtest_fn, score_fn)`**  
  - `param_space`: `{"short_window": (5, 20), "long_window": (20, 60)}` 或 `[min, max]`  
  - `backtest_fn(df, strategy_instance)` → stats；`score_fn(stats)` → 适应度；返回 `(best_params, best_score)`。

### 4.2 A 股股票池（data）

- **`StockUniverse`**  
  - 属性：`items`, `source`；方法：`symbols(limit?)`, `to_dict_list()`, `__len__`
- **`load_universe_from_database`** / **`load_universe_from_csv`** / **`get_universe`**  
  - 同前。
- **`get_a_share_list()`**  
  - 使用 AKShare 获取全 A 列表，返回 `[{"symbol", "name"}, ...]`。
- **`load_kline_akshare`**（即 stock_pool.load_kline）  
  - `load_kline(symbol, period="daily", adjust="qfq", start_date, end_date)` → DataFrame（列 date, open, high, low, close, volume）。
- **`load_kline_unified`**（即 data_loader.load_kline）  
  - `load_kline(symbol, start_date, end_date, source="database"|"akshare")` 统一从数据库或 AKShare 加载。

### 4.3 TradingView K 线（core/tv_kline）

- **`TvKlineBar`** / **`TvKlineSeries`**  
  - 同前；`to_chart_payload()` 返回 `{ bars, bars_array, indicators, markers }`。
- **`from_backtest_kline`** / **`from_backtest_result`** / **`to_tv_series_payload`**  
  - 同前。
- **`convert_to_tv(df, date_col="date", open_col="open", ..., markers=None, indicators=None)`**  
  - 将 DataFrame 转为 **TradingView / Lightweight Charts** 兼容格式。  
  - 返回：`{ "candles": [{ time, open, high, low, close, volume }, ...], "markers": [], "indicators": {} }`。

### 4.4 多策略组合（portfolio）

- **`aggregate_curves(curves, weights)`**  
  - 按权重合并多条净值曲线，日期并集、前向填充。
- **`run_portfolio_backtest(strategies, stock_code, start_date, end_date, timeframe)`**  
  - `strategies`: `[{ strategy_id, weight, symbol? }]`；返回与单策略回测同构的 result。
- **`PortfolioEngine(strategies, weights=None)`**  
  - **`combine_signal(signals: List[str])`** → `"BUY"|"SELL"|"HOLD"`（多数决）。  
  - **`run(df)`** → `{ "signals": [{ date, signal, weights_per_strategy }], "equity": [{ date, value }], "stats": {} }`。  
  - **`run_portfolio(strategies, df, weights)`** 类方法式入口。

### 4.5 扫描器（scanner）

- **`scan_market(strategy_id, timeframe, ...)`**  
  - 单策略扫描，返回最新 K 线当日有信号的股票列表。
- **`scan_market_portfolio(strategies, timeframe, ...)`**  
  - 组合策略版：多策略融合后，返回组合信号为 BUY/SELL 的标的。  
  - `strategies`: `[{ strategy_id, weight }, ...]`。

### 4.6 HTTP API（api/routes + web_platform）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/portfolio` | 多策略组合回测。Body: `strategies`, `stockCode`, `startDate`, `endDate`, `timeframe?` |
| POST | `/api/tv_kline` | 回测 result 转 TradingView 结构。Body: `result` |
| GET  | `/api/universe` | 股票池。Query: `source=database|csv`, `limit=`, `csvPath=` |
| POST | `/api/scan` | 扫描市场。Body: **strategy**（单策略）或 **strategies**（组合），`timeframe`, `limit?`；组合时返回 `mode: "portfolio"` |
| POST | `/api/optimize` | 参数优化。Body: `strategy`, `stockCode`, `startDate`, `endDate`, `timeframe?`, `paramSpace?` |

---

## 五、统一数据结构约定

- **回测 result**：`curve`, `holdCurve`, `kline`, `signals`, `markers`, `stats`, `strategy_name`, `timeframe`, `strategy_score`, `strategy_grade`；组合结果增加 `portfolio_weights`。
- **K 线单条**：`date`, `open`, `high`, `low`, `close`, `volume`（与 TvKlineBar 一一对应）。
- **信号**：`date`, `type`(buy/sell), `price`, `reason`（及可选 strategy_id 用于组合）。
