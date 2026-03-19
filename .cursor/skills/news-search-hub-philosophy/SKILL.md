---
name: news-search-hub-philosophy
description: 新闻与舆情检索的分层策略：站内东财/DuckDB 快讯 + 借鉴 AI-Search-Hub「多平台原生搜索」补抖音/公众号/X 等。在用户要 A 股公告向新闻时用 GET /api/news；要社媒热点、公众号、海外舆情时说明局限并建议豆包/元宝/Grok 等路径或外部 AI-Search-Hub。与 a-stock-ai-research、mx-data 协同。
---

# 新闻搜索（对齐 [AI-Search-Hub](https://github.com/minsight-ai-info/AI-Search-Hub) 理念）

## 第一层：newhigh 站内（优先）

- **`GET /api/news?symbol=&limit=`** — DuckDB → akshare 东方财富个股新闻。
- **`POST /api/research/news-summary`** — 对已获新闻做投研向摘要（需 Gateway 配大模型 Key）。
- **妙想 mx-data** — 偏行情/财务/公告类权威数据，非社媒爬虫。

适用：**A 股标的公告链、东财快讯、投研页一键拉新闻**。

## 第二层：大厂原生搜索（理念借鉴）

AI-Search-Hub 的做法是：**同一问题，多平台各搜一圈**，用各平台已接好的数据世界（见对方 README：Gemini / Grok / 豆包 / 元宝 / 通义等），**少写脆弱爬虫**。

| 用户意图 | 建议 |
|----------|------|
| 抖音/今日头条热点、中文短视频舆情 | 说明站内无直连；可建议用户用 **豆包** 等带联网的会话，或本机跑 [AI-Search-Hub](https://github.com/minsight-ai-info/AI-Search-Hub) `--site doubao` |
| 微信公众号文章检索 | **元宝** 方向；同上 Hub 或手动检索后粘贴 |
| X/Twitter、海外实时讨论 | **Grok**；Hub `--site grok` |
| 全球网页、英文源 | **Gemini** |

**不要**在 newhigh 内假装已抓取上述源；应明确：**站内仅 L1，L2 需外部工具或用户粘贴**。

## 工作流建议

1. 先 **`/api/news` + 摘要** 覆盖公告向。  
2. 若用户明确要「抖音在说什么」「公众号怎么说」→ 引导 Hub 或对应平台 AI，**把结果贴回**再继续分析。  
3. 输出合并时标注**来源层级**（站内 / 外部检索）。

## 文档

详见仓库 **`docs/NEWS_SEARCH_AI_SEARCH_HUB.md`**。

## OpenClaw

可将 AI-Search-Hub 作为**独立 Skill** 与本项目并列；聚合结果再喂给 newhigh 投研摘要接口，形成「多源搜 → 统一风控表述」链路。
