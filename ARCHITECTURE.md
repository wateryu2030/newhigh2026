# 项目架构说明 - AKShare + RQAlpha 整合

## 一、核心定位

本项目按照「**数据供给 → 策略执行 → 回测/实盘**」的量化闭环设计，明确分工：

| 工具 | 核心定位 | 职责 |
|------|---------|------|
| **AKShare** | 全品类金融数据供给引擎 | 提供 A 股、期货、宏观等全品类数据 |
| **RQAlpha** | 策略全生命周期执行框架 | 基于数据执行策略回测，输出绩效 |
| **数据源适配层** | AKShare → RQAlpha 桥梁 | 转换数据格式，统一接口 |

## 二、项目结构

```
astock/
├── data_source/                    # 数据源适配层（核心）
│   ├── __init__.py
│   ├── akshare_rqalpha_ds.py      # AKShare → RQAlpha 数据源适配器
│   └── akshare_data_source_mod.py # RQAlpha Mod（注册数据源）
│
├── strategies/                     # 策略目录
│   └── simple_akshare_strategy.py  # 示例策略（使用 AKShare 数据源）
│
├── run_backtest_akshare.py         # 简化的回测入口
├── web_platform_simple.py         # 简化的 Web 平台
│
├── akshare/                        # AKShare 仓库（可编辑安装）
├── rqalpha/                        # RQAlpha 仓库（可编辑安装）
└── venv/                           # Python 虚拟环境
```

## 三、数据流

```
用户选择股票
    ↓
Web 平台（web_platform_simple.py）
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

## 四、核心组件说明

### 1. AKShare 数据源适配器 (`data_source/akshare_rqalpha_ds.py`)

**职责**：
- 实现 RQAlpha 的 `AbstractDataSource` 接口
- 调用 AKShare API 获取 A 股日线数据
- 转换数据格式（AKShare → RQAlpha Bar）
- 提供数据缓存机制（避免重复请求）

**关键方法**：
- `get_bar()`: 获取单个 bar
- `get_bar_range()`: 获取 bar 序列
- `get_instruments()`: 获取合约列表

### 2. RQAlpha Mod (`data_source/akshare_data_source_mod.py`)

**职责**：
- 在 RQAlpha 启动时注册 AKShare 数据源
- 替换默认数据源

### 3. 回测入口 (`run_backtest_akshare.py`)

**职责**：
- 简化的命令行回测入口
- 自动启用 AKShare 数据源 Mod
- 加载策略并运行回测

**用法**：
```bash
python run_backtest_akshare.py <策略文件> <开始日期> <结束日期> [股票代码]
```

### 4. Web 平台 (`web_platform_simple.py`)

**职责**：
- 提供 Web 界面选择股票和策略
- 调用回测入口执行回测
- 显示回测结果

**特点**：
- 简化设计，移除复杂的数据准备逻辑
- 直接使用 AKShare 数据源，无需数据库

## 五、使用示例

### 1. 命令行回测

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行回测
python run_backtest_akshare.py \
    strategies/simple_akshare_strategy.py \
    2024-01-01 \
    2024-12-31 \
    600745.XSHG
```

### 2. Web 平台

```bash
# 启动 Web 平台
python web_platform_simple.py

# 访问 http://127.0.0.1:5050
# 在界面中选择策略、股票代码、日期范围，点击「运行回测」
```

### 3. 编写策略

策略示例 (`strategies/simple_akshare_strategy.py`)：

```python
from rqalpha.apis import *
import numpy as np

def init(context):
    # 从环境变量获取股票代码
    import os
    stock_code = os.environ.get('STOCK_CODE', '600745.XSHG')
    context.stock = stock_code
    update_universe(stock_code)

def handle_bar(context, bar_dict):
    # 获取历史数据（自动从 AKShare 获取）
    hist = history_bars(context.stock, 20, "1d", "close")
    # ... 策略逻辑
```

## 六、优势

1. **清晰分工**：AKShare 专注数据，RQAlpha 专注执行
2. **简化流程**：无需数据库，直接使用 AKShare API
3. **易于扩展**：可轻松添加更多 AKShare 数据接口
4. **统一接口**：通过适配层统一数据格式

## 七、后续扩展

- [ ] 支持更多 AKShare 数据接口（期货、宏观、另类数据）
- [ ] 添加数据缓存到本地数据库（可选）
- [ ] 支持多股票组合策略
- [ ] 添加策略绩效可视化
