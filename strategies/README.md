# 量化交易策略说明

本目录包含4个针对**高科技（半导体/AI/算力/新能源）**和**消费（必选消费/可选消费）**板块的量化交易策略。

## 策略列表

### 策略1：行业轮动策略（基本面+资金流双驱动）
**文件**: `strategy1_industry_rotation.py`

**策略逻辑**:
- 筛选高科技（半导体/AI/算力）和消费（食品饮料/美妆/家电）核心行业
- 基于行业景气度（财务）+ 资金流（北向/主力资金）做月度轮动
- 选景气度高+资金净流入的行业，持仓龙头标的
- 月度调仓，8%止损

**核心参数**:
- `REBALANCE_INTERVAL = 30` - 月度调仓（30个交易日）
- `STOP_LOSS_RATIO = 0.08` - 8%止损
- `TOP_N_INDUSTRIES = 2` - 选前2个行业
- `TOP_N_STOCKS_PER_INDUSTRY = 3` - 每个行业选前3只股票

**数据需求**:
- `data/industry_stock_map.csv` - 行业股票映射表
- `data/industry_score.csv` - 行业得分表

**使用方法**:
```bash
python run_backtest.py strategies/strategy1_industry_rotation.py 2024-01-01 2024-12-31
```

---

### 策略2：动量+均值回归混合策略
**文件**: `strategy2_momentum_meanreversion.py`

**策略逻辑**:
- 高科技龙头：60日动量策略，选收益率前10%标的，持仓2周
- 消费龙头：均值回归策略，股价偏离20日均线超10%买入，回归卖出
- 仓位分配：高科技60% + 消费40%

**核心参数**:
- `MOMENTUM_WINDOW = 60` - 动量周期60日
- `MEAN_REVERSION_WINDOW = 20` - 均值回归周期20日
- `REBALANCE_INTERVAL = 5` - 周度调仓（5个交易日）
- `TECH_WEIGHT = 0.6` - 高科技仓位60%
- `CONSUME_WEIGHT = 0.4` - 消费仓位40%
- `TAKE_PROFIT_RATIO = 0.15` - 止盈15%

**数据需求**:
- `data/tech_leader_stocks.csv` - 高科技龙头股票池
- `data/consume_leader_stocks.csv` - 消费龙头股票池

**使用方法**:
```bash
python run_backtest.py strategies/strategy2_momentum_meanreversion.py 2024-01-01 2024-12-31
```

---

### 策略3：财报超预期事件驱动策略
**文件**: `strategy3_earnings_surprise.py`

**策略逻辑**:
- 聚焦高科技（研发投入高）和消费（毛利率稳定）标的
- 当财报营收/净利润超分析师预期时买入
- 持有1个月博弈业绩驱动行情

**核心参数**:
- `HOLD_PERIOD = 20` - 持有20个交易日（约1个月）
- `TECH_RD_THRESHOLD = 0.05` - 高科技研发投入/营收>5%
- `TECH_PROFIT_GROWTH_THRESHOLD = 0.20` - 净利润同比增速超预期>20%
- `CONSUME_GROSS_MARGIN_THRESHOLD = 0.30` - 消费毛利率>30%
- `CONSUME_REVENUE_GROWTH_THRESHOLD = 0.10` - 营收同比增速超预期>10%

**数据需求**:
- 需要从AKShare获取财报数据和分析师预期数据
- 需要实时监控财报发布事件

**使用方法**:
```bash
python run_backtest.py strategies/strategy3_earnings_surprise.py 2024-01-01 2024-12-31
```

---

### 策略4：ETF网格交易策略
**文件**: `strategy4_etf_grid.py`

**策略逻辑**:
- 针对高流动性的ETF做网格交易
- 高科技ETF：网格间距5%，利用高波动赚差价
- 消费ETF：网格间距3%，波动小但收益稳定
- 趋势性行情（涨跌幅>20%）暂停网格，转为趋势跟踪

**核心参数**:
- `TECH_ETF = "512480.XSHG"` - 半导体ETF（需确认实际代码）
- `CONSUME_ETF = "516130.XSHG"` - 消费龙头ETF（需确认实际代码）
- `TECH_GRID_SPACING = 0.05` - 高科技网格间距5%
- `CONSUME_GRID_SPACING = 0.03` - 消费网格间距3%
- `GRID_POSITION_SIZE = 0.10` - 单格仓位10%
- `MAX_ETF_POSITION = 0.50` - 单ETF最大仓位50%

**使用方法**:
```bash
python run_backtest.py strategies/strategy4_etf_grid.py 2024-01-01 2024-12-31
```

---

## 数据准备

### 1. 准备行业数据（策略1使用）

```bash
cd /Users/apple/astock
source venv/bin/activate
python data_prep/akshare_data_fetcher.py
```

这会生成：
- `data/industry_stock_map.csv` - 行业股票映射表
- `data/industry_score.csv` - 行业得分表

### 2. 准备龙头股票池（策略2使用）

需要手动创建或使用AKShare获取：
- `data/tech_leader_stocks.csv` - 高科技龙头股票池
- `data/consume_leader_stocks.csv` - 消费龙头股票池

格式示例：
```csv
代码
000001.XSHE
000002.XSHE
```

---

## 策略回测

### 使用命令行回测

```bash
source venv/bin/activate
python run_backtest.py strategies/strategy1_industry_rotation.py 2024-01-01 2024-12-31
```

### 使用Web平台回测

1. 启动Web平台：`python web_platform.py`
2. 访问 http://127.0.0.1:5050
3. 选择策略文件，配置回测参数，运行回测

---

## 策略优化建议

1. **参数调优**：根据回测结果调整调仓频率、止损止盈比例等参数
2. **数据完善**：使用AKShare完整获取财务数据、资金流数据，提高策略准确性
3. **风控加强**：添加更多风控规则，如最大回撤控制、仓位管理
4. **实盘验证**：先用小资金实盘验证，逐步放大仓位

---

## 注意事项

1. **数据依赖**：策略需要相应的数据文件，请先运行数据准备脚本
2. **股票代码格式**：RQAlpha使用 `000001.XSHE` 格式（6位代码+交易所后缀）
3. **ETF代码**：策略4中的ETF代码需要根据实际情况修改
4. **回测数据**：确保RQAlpha有足够的历史数据用于回测
