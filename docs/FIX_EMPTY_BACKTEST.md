# 修复回测结果为空的问题

## 问题描述

运行「动量+均值回归混合」策略时，回测完成但选股结果为空（`高科技动量股票: []`、`消费均值回归股票: []`），导致没有持仓，回测结果没有内容。

## 根本原因

1. **策略需要历史数据**：动量策略需要60日历史数据计算收益率，但数据库只有回测区间（2025-02-19 至 2026-02-19）的数据，没有回测开始日期**之前**的数据。
2. **股票池数据缺失**：策略从 CSV 文件加载股票池，但股票池中的部分股票在数据库中没有数据。
3. **选股逻辑失败**：`history_bars(stock, 60, "1d", "close")` 返回数据不足60日，导致选股失败。
4. **⚠️ 关键问题：股票未加入 universe**：策略从 CSV 加载股票池后，**没有调用 `update_universe()` 将股票加入 universe**，导致 `bar_dict` 中不包含这些股票，`if stock not in bar_dict: continue` 过滤掉了所有股票。

## 解决方案

### 1. 自动拉取更早的历史数据

在回测前，检查策略是否需要额外历史数据：
- **动量策略**（strategy2）：需要60日历史
- **均线策略**：需要20日历史

如果数据不足，自动从回测开始日期前拉取足够的数据（如回测开始前120自然日，确保有60个交易日）。

### 2. 自动拉取股票池中所有股票的数据

对于多股票策略（如 strategy2），自动检查股票池文件（`tech_leader_stocks.csv`、`consume_leader_stocks.csv`），确保所有股票都有：
- 回测区间的数据
- 足够的历史数据（策略需要的前置数据）

### 3. 统一数据源

无论用户选择「数据库」还是「AKShare」数据源，都统一使用数据库执行回测：
- **数据库**：有数据直接用，无数据则按需拉取
- **AKShare**：强制从网络拉取后写入 DB，再回测

这样避免了 bundle 无数据导致的 "There is no data" 错误。

### 4. 将股票池加入 universe

**关键修复**：在 `init()` 函数中，加载股票池后，必须调用 `update_universe()` 将所有股票加入 universe，这样 `bar_dict` 才会包含这些股票的数据。

```python
# 将所有股票池加入 universe
all_stocks = list(set(context.tech_stocks + context.consume_stocks))
if all_stocks:
    update_universe(all_stocks)
    logger.info(f"已加入 {len(all_stocks)} 只股票到 universe")
```

## 实现细节

### 数据拉取逻辑

```python
# 检查策略需要的历史数据天数
strategy_needs_extra_days = 0
if "momentum" in strategy.lower() or "strategy2" in strategy.lower():
    strategy_needs_extra_days = 60  # 动量策略需要60日历史

# 计算需要的最早日期
start_dt = pd.to_datetime(start_date)
earliest_needed = (start_dt - timedelta(days=strategy_needs_extra_days * 2)).strftime("%Y-%m-%d")
fetch_start_ymd = (start_dt - timedelta(days=strategy_needs_extra_days * 2)).strftime("%Y%m%d")

# 拉取数据（包含历史数据）
fetcher.fetch_stock_data(symbol, fetch_start_ymd, end_ymd)
```

### 股票池数据补齐

```python
# 读取股票池文件
pool_df = pd.read_csv("data/tech_leader_stocks.csv", encoding="utf-8-sig")
all_pool_stocks = pool_df["代码"].tolist()

# 检查每只股票的历史数据
for stock in all_pool_stocks:
    early_bars = db.get_daily_bars(stock, earliest_needed, start_date)
    if early_bars is None or len(early_bars) < strategy_needs_extra_days:
        # 拉取数据
        fetcher.fetch_stock_data(symbol, fetch_start_ymd, end_ymd)
```

## 验证

修复后，运行策略2回测：
- ✅ 自动拉取回测开始日期前60日的数据
- ✅ 自动拉取股票池中所有股票的数据
- ✅ **将股票池加入 universe**（关键修复）
- ✅ 选股逻辑能正常执行，选出股票（如：`高科技动量股票: ['000001.XSHE']`）
- ✅ 回测结果有持仓和交易记录

**测试结果**：
```
[2025-02-19 00:00:00] INFO: 已加入 6 只股票到 universe: ['600745.XSHG', '002304.XSHE', '000001.XSHE', '002701.XSHE', '600519.XSHG', '000858.XSHE']
[2025-02-25 15:00:00] INFO: 高科技动量股票: ['000001.XSHE']
[2025-03-18 15:00:00] INFO: 高科技动量股票: ['600745.XSHG']
✅ 回测完成！
```

## 使用建议

1. **首次运行策略2**：系统会自动拉取股票池中所有股票的数据，可能需要一些时间
2. **后续运行**：如果数据已存在，会直接使用，速度更快
3. **更换回测日期**：如果新日期需要更早的数据，系统会自动拉取

## 注意事项

- 拉取数据需要网络连接（使用 AKShare API）
- 股票池中的股票数量会影响拉取时间
- 建议先运行一次，让系统补齐数据，后续回测会更快
