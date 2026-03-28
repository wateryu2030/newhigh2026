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

## Awesome Finance Skills（OpenClaw / 飞书机器人曾提示安装）

- **本机 OpenClaw 工作区** `~/.openclaw/workspace/skills/` 当前**无** `awesome-finance`；仅有 `stock-data`、`backtest`、`risk-monitor` 等。
- 上游仓库 [RKiding/Awesome-finance-skills](https://github.com/RKiding/Awesome-finance-skills) **仅有 `main` 分支**；`alphaear-news` 已不存在，`npx skills add ...@alphaear-news` 会失败。
- 网络正常时可尝试：`cd ~/.openclaw/workspace && npx skills add RKiding/Awesome-finance-skills --yes`（或 `git clone` 到 `skills/awesome-finance`）；需代理时设置 `https_proxy`。
- 红山「金融新闻」页不依赖该包；安装后可再接到 OpenClaw 工具链。
