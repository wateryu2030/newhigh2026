# 无 Cursor / 无人值守运行说明

本项目**不依赖 Cursor**：日常运行靠本机 **Python 虚拟环境、`.env`、LaunchAgent（可选）与 nohup 脚本**。Cursor 仅用于开发。

## 迭代要点（当前）

| 组件 | 作用 | 与 Cursor 关系 |
|------|------|----------------|
| **Gateway** (`uvicorn gateway.app:app`) | 启动时 `gateway/app.py` 加载根目录 `.env` | 无关 |
| **隧道栈** `scripts/run_tunnel_stack.sh` | `source .env` 后起 Gateway + `next start` | 无关 |
| **调度器** `scripts/start_schedulers.py` | 入口已调用 `lib/newhigh_env.load_dotenv_if_present`，子进程继承环境变量 | 已加固 |
| **股东采集 / 巡检** | `run_shareholder_collect.py`、`run_data_quality_checks.py`、`run_nightly_shareholder_coverage.py` 均会加载 `.env` | 已加固 |
| **晚间 22:15 巡检** | `SchedulerManager.run_nightly_shareholder_coverage()` 已实现（此前仅调用未定义方法会导致异常） | 已修复 |

## 本机常驻推荐（macOS）

1. **`.env`**：放在仓库根目录，含 `TUSHARE_TOKEN`、`QUANT_SYSTEM_DUCKDB_PATH`（若不用默认路径）等。勿提交 Git。
2. **虚拟环境**：`python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. **对外站点（Cloudflare Tunnel）**  
   - 安装：`cp config/com.newhigh.tunnel-stack.plist ~/Library/LaunchAgents/`（路径按你机器改 plist 内 `WorkingDirectory` / 脚本路径）  
   - `launchctl load ~/Library/LaunchAgents/com.newhigh.tunnel-stack.plist`
4. **调度器（定时任务）**  
   - `config/com.newhigh.scheduler.plist` 内为示例绝对路径，需改成你的 `NEWHIGH_ROOT`。  
   - 复制到 `~/Library/LaunchAgents/` 后 `launchctl load`。

## 手动启动（不装 launchd）

```bash
cd /path/to/newhigh && source .venv/bin/activate
bash scripts/restart_gateway_frontend.sh
# 或生产前端：
# NEWHIGH_FRONTEND_PROD=1 bash scripts/restart_gateway_frontend.sh
```

调度器前台：

```bash
python scripts/start_schedulers.py monitor
```

## 注意

- **plist 中的路径**（如 `/Users/apple/Ahope/newhigh`）仅为示例，换机器或目录需同步修改。
- **东财 akshare** 若遇代理错误，与 Cursor 无关；请用 Tushare 渠道或调整系统代理，见数据页 FAQ / `scripts/backfill_a_stock_daily.py`。
- **OpenClaw / 进化脚本**（如 `scripts/cursor_evolution_cycle.sh`）名称含 cursor，仅为开发自动化，**生产数据管道不依赖**。
