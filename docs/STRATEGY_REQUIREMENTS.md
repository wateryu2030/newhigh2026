# 策略数据要求说明

## 策略分类

### 1. 简单策略（无需额外数据）

这些策略可以直接运行，只需要股票日线数据：

- ✅ **买入并持有** (`buy_and_hold_akshare.py`)
- ✅ **简单均线策略** (`simple_ma_strategy.py`)
- ✅ **通用均线策略** (`universal_ma_strategy.py`) - **推荐用于测试**
- ✅ **闻泰科技案例** (`strategy_wentai_demo.py`)

### 2. 复杂策略（需要额外数据文件）

这些策略需要额外的数据文件，如果数据文件不存在，回测可能失败：

#### 行业轮动策略 (`strategy1_industry_rotation.py`)

**需要的数据文件：**
- `data/industry_stock_map.csv` - 行业-股票映射表
- `data/industry_score.csv` - 行业评分数据

**如果数据文件不存在：**
- 策略会使用默认股票池（示例数据）
- 回测可能无法正常运行或结果不准确

**解决方案：**
1. 运行数据准备脚本：
   ```bash
   python data_prep/akshare_data_fetcher.py
   ```
2. 或使用简单策略进行测试（如 `universal_ma_strategy.py`）

#### 动量+均值回归混合策略 (`strategy2_momentum_meanreversion.py`)

**需要的数据：**
- 高科技和消费板块的股票列表
- 可能需要行业分类数据

#### 财报超预期事件驱动策略 (`strategy3_earnings_surprise.py`)

**需要的数据：**
- 财报事件数据（营收/净利润超预期事件）
- 当前为简化实现，可能需要完善数据获取

#### ETF网格交易策略 (`strategy4_etf_grid.py`)

**需要的数据：**
- ETF 代码列表
- ETF 日线数据

## 推荐使用顺序

1. **首次使用**：使用 `universal_ma_strategy.py` + 任意股票代码测试
2. **验证数据源**：使用 `buy_and_hold_akshare.py` 或 `simple_ma_strategy.py`
3. **准备数据后**：再使用复杂策略（行业轮动、ETF 网格等）

## 数据准备

如需使用复杂策略，请先准备数据：

```bash
# 准备行业和财务数据
python data_prep/akshare_data_fetcher.py

# 或使用准备脚本
./prepare_strategy_data.sh
```

## 故障排除

如果回测失败，检查：

1. **数据文件是否存在**：
   ```bash
   ls -la data/industry_* data/stock_*
   ```

2. **股票数据是否在数据库中**：
   - 检查数据库中的股票列表
   - 使用按需拉取功能自动获取

3. **策略文件语法是否正确**：
   - 检查策略文件是否有语法错误
   - 查看回测日志中的错误信息

4. **使用简单策略测试**：
   - 先用 `universal_ma_strategy.py` 验证系统是否正常
   - 再尝试复杂策略
