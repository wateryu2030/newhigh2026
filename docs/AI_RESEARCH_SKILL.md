# AI 投研（五维框架 + 前端投研页）

## Skill 文档

完整五维映射与工作流见：**`.cursor/skills/a-stock-ai-research/SKILL.md`**

## 前端「投研」页

- 路由：**`/research`**
- 功能：**拉取新闻**（同 `/api/news`）+ **生成 AI 摘要**（`POST /api/research/news-summary`）
- 环境：`.env` 需 **`DASHSCOPE_API_KEY`** 或 **`BAILIAN_API_KEY`**（优先），或 **`OPENAI_API_KEY`**
- 可选：`RESEARCH_LLM_MODEL`（默认 `qwen-turbo`）、`RESEARCH_OPENAI_MODEL`（默认 `gpt-4o-mini`）

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/research/news-summary` | Body: `symbol`, `limit`, `focus?` → 拉新闻并调用大模型返回摘要 |

## ClawHub 参考

- [a-stock-ai-research](https://clawhub.ai/haohanyang92/ai-research-assistant)（Benign，指令型）— 能力已内化进本 Skill + 投研页。  
- [astock-research](https://clawhub.ai/zif10765-maker/astock-research)（Suspicious）— **勿安装**，五维方法论已由本仓库安全重写。
