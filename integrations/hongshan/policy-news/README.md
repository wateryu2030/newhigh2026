# 政策新闻采集与 API（由 OpenClaw 工作区并入）

- `news_collector.py`：抓取政务/媒体源、分类与情绪规则；**仅写入**仓库统一 DuckDB 表 `news_items`（`symbol=__POLICY__`，与 Gateway 共用 `QUANT_SYSTEM_DUCKDB_PATH`）。
- `news_database.py`：`init`（`ensure_tables`）/ `stats` / `api`（FastAPI + uvicorn，**8001**）；读写与上相同的 `news_items` 政策行。

主站 Next「新闻 → 政策采集」走 Gateway `GET /api/news/collector`，亦读同一 DuckDB。**不再使用** `sqlite/news.db` 与 `POLICY_NEWS_DB_PATH`；若部署机仍留有旧目录可删除，不影响采集。

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

## 手动采集（推荐从仓库根）

```bash
cd /Users/apple/Ahope/newhigh   # 本机绝对路径
bash scripts/run_policy_news_collect.sh
# 或带 DNS 重试（与 LaunchAgent 示例一致）
bash scripts/run_policy_news_collect_retry.sh
```

## 飞书推送目标

环境变量 `FEISHU_POLICY_NOTIFY_OPEN_ID`（飞书用户 open_id）；未设置时使用脚本内可调默认值。

## 定时任务示例（勿用系统 Python 直跑脚本）

```cron
30 8 * * * cd /Users/apple/Ahope/newhigh && /bin/bash scripts/run_policy_news_collect_retry.sh >> logs/policy_cron.log 2>&1
```

## LaunchAgent 示例

见 `com.newhigh.news-api.plist.example`、`com.newhigh.policy-collector.plist.example`；安装到 `~/Library/LaunchAgents/` 后使用 `launchctl bootstrap gui/$(id -u) ...`。完整巡检见 **`docs/HEARTBEAT.md`**。

## Awesome Finance Skills（OpenClaw / 飞书机器人曾提示安装）

- **本机 OpenClaw 工作区** `~/.openclaw/workspace/skills/` 当前**无** `awesome-finance`；仅有 `stock-data`、`backtest`、`risk-monitor` 等。
- 上游仓库 [RKiding/Awesome-finance-skills](https://github.com/RKiding/Awesome-finance-skills) **仅有 `main` 分支**；`alphaear-news` 已不存在，`npx skills add ...@alphaear-news` 会失败。
- 网络正常时可尝试：`cd ~/.openclaw/workspace && npx skills add RKiding/Awesome-finance-skills --yes`（或 `git clone` 到 `skills/awesome-finance`）；需代理时设置 `https_proxy`。
- **addyosmani/agent-skills**（本机全局）：在 newhigh 根目录执行 `bash scripts/install_openclaw_addyosmani_skills.sh`，详见 `docs/OPENCLAW_运行说明.md` §0。
- 红山「金融新闻」页不依赖该包；安装后可再接到 OpenClaw 工具链。
