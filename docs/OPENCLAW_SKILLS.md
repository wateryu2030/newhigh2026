# OpenClaw A股数据 Skill 集成说明

## 一、概述

在 OpenClaw 设计下，红山量化平台集成了 **A股数据 Skill**（`skills.a_share_skill`），基于 Tushare 提供 A 股行情、基本面、技术指标查询，供 Gateway API、进化引擎或脚本直接调用。

## 二、Skill 能力

| 函数 / API | 功能 | 入参示例 |
|------------|------|----------|
| `get_stock_basic` | 股票基本信息（代码、名称、行业、上市日期） | `name="贵州茅台"` 或 `ts_code="600519.SH"` |
| `get_daily_price` | 日线行情（开高低收、成交量、涨跌幅） | `ts_code="600519.SH", start_date="20240101"` |
| `get_tech_indicator` | 技术指标（MA5、MA10、MACD） | `ts_code="600519.SH"` |
| `get_finance_indicator` | 财务指标（PE、PB、ROE、毛利率） | `ts_code="600519.SH", year=2023` |

## 三、前置条件

1. **依赖**：`tushare`、`pandas`、`numpy`（见根目录 `requirements.txt`）。
2. **Tushare Token**：在 `.env` 中设置 `TUSHARE_TOKEN`（或在环境变量中）。  
   - 获取地址：https://tushare.pro/register  
   - Gateway 启动时会加载 `.env`，Skill 通过 `TUSHARE_TOKEN` 调用 Tushare 接口。

## 四、使用方式

### 1. 代码中加载（OpenClaw / 脚本）

```python
from skills.a_share_skill import load_skill

skill = load_skill()
# 查询股票基本信息
print(skill.get_stock_basic(name="贵州茅台"))
# 日线行情
print(skill.get_daily_price("600519.SH"))
# 技术指标
print(skill.get_tech_indicator("600519.SH"))
# 财务指标
print(skill.get_finance_indicator("600519.SH", year=2023))
```

### 2. 命令行测试

在项目根目录执行（需已激活 venv 并配置 `TUSHARE_TOKEN`）：

```bash
python -m skills.a_share_skill
```

### 3. Gateway API（HTTP）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skill/ashare/stock-basic?ts_code=&name=` | 股票基本信息 |
| GET | `/api/skill/ashare/daily?ts_code=&start_date=&end_date=` | 日线行情 |
| GET | `/api/skill/ashare/tech-indicator?ts_code=&start_date=&end_date=` | 技术指标 |
| GET | `/api/skill/ashare/finance-indicator?ts_code=&year=` | 财务指标 |

示例：

```bash
curl "http://127.0.0.1:8000/api/skill/ashare/stock-basic?name=茅台"
curl "http://127.0.0.1:8000/api/skill/ashare/daily?ts_code=600519.SH"
```

## 五、与现有数据管道的关系

- **Tushare 数据源**：`data_pipeline` 中已注册 `tushare_daily`，用于增量写入日 K 到 `a_stock_daily`，与 Skill 共用同一 `TUSHARE_TOKEN`。
- **股票池**：`POST /api/data/ensure-stocks` 使用 akshare 写入 `a_stock_basic`；Skill 的 `get_stock_basic` 为实时 Tushare 查询，二者可互补（本地池 + 实时信息）。

## 六、扩展建议

- 涨停/跌停判断、行业涨幅排行等可在此 Skill 内新增方法并暴露到 `/api/skill/ashare/*`。
- 可增加简单缓存（如按 `ts_code+date` 缓存日线）以减少 Tushare 调用频次。

## 七、延伸阅读

- 通用 OpenClaw 量化场景、ClawHub 技能示例与安全铁律：[`OPENCLAW_QUANT_ECOSYSTEM_AND_SAFETY.md`](./OPENCLAW_QUANT_ECOSYSTEM_AND_SAFETY.md)
