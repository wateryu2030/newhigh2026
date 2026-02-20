# 快速开始指南 - AKShare 数据源

## 🎯 核心目标

**让用户能够自主选择 A 股股票进行量化分析**

## 🚀 快速开始

### 1. 激活虚拟环境

```bash
source venv/bin/activate
```

### 2. 命令行回测（推荐）

```bash
python run_backtest_akshare.py <策略文件> <开始日期> <结束日期> [股票代码]
```

**示例**：
```bash
# 回测闻泰科技（600745.XSHG）
python run_backtest_akshare.py strategies/simple_akshare_strategy.py 2024-01-01 2024-12-31 600745.XSHG

# 回测平安银行（000001.XSHE）
python run_backtest_akshare.py strategies/simple_akshare_strategy.py 2024-01-01 2024-12-31 000001.XSHE
```

### 3. Web 平台

```bash
python web_platform_simple.py
```

然后访问：http://127.0.0.1:5050

在界面中：
1. 选择策略（如：简单移动平均策略）
2. 输入股票代码（如：600745.XSHG 或 000001.XSHE）
3. 选择回测日期范围
4. 点击「运行回测」

## 📊 架构说明

```
用户选择股票
    ↓
Web 平台 / 命令行
    ↓
回测入口（run_backtest_akshare.py）
    ↓
RQAlpha 回测引擎
    ↓
AKShare 数据源适配器（data_source/akshare_rqalpha_ds.py）
    ↓
AKShare API（stock_zh_a_hist）
    ↓
返回标准化数据（RQAlpha Bar 格式）
    ↓
策略执行（strategies/*.py）
    ↓
回测结果
```

## ✨ 特点

1. **无需数据库**：直接使用 AKShare API 获取数据
2. **自动缓存**：数据源适配器有 1 小时缓存，避免重复请求
3. **自主选择**：可以选择任意 A 股股票进行回测
4. **简化流程**：无需复杂的数据准备步骤

## 📝 编写策略

策略示例 (`strategies/simple_akshare_strategy.py`)：

```python
from rqalpha.apis import *
import numpy as np

def init(context):
    # 从环境变量获取股票代码
    import os
    stock_code = os.environ.get('STOCK_CODE', '600745.XSHG')
    context.stock = stock_code
    update_universe(stock_code)  # 重要：必须加入 universe

def handle_bar(context, bar_dict):
    stock = context.stock
    
    # 获取历史数据（自动从 AKShare 获取）
    hist = history_bars(stock, 20, "1d", "close")
    
    # 策略逻辑...
```

**关键点**：
- 使用 `update_universe()` 将股票加入 universe
- 使用 `history_bars()` 获取历史数据（自动从 AKShare 获取）
- 通过环境变量 `STOCK_CODE` 或 `context.config.extra.stock_code` 获取股票代码

## 🔍 测试结果

**成功示例**：
```
[2024-03-15] 买入信号: 短期均线(39.96) > 长期均线(38.41)
[2024-03-22] 卖出信号: 短期均线(39.06) < 长期均线(39.34)
✅ 回测完成！
```

## ⚠️ 注意事项

1. **网络连接**：需要网络连接才能获取 AKShare 数据
2. **股票代码格式**：使用 RQAlpha 格式（如 `600745.XSHG`、`000001.XSHE`）
3. **日期格式**：使用 `YYYY-MM-DD` 格式（如 `2024-01-01`）
4. **数据缓存**：数据有 1 小时缓存，相同请求会使用缓存

## 🆘 问题排查

### 问题：ImportError: cannot import name 'run_func'

**解决**：已修复，使用子进程方式避免导入路径问题。

### 问题：回测没有数据

**检查**：
1. 股票代码格式是否正确（如 `600745.XSHG`）
2. 日期范围是否合理（不要使用未来日期）
3. 网络连接是否正常

### 问题：策略没有交易信号

**检查**：
1. 策略逻辑是否正确
2. 是否调用了 `update_universe()` 将股票加入 universe
3. 历史数据是否足够（如需要 20 日均线，需要至少 20 个交易日的数据）

## 📚 更多信息

- `ARCHITECTURE.md` - 详细架构说明
- `REFACTOR_SUMMARY.md` - 重构总结
- `README.md` - 项目使用说明
