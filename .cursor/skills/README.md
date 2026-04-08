# newhigh 仓库内 Cursor Skills 索引（分工与去重）

本目录下 **4 个 SKILL** 是**分层协作**，不是同一能力的四份拷贝；Agent 按用户意图选 **一个主入口**，其余按需跳转。

## 分工一览（建议保留全部 4 个，勿合并为单文件）

| 技能 | 唯一职责 | 易混淆点（实际不重复） |
|------|----------|------------------------|
| **a-stock-ai-research** | 个股/策略向 **五维投研主流程**（基本面→…→消息→结论） | 内含对 mx/news/monitor 的 **引用**，不替代各 skill 的细节 |
| **mx-data** | **妙想 API** 调用约定（`MX_APIKEY`、POST、自然语言查数） | 只解决「权威数字从哪来」；不做投研叙事与全市场情绪 |
| **news-search-hub-philosophy** | **新闻/舆情分层**：站内 `/api/news` vs 站外 Hub/大模型联网 | 与投研 skill 的「消息面」互补；**不**重复 mx 的行情财务能力 |
| **a-stock-monitor-sanitized** | **全市场** 7 维情绪与快照 API（`sentiment-7d`、`realtime` 等） | 投研 skill 里「情绪面」偏个股/五维；本 skill 偏 **大盘仪表盘** |

**结论**：无需因「都叫 A 股」而删掉其中一个；删掉任意一个会丢失 **API 细节** 或 **工作流边界**。

## 与 `tools/x-tweet-fetcher` 的关系

- `tools/x-tweet-fetcher/SKILL.md` 是 **独立工具**（拉 X/微博等），**不在** `.cursor/skills/`。
- 与 **news-search-hub-philosophy** 的关系：哲学层仍建议「站外/分层标注」；若本机已装 Camofox 等，可用该工具作为 **L2 补充**，并在回答里标明来源层级。

## 与 `~/.agents/skills`（addyosmani）的关系

- **addyosmani**：通用工程（spec、UI、规划、ADR 等）。
- **本目录**：newhigh **域内**数据链路与投研。**二者并列**，无合并必要。

## 文档中的「重复」

- `docs/AI_RESEARCH_SKILL.md`：仅 **投研页 + API 速查**，五维正文以 **`a-stock-ai-research/SKILL.md`** 为准——属于 **索引 vs 权威** 分工，可保留。
- `docs/NEWS_SEARCH_AI_SEARCH_HUB.md`、`docs/CLAWHUB_A_STOCK_MONITOR_INTEGRATION.md`：专题说明，与对应 skill 交叉引用即可。

## 若仍想减少文件数（不推荐）

唯一折中：把 **a-stock-monitor-sanitized** 全文并入 **a-stock-ai-research** 某一节，并全局改链接——会显著拉长主 skill、降低「问大盘情绪」时的检索精度。**默认不建议。**
