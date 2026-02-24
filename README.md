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

### 先启动 Web 平台（避免 ERR_CONNECTION_REFUSED）

若浏览器提示「无法访问此网站 / localhost 拒绝了我们的连接请求」，说明 **服务未启动**。在项目根目录执行：

```bash
# 方式一：一键脚本（推荐）
./start_platform.sh

# 方式二：手动启动
source venv/bin/activate
python web_platform.py
```

终端出现「访问 http://127.0.0.1:5050 使用平台」后，用浏览器打开 **http://127.0.0.1:5050** 或 **http://localhost:5050**。按 Ctrl+C 可停止服务。

**新界面（市场扫描器、名称/去年营收/去年净利润等）**：需先构建前端，5050 才会托管 React 界面；否则为旧版单页。在项目根目录执行：
```bash
cd frontend && npm run build && cd ..
```
之后重启 `python web_platform.py`，访问 http://127.0.0.1:5050 并点击「市场扫描器」即可看到新表格。

**市场扫描器功能**：点击表头可排序（标的、价格、买点概率等）；点击某行可打开右侧抽屉，查看该股票详情与 K 线图。若改动未生效，请执行 `./scripts/rebuild_and_start.sh` 并**强制刷新浏览器**（Cmd+Shift+R 或 Ctrl+Shift+R）。

### 使用 AKShare 数据源（无需数据库）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 命令行回测（推荐）
python run_backtest_akshare.py strategies/simple_akshare_strategy.py 2024-01-01 2024-12-31 600745.XSHG

# 3. 或启动简易 Web 平台
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

### 前 9 月训练 + 后 3 月验证（样本外轮巡）

结合现有数据，轮巡多标的×多策略，验证策略在样本外是否可行：

```bash
source venv/bin/activate
python scripts/walk_forward_validate.py
# 侧重 MACD+KDJ 组合（经验较有效）
python scripts/walk_forward_validate.py --strategies macd,kdj
# 限制标的数
python scripts/walk_forward_validate.py --stocks 5
# 输出 CSV 报告
python scripts/walk_forward_validate.py --csv output/wf_report.csv
# 结束后发送到飞书（需设置 FEISHU_WEBHOOK_URL）
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
python scripts/walk_forward_validate.py --feishu
```

### 批量回测验证（多标的 × 多策略）

使用 002701、600598、300212 等标的，批量跑通所有策略，确保项目能满足多数 A 股的分析与回测：

```bash
source venv/bin/activate
python scripts/run_all_backtests.py
# 可选：指定标的与区间
python scripts/run_all_backtests.py 002701.XSHE 600598.XSHG 300212.XSHE 2025-02-20 2026-02-20
```

通过即表示当前 7 个策略 × 3 只标的共 21 组回测均能正常完成。发布或修改策略/数据层后建议跑一遍以回归。

### 新闻舆情（东方财富、财新、抖音占位）

采集热点新闻并做舆情分析：

```bash
source venv/bin/activate
python scripts/fetch_news_sentiment.py 600519
```

- **东方财富**：个股/关键词新闻（`akshare.stock_news_em`）
- **财新**：热点财经新闻（`akshare.stock_news_main_cx`）
- **抖音**：占位（需开放平台或第三方数据）
- **舆情分析**：简单情感打分（可扩展 SnowNLP、NLP 模型）

Web API：`GET /api/news?symbol=600519&sources=eastmoney,caixin`

### 多策略组合系统（私募级）

支持多策略、多标的、权重分配、风险平价、定期再平衡、策略归因：

```bash
source venv/bin/activate
python run_portfolio_multi.py
```

- **MultiStrategyPortfolio**：主编排，支持 `run_backtest`（数据库）与 `run_with_paper_trading`（AKShare + 模拟交易）
- **CapitalAllocator**：等权 / 风险平价 / 夏普最大化
- **PortfolioRebalancer**：按日/周/月再平衡
- **StrategyAttribution**：各策略收益贡献度

### 全量同步股票池（多标的策略推荐）

