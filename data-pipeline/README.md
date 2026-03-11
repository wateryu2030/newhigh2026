# A股数据管道 (Data Pipeline)

AkShare → ETL → DuckDB（`data/market.duckdb`）→ API → 前端。与 `quant.duckdb`（astock 复制 + 特征）分离，专用于管道表。

## 结构

```
data-pipeline/
├── src/data_pipeline/
│   ├── storage/duckdb_manager.py   # 库路径、建表
│   ├── collectors/                  # 采集
│   │   ├── stock_list.py            # 沪A+深A+北交所股票池
│   │   ├── daily_kline.py           # 历史日K（单只）
│   │   ├── realtime_quotes.py       # 全市场实时快照
│   │   ├── fund_flow.py             # 个股资金流排名
│   │   ├── limit_up.py              # 涨停池
│   │   └── longhubang.py            # 龙虎榜
│   ├── etl/
│   │   ├── clean_kline.py           # K线清洗
│   │   └── factor_builder.py        # 因子占位
│   └── scheduler/
│       ├── realtime_scheduler.py    # 每30秒：行情+涨停
│       └── daily_scheduler.py       # 每日：股票池+资金流+龙虎榜
```

## 表（market.duckdb）

| 表 | 说明 |
|----|------|
| a_stock_basic | 股票池 code, name |
| a_stock_daily | 日K code, date, open, high, low, close, volume, amount |
| a_stock_realtime | 实时快照 |
| a_stock_fundflow | 资金流排名 |
| a_stock_limitup | 涨停池 |
| a_stock_longhubang | 龙虎榜 |

## 运行

- 环境：`pip install -e ./data-pipeline`（依赖 akshare, duckdb, pandas）
- 路径：`NEWHIGH_MARKET_DUCKDB_PATH` 可覆盖，默认 `data/market.duckdb`

```bash
# 每日一次（建议 18:00）
python scripts/run_pipeline_daily.py

# 实时循环（交易时间，每30秒）
python scripts/run_pipeline_realtime.py
```

## API（Gateway）

- `GET /api/market/realtime?limit=100` 实时行情
- `GET /api/market/limitup?limit=100` 涨停池
- `GET /api/market/fundflow?limit=100` 资金流

## 原则

1. 数据可回测：日K入 a_stock_daily，清洗后供回测
2. 实时可扫描：realtime + limitup 供盘中扫描
3. 可训练：ETL/factor_builder 可接 feature-engine
4. 可复盘：历史日K + 龙虎榜/资金流 供策略复盘
