# 政策新闻采集与 API（由 OpenClaw 工作区并入）

- `news_collector.py`：抓取政务/媒体源、分类与情绪规则、写入 SQLite、可选 `openclaw message` 推飞书。
- `news_database.py`：`init` / `stats` / `api`（FastAPI + uvicorn，**8001**）；库文件在 `sqlite/news.db`。

## 依赖

```bash
pip install requests beautifulsoup4 fastapi uvicorn
```

## 初始化与启动 API

```bash
cd integrations/hongshan/hongshan-quant-platform
chmod +x start-news-api.sh
./start-news-api.sh
```

前端开发时 `vite` 已将 `/news` 代理到 `http://127.0.0.1:8001`，见 `hongshan-quant-platform/vite.config.js`。

## 手动采集

```bash
cd integrations/hongshan/policy-news
python3 news_collector.py
```

## 飞书推送目标

环境变量 `FEISHU_POLICY_NOTIFY_OPEN_ID`（飞书用户 open_id）；未设置时使用脚本内可调默认值。

## 定时任务示例

```cron
30 8 * * * cd /path/to/newhigh/integrations/hongshan/policy-news && /usr/bin/python3 news_collector.py >> ../logs/policy_collector.log 2>&1
```

## LaunchAgent 示例

见同目录 `com.newhigh.news-api.plist.example`（将路径替换为本机 newhigh 根目录后 `cp` 到 `~/Library/LaunchAgents/` 并 `launchctl load`）。