策略2/策略1 等会用到多只股票，若数据库缺少部分标的或日期会出现「No market data」。可先全量同步股票池再回测：

```bash
source venv/bin/activate
python scripts/sync_pool_stocks.py
# 指定区间
python scripts/sync_pool_stocks.py --start 20240220 --end 20260220
```

或在 Web 回测页点击 **「📦 全量同步股票池」**，会按当前回测开始/结束日期拉取 data/ 下所有策略 CSV 中的股票日线并写入数据库（需网络，耗时数分钟）。

### 已有 SQLite 全量日线时：直接复制到 DuckDB（推荐，最快）

若 `data/astock.db` 里已经有全部日线（例如之前全量拉取过），**无需再拉取**，直接把 SQLite 拷贝到 DuckDB 即可，本地复制、不占网络，通常几十秒完成：

```bash
python scripts/migrate_sqlite_to_duckdb.py
```

生成 `data/quant.duckdb` 后，平台会默认使用 DuckDB。

### 全量导入 A 股（无 SQLite 或需补全时，需网络）

将沪深京 A 股全部股票（约 5000+ 只）的日线从 AKShare 拉取并写入本地数据库，回测时可任意选股、多标的策略不再缺数据：

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

### 控制台出现 content.js / antd / chunk-*.js / chrome-extension 报错

这些来自**浏览器扩展**（如 React DevTools、阿里通义等），不是本项目的代码。可忽略，或在无扩展的隐身窗口/新配置文件中打开 http://127.0.0.1:5050 以确认页面功能正常。

### `npm run build` 报错：Library not loaded libsimdjson.28.dylib（macOS Homebrew Node）

这是本机 **Node 与 Homebrew simdjson 版本不匹配**导致的，不是项目代码问题。任选其一即可：

1. **重装 Node，让其重新链接当前 simdjson**：
   ```bash
   brew reinstall node
   ```
2. **或重装 simdjson 并重链**：
   ```bash
   brew reinstall simdjson
   brew link --overwrite simdjson
   ```
3. **或改用 nvm 安装的 Node**（不依赖 Homebrew 的 simdjson）：
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
   # 重启终端后
   nvm install 20
   nvm use 20
   cd frontend && npm run build
   ```

### 若出现「无法访问此网站 / 连接被拒绝」(ERR_CONNECTION_REFUSED)

1. **确认服务已启动**：在项目根目录执行  
   `./start_platform.sh` 或  
   `source venv/bin/activate && python web_platform.py`
2. **使用正确端口**：平台默认使用 **5050**（避免与 macOS 占用的 5000/5001 冲突），浏览器访问 **http://127.0.0.1:5050**
3. **自检**：终端执行 `curl -s http://127.0.0.1:5050/health`，若返回 `{"status":"ok"}` 表示服务正常
4. **换端口**：若 5050 被占用，可执行 `PORT=8080 python web_platform.py`，然后访问 http://127.0.0.1:8080
5. **DuckDB**：若存在 `data/quant.duckdb`（执行 `python scripts/migrate_sqlite_to_duckdb.py` 生成），平台默认使用 DuckDB；用 `USE_DUCKDB=0` 可改回 SQLite  
6. **数据已有 SQLite 时**：若 `data/astock.db` 里已有全部日线，**直接复制到 DuckDB 即可**，比从网络全量拉取快得多：`python scripts/migrate_sqlite_to_duckdb.py`（本地拷贝，通常几十秒完成）

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
├── frontend/              # 专业量化前端（React + TS + TradingView 风格）
│   ├── src/pages/         # 交易决策中心、策略实验室、市场扫描器
│   ├── COMPONENT_STRUCTURE.md
│   └── npm run dev        # 开发（需先启动 web_platform.py，API 代理到 5050）
├── run_akshare.py         # AKShare 快速测试脚本
├── app.py                  # AKShare 数据展示 Web 页面
├── web_platform.py         # 量化交易平台 Web 界面（含 /api/kline、/api/signals、/api/ai_score、/api/backtest、/api/scan）
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

