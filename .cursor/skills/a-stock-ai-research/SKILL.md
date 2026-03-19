---
name: a-stock-ai-research
description: A 股 AI 投研：五维分析框架（基本面/资金/技术/情绪/消息）+ 研报公告解读 + 新闻 AI 摘要。与用户问个股深度分析、利好利空、策略可行性时使用。联动前端「投研」页、GET/POST /api/research/news-summary、mx_data、行情/新闻/回测 API。参考 ClawHub a-stock-ai-research；勿安装 astock-research 等含硬编码密钥的 zip。
---

# A 股 AI 投研（整合 newhigh）

## 一、五维分析框架（对标同花顺/萝卜式投研）

分析顺序建议：**基本面 → 资金面 → 技术面 → 情绪面 → 消息面 → 交易预案 → 结论**。五维闭环，数据说话，风险优先。

### 1. 基本面（宏观 + 微观）

| 子维度 | 要点 | **newhigh 数据映射** |
|--------|------|----------------------|
| 宏观 | 大盘环境、政策与风险偏好 | 上证指数等：`mx-data` 自然语言查指数；`/api/market/summary` |
| 微观-公司 | 主营、行业地位 | `mx-data` 查公司概况、主营业务 |
| 微观-财务 | 营收利润、增速、ROE、负债 | `mx-data` 查财报指标；Tushare（若已接） |
| 估值 | PE/PB/股息 | `mx-data`；本地日 K + 市值可粗算 |

**缺数时**：明确写出「缺某某数据，建议用妙想/交易所公告核对」，勿编造。

### 2. 资金面

| 子维度 | 要点 | **newhigh 数据映射** |
|--------|------|----------------------|
| 主力/成交额/换手 | 资金关注度 | `a_stock_realtime`、`market_signals`（volume/trend）；mx_data 查资金流向 |
| 股东与筹码 | 机构持仓、户数变化、解禁 | 以 mx_data / 公告为准；库内龙虎榜、游资席位辅助 |

### 3. 技术面

| 子维度 | 要点 | **newhigh 数据映射** |
|--------|------|----------------------|
| 趋势与均线 | 多空头排列 | `/api/market/klines`（A 股日线 DuckDB）；feature-engine RSI/MACD/ATR |
| 支撑压力/K 线形态 | 结合量价 | K 线序列自算；扫描器 trend 类信号可参考 |

### 4. 情绪面

| 子维度 | 要点 | **newhigh 数据映射** |
|--------|------|----------------------|
| 全市场热度 | 涨跌家数、涨停比 | 行情页 **7 维情绪**；`/api/market/sentiment-7d` |
| 情绪周期 | 冰点/主升/退潮等 | `/api/market/emotion`；`EmotionCycleModel` / `market_emotion` 表 |
| 个股活跃度 | 换手、量价 | 实时表、狙击候选 `sniper_candidates` |

### 5. 消息面

| 子维度 | 要点 | **newhigh 数据映射** |
|--------|------|----------------------|
| 公告/业绩/资本运作 | 预告、财报、增减持、重组 | 用户粘贴 + **前端「投研」页**：拉新闻 + **AI 摘要**（`POST /api/research/news-summary`） |
| 行业与政策 | 新闻聚合 | `GET /api/news?symbol=`；投研页一键摘要 |
| 抖音/公众号/X 等社媒舆情 | 东财链外 | 站内不覆盖 → 见 **news-search-hub-philosophy** skill 与 `GET /api/news/coverage`；可配合 [AI-Search-Hub](https://github.com/minsight-ai-info/AI-Search-Hub) 理念扩展 |

---

## 二、交易预案（输出模板）

- **剧本 A 上涨突破**：触发条件、目标区间、止损参考。  
- **剧本 B 下跌破位**：触发与应对。  
- **剧本 C 震荡**：区间与策略。  
- **剧本 D 观望**：等待催化剂。  

每项需与五维中的至少两维呼应，避免单点臆测。

---

## 三、前端「投研」能力（已实现）

- 路径：**`/research`**（导航「投研」）。
- **拉取新闻**：`GET /api/news`（与代码框一致）。
- **生成 AI 摘要**：`POST /api/research/news-summary`，Body：`{ "symbol": "000001", "limit": 30, "focus": "可选关注点" }`。  
- **模型**：优先 `DASHSCOPE_API_KEY` / `BAILIAN_API_KEY`（默认 `qwen-turbo`，可用环境变量 `RESEARCH_LLM_MODEL` 覆盖）；否则 `OPENAI_API_KEY`（`RESEARCH_OPENAI_MODEL` 默认 `gpt-4o-mini`）。

---

## 四、与其他能力联动（优先顺序）

1. **权威数字**：**mx-data**（`MX_APIKEY`）妙想 API。  
2. **新闻 + 摘要**：投研页或 `/api/news` + `/api/research/news-summary`。  
3. **深度脚本**：`personal_assistant`（`deep_analyzer`、`run_daily`）。  
4. **回测解读**：`/api/backtest/run`、`/api/backtest/result`；只解读已有结果，不虚构回测数据。

---

## 五、核心能力（执行方式）

### 研报 / 公告

- 核心观点、盈利预测与假设、风险提示；**300 字以内摘要**。

### 策略 / 回测

- 过拟合、样本外、规则可行性；缺数据则要求跑回测或贴结果。

### 触发话术示例

「分析这只股票」「最近有什么利好」「这个公告说了什么」「策略靠不靠谱」

---

## 六、输出规范与安全

- 中文、小标题 + 列表；数字标注来源（API/表/公告）。  
- 末尾 **不构成投资建议**。  
- 勿向模型粘贴 **API Key、密码、内幕信息**。  
- **禁止**安装 [astock-research](https://clawhub.ai/zif10765-maker/astock-research) 等含硬编码密钥与绝对路径脚本的 ClawHub 包。

---

## 七、溯源

- 轻量投研指令参考：[ClawHub · a-stock-ai-research](https://clawhub.ai/haohanyang92/ai-research-assistant)。  
- 五维框架理念参考公开投研体系（同花顺/萝卜式），**数据层全部由 newhigh + mx_data 落地**。
