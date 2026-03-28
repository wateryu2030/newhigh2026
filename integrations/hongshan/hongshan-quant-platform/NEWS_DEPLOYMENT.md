# 红山量化 — 政策新闻板块（已并入 newhigh 主仓）

功能：采集国务院/新华网等摘要、SQLite 存储、FastAPI（8001）、Vue「💰 金融」页展示。

## 目录（主仓内）

- `integrations/hongshan/policy-news/`：`news_database.py`、`news_collector.py`、定时脚本与说明
- `integrations/hongshan/hongshan-quant-platform/src/views/FinanceNews.vue`：金融新闻页
- `integrations/hongshan/policy-news/sqlite/`：本地 `news.db`（目录已 gitignore）

## 快速启动

1. Python：`pip install requests beautifulsoup4 fastapi uvicorn`
2. API：`cd integrations/hongshan/hongshan-quant-platform && chmod +x start-news-api.sh && ./start-news-api.sh`
3. 前端：`cd integrations/hongshan/hongshan-quant-platform && npm ci && npm run dev`
4. 开发环境下新闻 API 经 Vite 代理：请求 `/news/...` → `http://127.0.0.1:8001/news/...`，无需单独配 `VITE_NEWS_API_URL`。若直连，可设置 `VITE_NEWS_API_URL=http://127.0.0.1:8001`。

更多运维说明见 `../policy-news/README.md`。