## 十一、机构级量化模块（私募级）

在「数据 → 回测 → 实盘」闭环基础上，已接入 **高频因子库、LSTM 预测、多策略组合、实盘监控**，达到私募量化中等水平。

### 11.1 目录结构

```
quant_system/
├── factors/           # Alpha 因子库
│   ├── alpha_factors.py   # 动量/波动率/量价/趋势/偏度峰度等 20+ 因子
│   └── factor_engine.py   # 统一特征矩阵输出
├── ai_models/         # 深度学习
│   ├── lstm_model.py      # LSTM 序列 → 未来 1 日收益
│   ├── train_lstm.py      # 训练脚本
│   └── predict_lstm.py   # 预测脚本
├── portfolio/         # 多策略组合
│   ├── strategy_pool.py       # 策略池 run()
│   ├── capital_allocator.py   # 资金分配（等权/可扩展风险平价）
│   └── portfolio_manager.py  # 持仓与总资产
└── monitor/           # 实盘监控
    ├── api_server.py        # FastAPI：/positions, /orders, /pnl
    └── dashboard/           # 监控页（持仓/订单/PnL/图表）
```

### 11.2 依赖（可选）

机构级模块依赖需单独安装：

```bash
pip install torch fastapi uvicorn
```

或使用项目提供的清单（若存在）：

```bash
pip install -r requirements-institutional.txt
```

### 11.3 使用方式

**因子 + 特征矩阵（与现有 DataFrame 兼容）**

```python
from factors import add_alpha_factors, build_factor_matrix
import pandas as pd
# df 需含 open, high, low, close, volume
df = build_factor_matrix(df, keep_date=True)
```

**LSTM 训练与预测**

```bash
# 训练（示例假数据）
python ai_models/train_lstm.py

# 预测：在代码中调用 predict_from_df(feature_matrix) 或 load_lstm + predict
```

**多策略组合与资金分配**

```python
from portfolio.strategy_pool import StrategyPool
from portfolio.capital_allocator import CapitalAllocator
from portfolio.portfolio_manager import PositionTracker

pool = StrategyPool()
pool.add(strategy_a).add(strategy_b)
results = pool.run(df)
alloc = CapitalAllocator().allocate(1_000_000, pool.strategies)
pm = PositionTracker(capital=alloc.get(strategy_a, 0))
pm.update("600519.XSHG", 100000)
print(pm.total_value())
```

**实盘监控 API + Dashboard**

```bash
uvicorn monitor.api_server:app --reload --host 0.0.0.0 --port 8000
# 浏览器打开 http://127.0.0.1:8000 查看 Dashboard；API 文档 http://127.0.0.1:8000/docs
```

### 11.4 建议的下一步

1. **回测**：用历史 10 年数据回测因子与策略。
2. **模拟盘**：跑 3 个月模拟盘验证稳定性。
3. **小资金实盘**：市场验证优于自我检查。

### 11.5 顶级量化扩展（百亿私募路线）

在机构级模块之上，已接入 **强化学习交易、Tick 高频框架、AutoML 因子挖掘、机构级风险预测与仓位控制**，架构达到国内头部私募技术中枢水平。

| 模块 | 路径 | 说明 |
|------|------|------|
| 强化学习交易 | `rl/` | Gymnasium 环境 + stable-baselines3 PPO，状态=价格/指标/仓位，动作=空仓/买/卖 |
| Tick 高频框架 | `hft/` | 行情流 → 信号引擎 → 下单/风控，`TickEngine.on_tick(tick)` 驱动 |
| AutoML 因子挖掘 | `automl/` | Optuna + sklearn 自动搜索因子与超参，最大化 CV 得分 |
| 风险预测 AI | `risk/risk_model.py` | XGBoost 预测回撤/爆仓/亏损概率 |
| 仓位控制器 | `risk/position_sizer.py` | 根据 risk_prob 动态调整可用资金比例 |

**整体架构（完成后）：**

