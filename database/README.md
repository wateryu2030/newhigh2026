# 数据库数据源系统

本系统实现了从 AKShare 获取真实股票数据并存储到本地 SQLite 数据库，供 RQAlpha 回测使用。

## 架构

```
AKShare API → DataFetcher → SQLite Database → DatabaseDataSource → RQAlpha
```

## 快速开始

### 1. 初始化数据库

数据库会在首次使用时自动创建：

```bash
python database/data_fetcher.py
```

### 2. 获取股票数据

#### 获取单只股票数据

```bash
python database/sync_data.py --symbol 600745 --days 365
```

#### 获取闻泰科技数据（示例）

```bash
python database/sync_data.py --wentai
```

#### 批量获取策略股票数据

```bash
python database/sync_data.py --strategy
```

#### 更新所有已存储股票的数据

```bash
python database/sync_data.py --update-all
```

### 3. 使用数据库数据源运行回测

```bash
python run_backtest_db.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31
```

## 数据库结构

### 表结构

- **stocks**: 股票基本信息
  - `order_book_id`: 合约代码（如 "600745.XSHG"）
  - `symbol`: 股票代码（如 "600745"）
  - `name`: 股票名称
  - `market`: 市场代码
  - `listed_date`: 上市日期
  - `de_listed_date`: 退市日期

- **daily_bars**: 日线行情数据
  - `order_book_id`: 合约代码
  - `trade_date`: 交易日期
  - `open`, `high`, `low`, `close`: OHLC 价格
  - `volume`: 成交量
  - `total_turnover`: 成交额
  - `adjust_factor`: 复权因子

- **trading_calendar**: 交易日历
  - `trade_date`: 交易日期
  - `is_trading`: 是否为交易日

## 数据源适配器

`DatabaseDataSource` 实现了 RQAlpha 的 `AbstractDataSource` 接口，提供：

- `get_instruments()`: 获取合约列表
- `get_bar()`: 获取单个 bar
- `history_bars()`: 获取历史 bar 数据
- `get_trading_calendars()`: 获取交易日历
- 其他必需接口

## 使用示例

### Python 代码示例

```python
from database.data_fetcher import DataFetcher
from database.duckdb_backend import get_db_backend

# 获取数据
fetcher = DataFetcher()
fetcher.fetch_stock_data("600745", "20200101", "20241231")

# 查询数据（统一使用 DuckDB：data/quant.duckdb）
db = get_db_backend()
df = db.get_daily_bars("600745.XSHG", "2024-01-01", "2024-06-30")
print(df)
```

## 注意事项

1. **数据更新**: 建议定期运行 `sync_data.py` 更新数据
2. **数据量**: 单只股票一年的日线数据约 250 条，注意数据库大小
3. **网络**: 首次获取数据需要网络连接，后续可离线使用
4. **交易日历**: 当前使用简化的工作日历，实际应使用真实交易日历

## 故障排除

### 数据库文件位置

默认位置：`data/astock.db`

### 查看数据库内容

```bash
sqlite3 data/astock.db
.tables
SELECT * FROM stocks LIMIT 5;
SELECT COUNT(*) FROM daily_bars;
```

### 重新初始化数据库

删除 `data/astock.db` 文件，重新运行数据获取脚本即可。
