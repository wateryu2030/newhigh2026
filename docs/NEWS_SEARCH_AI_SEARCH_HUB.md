# 新闻搜索 × [AI-Search-Hub](https://github.com/minsight-ai-info/AI-Search-Hub) 理念对齐

## 对方在解决什么

[AI-Search-Hub](https://github.com/minsight-ai-info/AI-Search-Hub) 的核心思想是：

- **一次提问，多平台分发**：同一问题交给 Gemini / Grok / 豆包 / 元宝等，各自用**平台原生搜索**去触达不同数据世界（Google 网页、X、抖音、微信公众号等）。
- **少造爬虫**：不维护脆弱解析与登录流，**借力大厂已接好的信源与排序**。
- **统一出口**：结果回收给 Agent / 工作流。

执行上依赖仓库内 **`scripts/run_web_chat.py`** 等浏览器自动化（Chrome Debug），适合本机 OpenClaw 外挂，**不宜直接打进 newhigh 主仓库**（依赖重、合规与 ToS 需自担）。

---

## newhigh 新闻现状（第一层：站内）

| 能力 | 实现 |
|------|------|
| 个股/市场快讯 | `GET /api/news`：DuckDB `news_items` → 兜底 **akshare 东方财富** |
| AI 摘要 | `POST /api/research/news-summary`：在已拉取文本上调用大模型 |
| 妙想数据 | mx-data：权威行情/财务类自然语言查数（与「社媒舆情」互补） |

这一层覆盖 **A 股公告向、东财源** 新闻，成本低、可定时落库，适合量化流水线。

---

## 借鉴理念后的「第二层：扩展舆情」（可选）

当用户要 **抖音热点、公众号深度、X/Twitter 实时、Google 英文源** 等，单靠东财链路易不够。对齐 AI-Search-Hub 的**路由思想**（见对方 [ROUTING.md](https://github.com/minsight-ai-info/AI-Search-Hub/blob/main/ROUTING.md)）：

| 需求类型 | 建议借力方向（理念对齐） |
|----------|---------------------------|
| 中文热点 / 短视频舆情 | 豆包等（字节系内容理解） |
| 微信公众号 / 腾讯系补充 | 元宝等 |
| X 实时 / 海外社交 | Grok |
| 全球网页发现 | Gemini |
| 通用中文搜索扩展 | 通义千问 |

**落地方式（推荐）**：

1. **OpenClaw / 本机**：按需克隆 [AI-Search-Hub](https://github.com/minsight-ai-info/AI-Search-Hub)，用其脚本跑一轮，将 **输出文本** 粘贴回 newhigh 投研对话或入库（不自动执行对方脚本于 Gateway）。
2. **API 路线**：若已有豆包/通义等 **官方 API + 联网搜索** 能力，可在后续单独加 `POST /api/news/augment`（设计预留），与第一层结果 merge。

---

## 与 OpenClaw 的配合

- OpenClaw 可把 **「深度舆情」** 标为 **外部 Skill**：调用 AI-Search-Hub 产出 → 再调用 newhigh `/api/research/news-summary` 做**统一摘要与风控表述**。
- newhigh 内 **Cursor Skill**：`news-search-hub-philosophy` 写明何时用站内 `/api/news`、何时建议走 Hub。

---

## 小结

| 层级 | 做法 |
|------|------|
| **L1 默认** | 继续用 DuckDB + 东财 + 投研摘要（量化友好） |
| **L2 扩展** | 理念借鉴 AI-Search-Hub：**多平台原生搜索**，通过 Hub 或官方联网 API 补抖音/公众号/X 等 |
| **L2（现有 Key）** | 见 **`docs/NEWS_CHANNELS_WITH_EXISTING_KEYS.md`**、`POST /api/news/web-insight`（豆包/通义 + 控制台联网插件） |
| **不做的** | 不把 Hub 的浏览器自动化绑进 Gateway 默认路径 |
