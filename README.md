# astock — 量化交易平台（AKShare + RQAlpha）

本项目整合了 [AKShare](https://github.com/akfamily/akshare) 和 [RQAlpha](https://github.com/ricequant/rqalpha)，构建了一套完整的量化交易平台，支持数据获取、策略回测、Web 管理界面等功能。

## 🎯 核心定位

按照「**数据供给 → 策略执行 → 回测/实盘**」的量化闭环设计，明确分工：

| 工具 | 核心定位 | 职责 |
|------|---------|------|
| **AKShare** | 全品类金融数据供给引擎 | 提供 A 股、期货、宏观等全品类数据 |
| **RQAlpha** | 策略全生命周期执行框架 | 基于数据执行策略回测，输出绩效 |
| **数据源适配层** | AKShare → RQAlpha 桥梁 | 转换数据格式，统一接口 |

## 🚀 快速开始（推荐）

### 使用 AKShare 数据源（无需数据库）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 命令行回测（推荐）
python run_backtest_akshare.py strategies/simple_akshare_strategy.py 2024-01-01 2024-12-31 600745.XSHG

# 3. 或启动 Web 平台
python web_platform_simple.py
# 访问 http://127.0.0.1:5050
```

**特点**：
- ✅ 无需数据库，直接使用 AKShare API
- ✅ 自主选择任意 A 股股票
- ✅ 自动数据缓存（1 小时）
- ✅ 简化流程，开箱即用

详细说明请参考：[QUICK_START_AKSHARE.md](QUICK_START_AKSHARE.md)

## 一、已完成的自动化配置

- ✅ **AKShare**：已克隆并安装（可编辑模式）
  - 仓库：`akshare` 来自 https://github.com/akfamily/akshare
  - 数据源：支持 A 股、期货、基金等多种金融数据
- ✅ **RQAlpha**：已克隆并安装（可编辑模式）
  - 仓库：`rqalpha` 来自 https://github.com/ricequant/rqalpha
  - 回测引擎：完整的量化回测框架
- ✅ **数据适配器**：`akshare_adapter.py` - 将 AKShare 数据转换为 RQAlpha 格式
- ✅ **数据库数据源**：`database/` - SQLite 数据库存储真实股票数据，支持离线回测
- ✅ **示例策略**：`strategies/` 目录包含多个策略示例
- ✅ **Web 平台**：`web_platform.py` - 可视化策略管理和回测界面
- ✅ **虚拟环境**：`venv`（Python 3.9+），所有依赖已安装  

## 产品规划：决策驾驶舱

目标从「回测工具」升级为 **决策驾驶舱**：用户一眼看到 **何时买/卖最好**、理解 **为何买卖**、看到 **未来可能走势（概率）**。已落地的设计文档与接口规范：

- **[决策驾驶舱设计](docs/DECISION_COCKPIT_DESIGN.md)**：买卖区间高亮、信号原因解释、概率趋势、策略 vs 持有曲线、页面布局与实施路线图
- **[决策驾驶舱 API 说明](docs/COCKPIT_API_SPEC.md)**：回测结果扩展字段（`buyZones`、`sellZones`、`signals`、`kline`、`futureProbability` 等）及前端使用建议

当前回测接口已预留上述字段（空结构），前端可按文档分阶段实现（建议优先：买卖区间高亮 + 策略/持有双曲线）。

## 二、自主测试与初始化

### 🔧 一键初始化（推荐首次使用）

```bash
# 方式1: 使用自动化脚本
./scripts/setup_all.sh

# 方式2: 手动执行
source venv/bin/activate
python setup_complete.py
```

这会自动：
- ✅ 检查并安装所有依赖（akshare, rqalpha, flask）
- ✅ 创建必要的目录结构（strategies, output, data, bundle）
- ✅ 创建 bundle 文件结构（供 RQAlpha 使用）
- ✅ 测试 AKShare 数据获取
- ✅ 测试 RQAlpha 导入
- ✅ 验证策略文件语法

### 🧪 运行自动化测试

```bash
source venv/bin/activate
python auto_test.py
```

这会检查：
- 依赖安装状态
- Bundle 数据包
- AKShare 数据获取
- RQAlpha 功能
- 策略文件语法

### 批量回测验证（多标的 × 多策略）

使用 002701、600598、300212 等标的，批量跑通所有策略，确保项目能满足多数 A 股的分析与回测：

```bash
source venv/bin/activate
python scripts/run_all_backtests.py
# 可选：指定标的与区间
python scripts/run_all_backtests.py 002701.XSHE 600598.XSHG 300212.XSHE 2025-02-20 2026-02-20
```

通过即表示当前 7 个策略 × 3 只标的共 21 组回测均能正常完成。发布或修改策略/数据层后建议跑一遍以回归。

### 全量同步股票池（多标的策略推荐）

策略2/策略1 等会用到多只股票，若数据库缺少部分标的或日期会出现「No market data」。可先全量同步股票池再回测：

```bash
source venv/bin/activate
python scripts/sync_pool_stocks.py
# 指定区间
python scripts/sync_pool_stocks.py --start 20240220 --end 20260220
```

或在 Web 回测页点击 **「📦 全量同步股票池」**，会按当前回测开始/结束日期拉取 data/ 下所有策略 CSV 中的股票日线并写入数据库（需网络，耗时数分钟）。

### 全量导入 A 股（本地全市场数据）

将沪深京 A 股全部股票（约 5000+ 只）的日线导入本地数据库，回测时可任意选股、多标的策略不再缺数据：

```bash
source venv/bin/activate
# 默认拉取近两年，跳过已有数据（可断点续传）
python scripts/import_all_a_stocks.py
# 指定区间
python scripts/import_all_a_stocks.py --start 20230201 --end 20260220
# 仅测试前 10 只
python scripts/import_all_a_stocks.py --limit 10
```

首次全量约 5000+ 只 × 约 500 交易日，耗时会较长（约 1～3 小时，视网络与 `--delay` 而定）。默认会跳过库中已有数据的股票，可多次执行直至全部完成。

### 若出现「无法访问此网站 / 连接被拒绝」(ERR_CONNECTION_REFUSED)

1. **确认服务已启动**：在项目根目录执行  
   `./start_platform.sh` 或  
   `source venv/bin/activate && python web_platform.py`
2. **使用正确端口**：平台默认使用 **5050**（避免与 macOS 占用的 5000/5001 冲突），浏览器访问 **http://127.0.0.1:5050**
3. **自检**：终端执行 `curl -s http://127.0.0.1:5050/health`，若返回 `{"status":"ok"}` 表示服务正常
4. **换端口**：若 5050 被占用，可执行 `PORT=8080 python web_platform.py`，然后访问 http://127.0.0.1:8080

### 2.1 测试 AKShare 数据获取

```bash
source venv/bin/activate   # Windows: venv\Scripts\activate
python run_akshare.py
# 或
./scripts/run.sh
```

### 2.2 启动 Web 量化交易平台

```bash
source venv/bin/activate
python web_platform.py
```

然后在浏览器访问：**http://127.0.0.1:5050**（默认端口 5050，避免与系统占用冲突）

Web 平台功能：
- 📊 策略列表管理
- ⚙️ 回测配置与运行
- 📝 策略代码编辑器
- 📈 回测日志查看

### 2.3 命令行运行回测

```bash
source venv/bin/activate
python run_backtest.py strategies/simple_ma_strategy.py 2024-01-01 2024-12-31
```

### 2.4 查看数据展示页面

```bash
source venv/bin/activate
python app.py
```

访问：**http://127.0.0.1:5000** 查看 AKShare 数据可视化

## 三、自主完善与调整

- **改源码即生效**：编辑 `akshare/` 下任意 Python 文件，保存后直接再次运行 `python run_akshare.py` 或你自己的脚本，无需 `pip install`。  
- **依赖变更**：若修改了 `akshare/pyproject.toml` 或 `akshare/setup.py`，在激活的 venv 中执行：
  ```bash
  pip install -e ./akshare
  ```
- **升级上游**：在 `akshare` 目录下执行 `git pull` 即可从官方仓库拉取最新代码；若有冲突，解决后再次运行上述命令即可。

## 四、与 OpenLCA、Kimi 配合使用

- **OpenLCA**：若需在 OpenLCA 或相关脚本中调用 AKShare，可指定本环境的 Python 解释器为 `astock/venv/bin/python`，或在 OpenLCA 能调用的外部脚本中通过该解释器执行 `import akshare` 及你的逻辑。  
- **Kimi / 其他 AI 助手**：可将本仓库路径、`venv` 路径以及「使用 `python run_akshare.py` 或 `import akshare`」的用法提供给 Kimi，便于其生成或修改调用 AKShare 的脚本，并在当前环境中直接运行、迭代。

## 五、目录结构

```
astock/
├── README.md              # 本说明文档
├── run_akshare.py         # AKShare 快速测试脚本
├── app.py                  # AKShare 数据展示 Web 页面
├── web_platform.py         # 量化交易平台 Web 界面
├── run_backtest.py        # 回测运行脚本
├── akshare_adapter.py      # AKShare 数据适配器（RQAlpha 接口）
├── venv/                   # Python 虚拟环境
├── scripts/
│   └── run.sh              # 一键运行脚本
├── strategies/             # 策略目录
│   ├── simple_ma_strategy.py      # 简单移动平均策略
│   └── buy_and_hold_akshare.py    # 买入并持有策略
├── output/                 # 回测结果输出目录
├── akshare/                # AKShare 仓库（可编辑安装）
└── rqalpha/                # RQAlpha 仓库（可编辑安装）
```

## 六、重新克隆与配置（在新机器上从零开始）

```bash
# 1. 克隆仓库
git clone https://github.com/akfamily/akshare.git
git clone https://github.com/ricequant/rqalpha.git
cd astock   # 项目根目录

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. 安装依赖（可编辑模式）
pip install -e ./akshare
pip install -e ./rqalpha

# 4. 安装 Web 平台依赖
pip install flask

# 5. 创建必要目录
mkdir -p strategies output

# 6. 运行测试
python run_akshare.py
python web_platform.py  # 启动 Web 平台

# 7. 设计目标自检（可选）
python scripts/check_design_goals.py  # 需先启动 web_platform.py 再自检
```

**浏览器测试**：启动 Web 平台后，在浏览器打开 http://127.0.0.1:5050，确认：
- 策略下拉列表有 8 个策略可选
- 股票代码下拉有数据库中的股票（如 600745、000001），并可输入自定义代码
- 选择「数据库」数据源后点击「运行回测」可完成回测（使用 `run_backtest_db.py`）

**说明**：若使用命令行直接回测，请用 **数据库数据源** 脚本避免导入错误：
```bash
python run_backtest_db.py strategies/universal_ma_strategy.py 2024-01-01 2024-12-31
```

## 七、量化交易策略

### 7.1 策略列表

策略说明在 Web 平台「策略列表」和下拉框中展示；元数据见 `strategies/strategies_meta.json`。

项目包含 4 个针对**高科技**和**消费**板块的量化交易策略，以及通用/示例策略：

1. **策略1：行业轮动策略** (`strategies/strategy1_industry_rotation.py`)
   - 基本面+资金流双驱动
   - 月度轮动，选景气度高+资金净流入的行业
   - 持仓龙头标的，8%止损

2. **策略2：动量+均值回归混合策略** (`strategies/strategy2_momentum_meanreversion.py`)
   - 高科技：60日动量策略
   - 消费：均值回归策略
   - 仓位分配：高科技60% + 消费40%

3. **策略3：财报超预期事件驱动策略** (`strategies/strategy3_earnings_surprise.py`)
   - 财报营收/净利润超预期时买入
   - 持有1个月博弈业绩驱动行情

4. **策略4：ETF网格交易策略** (`strategies/strategy4_etf_grid.py`)
   - 高科技ETF：网格间距5%
   - 消费ETF：网格间距3%
   - 适合震荡市

5. **闻泰科技案例测试** (`strategies/strategy_wentai_demo.py`) ⭐
   - 标的：闻泰科技（600745.XSHG）
   - 移动平均策略：5日/20日均线
   - 金叉买入，死叉卖出
   - 止损8%，止盈20%
   - **适合快速测试和验证系统功能**

### 7.2 数据准备

在运行策略前，需要准备数据：

```bash
source venv/bin/activate
# 准备行业数据（策略1使用）
python data_prep/akshare_data_fetcher.py
```

### 7.3 运行策略

**命令行回测**：
```bash
python run_backtest.py strategies/strategy1_industry_rotation.py 2024-01-01 2024-12-31
```

**Web平台回测**：
1. 启动平台：`python web_platform.py`
2. 访问 http://127.0.0.1:5050
3. 选择策略文件，配置参数，运行回测

详细策略说明请参考：`strategies/README.md`

### 7.4 闻泰科技案例测试（推荐新手）

**快速测试系统功能**，使用闻泰科技（600745）作为实例：

```bash
# 1. 测试数据获取
source venv/bin/activate
python test_wentai.py

# 2. 运行策略回测
python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31

# 3. 或在Web平台运行
# 访问 http://127.0.0.1:5050，选择 strategy_wentai_demo.py
```

详细说明请参考：`strategies/WENTAI_DEMO_README.md`

## 八、AKShare + RQAlpha 整合说明

### 7.1 数据适配器

`akshare_adapter.py` 实现了 `AbstractDataSource` 接口，将 AKShare 数据转换为 RQAlpha 可用的格式：

- **数据获取**：使用 `ak.stock_zh_a_hist()` 获取 A 股历史数据
- **格式转换**：将 pandas DataFrame 转换为 RQAlpha 的结构化数组
- **缓存机制**：缓存已获取的数据，提高性能

### 7.2 编写策略

策略文件放在 `strategies/` 目录，参考示例：

```python
from rqalpha.apis import *

def init(context):
    context.s1 = "000001.XSHE"  # 平安银行
    update_universe(context.s1)

def handle_bar(context, bar_dict):
    # 获取历史数据
    prices = history_bars(context.s1, 20, '1d', 'close')
    # 策略逻辑...
```

### 7.3 运行回测

**方式一：Web 界面**
1. 启动 `python web_platform.py`
2. 访问 http://127.0.0.1:5050
3. 选择策略、配置参数、运行回测

**方式二：命令行**
```bash
python run_backtest.py strategies/simple_ma_strategy.py 2024-01-01 2024-12-31
```

### 7.4 扩展开发

- **修改数据源**：编辑 `akshare_adapter.py`，添加更多数据接口
- **添加策略**：在 `strategies/` 目录创建新的策略文件
- **自定义 Web 功能**：修改 `web_platform.py` 添加新功能

## 九、与 OpenLCA、Kimi 配合使用

- **OpenLCA**：使用本环境的 Python 解释器 `venv/bin/python` 调用策略和数据接口
- **Kimi / AI 助手**：提供项目路径和策略示例，让 AI 生成或优化策略代码
- **自主完善**：所有代码都在本地，可直接编辑、调试、运行

## 十、数据库数据源（推荐）

### 10.1 为什么使用数据库数据源？

- ✅ **离线回测**：数据存储在本地 SQLite，无需每次联网
- ✅ **快速访问**：数据库查询比 API 调用快得多
- ✅ **数据持久化**：历史数据不会丢失
- ✅ **批量管理**：可以批量获取和管理多只股票数据

### 10.2 按需拉取（推荐，无需全量导入 A 股）

在 Web 平台选择「数据库」数据源时，**若本地没有该股票在回测区间的数据，会自动从 AKShare 按需拉取并写入数据库**，再执行回测。因此：

- 无需事先导入全部 A 股数据，节省内存和硬盘。
- 数据库只保存「被回测过的股票」的数据，随使用增长。
- 可选：仍可提前同步部分标的（见下方），用于离线回测。

详见：`docs/ON_DEMAND_DATA.md`。

#### 可选：提前同步部分股票

```bash
# 获取闻泰科技数据（示例）
python database/sync_data.py --wentai

# 获取指定股票数据
python database/sync_data.py --symbol 600745 --days 365

# 批量获取策略股票数据
python database/sync_data.py --strategy

# 更新所有股票数据
python database/sync_data.py --update-all
```

#### 使用数据库数据源运行回测

```bash
# 使用数据库数据源（推荐）
python run_backtest_db.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31

# 对比：使用原始适配器（需要联网）
python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31
```

### 10.3 数据库结构

- **位置**：`data/astock.db` (SQLite)
- **表结构**：
  - `stocks`: 股票基本信息
  - `daily_bars`: 日线行情数据
  - `trading_calendar`: 交易日历

详细说明请参考：`database/README.md`

## 十一、注意事项

1. **数据源选择**：
   - **数据库数据源**（推荐）：适合离线回测，数据已缓存
   - **AKShare 适配器**：适合实时数据获取，需要网络连接
2. **数据更新**：建议定期运行 `database/sync_data.py` 更新数据库
3. **数据量**：单只股票一年约 250 条日线数据，注意数据库大小
4. **商业使用**：RQAlpha 仅限非商业使用，商业使用需联系 ricequant

## 十二、版本控制与 Git 上传

- **不要提交**：`data/*.db`、`data/**/*.csv`（体积大，且 GitHub 单文件限制 100MB）。详见 `.gitignore`。
- **克隆后**：需自行安装 akshare、rqalpha（`pip install akshare rqalpha`），数据库可运行 `scripts/import_all_a_stocks.py` 或通过 Web 平台按需拉取。
- **推送前**：确认无大文件（如 `data/astock.db`），避免 `remote rejected`。

---

**项目状态**：✅ 已配置完成，可直接使用。支持自主完善、调整和扩展。
