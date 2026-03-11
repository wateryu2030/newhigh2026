# newhigh 本地 DuckDB 规范

本库为 **newhigh 系统** 使用的 A 股与新闻数据，与 astock 目录独立。路径：`newhigh/data/quant.duckdb`（可由 `NEWHIGH_DUCKDB_PATH` 覆盖）。

## 一、表结构（与 astock 源一致，便于复制）

复制脚本从 astock 原样拷贝以下表；后端与前端通过 **API 层** 使用统一字段名（如 `symbol` 展示为 `600519.SH`）。

### 1. daily_bars（日线）

| 字段 | 类型 | 说明 |
|------|------|------|
| order_book_id | VARCHAR | 标的 ID：600519.XSHG / 000001.XSHE / xxx.BSE |
| trade_date | DATE | 交易日期 |
| adjust_type | VARCHAR | qfq / hfq |
| open, high, low, close | DOUBLE | OHLC |
| volume | DOUBLE | 成交量 |
| total_turnover | DOUBLE | 成交额 |
| adjust_factor | DOUBLE | 复权因子 |

**主键**：(order_book_id, trade_date, adjust_type)

**API 映射**：order_book_id 转为统一 symbol（600519.SH / 000001.SZ）对外；K 线接口返回 `t, o, h, l, c, v, close`。

### 2. stocks（标的列表）

| 字段 | 类型 | 说明 |
|------|------|------|
| order_book_id | VARCHAR | 主键 |
| symbol | VARCHAR | 6 位代码 |
| name | VARCHAR | 中文名称 |

**API 映射**：返回 `symbol`（统一为 600519.SH）、`name`、可选 `order_book_id`，供前端 Market 页标的选择与 K 线请求。

### 3. news_items（新闻）

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | VARCHAR | 标的代码 |
| source_site, source | VARCHAR | 来源 |
| title, content, url | VARCHAR | 标题、正文、链接 |
| keyword, tag | VARCHAR | 关键词、标签 |
| publish_time | VARCHAR | 发布时间 |
| sentiment_score | DOUBLE | 情感分数 |
| sentiment_label | VARCHAR | 情感标签 |

**API**：GET /api/news，返回列表供前端 News 页展示。

### 4. features_daily（日线特征，扩展表）

由 `scripts/init_newhigh_duckdb_extensions.py` 创建，由 `scripts/compute_features_to_duckdb.py` 写入。供策略、回测与持续训练使用。

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | VARCHAR | 标的，如 600519、000001（与 daily_bars 对应） |
| trade_date | DATE | 交易日期 |
| open, high, low, close, volume | DOUBLE | 与日线一致 |
| rsi, macd, macd_signal, macd_hist | DOUBLE | 技术指标 |
| vwap, atr, momentum, volatility | DOUBLE | 量价与波动 |

**主键**：(symbol, trade_date)

### 5. backtest_runs（回测结果，扩展表）

由 `scripts/init_newhigh_duckdb_extensions.py` 创建；策略/回测引擎写入，供 Alpha 评分与进化、未来实盘前验证。

| 字段 | 类型 | 说明 |
|------|------|------|
| run_id | VARCHAR | 主键 |
| strategy_id | VARCHAR | 策略标识 |
| symbol | VARCHAR | 标的 |
| start_date, end_date | DATE | 回测区间 |
| sharpe_ratio, return_pct, max_drawdown_pct, win_rate_pct | DOUBLE | 绩效指标 |
| created_at | TIMESTAMP | 写入时间 |

## 二、数据流（前后端绑定）

```
data/quant.duckdb
    → data_engine.connector_astock_duckdb（读 daily_bars / stocks / news_items）
    → Gateway（/api/market/klines, /api/market/ashare/stocks, /api/news, /api/dashboard 聚合）
    → Frontend（Market 页 K 线+标的列表，News 页，Dashboard 收益曲线）
```

## 三、前端使用的 API 与字段

| 页面 | API | 后端数据来源 | 前端字段 |
|------|-----|--------------|----------|
| Dashboard | GET /api/dashboard | DuckDB 聚合 000001.SZ 等日线 → equity_curve, daily_return_pct, total_equity | total_equity, daily_return_pct, sharpe_ratio, max_drawdown_pct, equity_curve, top_strategies, ai_* |
| Market | GET /api/market/ashare/stocks | DuckDB stocks → 统一 symbol + name | stocks[].symbol, stocks[].name |
| Market | GET /api/market/klines?symbol= | DuckDB daily_bars → OHLCV | data[].t, data[].c, data[].close, data[].o, data[].h, data[].l, data[].v |
| News | GET /api/news | DuckDB news_items | news[].title, news[].source, news[].publish_time, news[].url, news[].sentiment_* |

## 四、复制与维护

- 数据由 `scripts/copy_astock_duckdb_to_newhigh.py` 从 astock 的 DuckDB 复制而来，两库独立。
- 可定期重跑复制脚本以更新 newhigh 本地数据；复制期间无需改表结构，API 层保持统一字段与绑定。
- **扩展表**：复制完成后执行 `python scripts/init_newhigh_duckdb_extensions.py` 创建 `features_daily`、`backtest_runs`；特征由进化循环中的「特征计算落库」步骤或单独运行 `scripts/compute_features_to_duckdb.py` 写入，满足持续训练与实体化（实盘）交易前的数据与回测落库需求。
- **并发**：DuckDB 同一文件同时仅支持一个写连接；`compute_features_to_duckdb.py` 已改为「单只读连接读完 → 关闭 → 单写连接写入」，避免自锁。请勿在复制脚本或其它写操作进行时同时跑特征脚本。