```
market_data/  factor_engine/  automl/  ai_models/  rl/  hft/
portfolio/    risk/            arbitrage/  evolution/  fund_platform/  monitor/
```

**终极阶段模块（世界顶级路线）：**

| 模块 | 路径 | 说明 |
|------|------|------|
| AI 自进化交易 | `evolution/` | 策略基因编码、变异/交叉、种群进化，回测适应度自动生成策略 |
| 高频做市 | `hft/market_making.py` | 双边报价赚取价差，库存 skew、最大仓位控制 |
| 多市场套利 | `arbitrage/` | 价差监控（SpreadMonitor）、多对套利引擎（ArbEngine） |
| 量化基金管理 | `fund_platform/` | NAV、投资者台账、申赎、`FundManager` + `/fund` API |

**依赖（顶级模块）：**

```bash
pip install gymnasium stable-baselines3 optuna xgboost scikit-learn
# 或一并安装
pip install -r requirements-institutional.txt
```

**使用示例：**

```bash
# RL 训练（示例价格序列）
python rl/train_rl.py

# AutoML 因子搜索（需准备 X, y）
# from automl import run_factor_search
# study = run_factor_search(X, y, n_trials=50)

# 风险模型 + 仓位控制
# from risk import RiskModel, PositionSizer
# rm = RiskModel().train(X_risk, y_risk)
# prob = rm.predict(X_live)
# size = PositionSizer().size(capital, prob)
```

**终极阶段使用示例：**

```python
# AI 自进化：策略基因进化，fitness 可接回测夏普
# from evolution import StrategyEvolver, StrategyGene
# ev = StrategyEvolver(population_size=50, top_k=10)
# best = ev.evolve(n_generations=20)

# 高频做市：按 mid 与库存报价
# from hft import MarketMakingEngine
# mm = MarketMakingEngine(half_spread_bps=5, max_position=1000)
# mm.on_tick(mid=100.5); mm.on_fill("BUY", 100, 100.5)

# 多市场套利：价差突破上下轨发信号
# from arbitrage import SpreadMonitor, ArbEngine
# arb = ArbEngine(); arb.add_pair("A-B", upper=0.5, lower=-0.5)
# arb.update("A-B", price_a=10.2, price_b=9.8)

# 基金管理：NAV、申赎
# from fund_platform import FundManager
# fm = FundManager(initial_capital=1_000_000)
# fm.update_aum(1_050_000, "2025-02-20")
# fm.subscribe("investor_01", 100_000, "2025-02-20")
# fm.redeem("investor_01", 500, "2025-02-21")
# 将 fm 注入 fund_platform.api 后，可暴露 /fund/nav、/fund/subscribe 等 API
```

### 11.6 关键建议（真心话）

- **数据质量**：没有高质量数据 = 全部白搭。优先 A 股 Level2、Tick、财务数据。
- **交易成本**：回测赚钱、实盘亏钱常因手续费+滑点，必须在回测中模拟真实成本。
- **风控优先**：活着比赚钱重要；风控优先级 > 策略。

---

## 十二、注意事项

1. **数据源选择**：
   - **数据库数据源**（推荐）：适合离线回测，数据已缓存
   - **AKShare 适配器**：适合实时数据获取，需要网络连接
2. **数据更新**：建议定期运行 `database/sync_data.py` 更新数据库
3. **数据量**：单只股票一年约 250 条日线数据，注意数据库大小
4. **商业使用**：RQAlpha 仅限非商业使用，商业使用需联系 ricequant

## 十三、版本控制与 Git 上传

- **不要提交**：`data/*.db`、`data/**/*.csv`（体积大，且 GitHub 单文件限制 100MB）。详见 `.gitignore`。
- **克隆后**：需自行安装 akshare、rqalpha（`pip install akshare rqalpha`），数据库可运行 `scripts/import_all_a_stocks.py` 或通过 Web 平台按需拉取。
- **推送前**：确认无大文件（如 `data/astock.db`），避免 `remote rejected`。

---

**项目状态**：✅ 已配置完成，可直接使用。支持自主完善、调整和扩展。
