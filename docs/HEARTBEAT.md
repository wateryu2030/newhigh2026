# newhigh 心跳与无人值守巡检（HEARTBEAT）

定义**每日状态看板**、**一键自检/恢复**、**launchd 正确域**与故障 playbook。与 `docs/HEADLESS_AND_LAUNCHD.md` 互补。

---

## 〇、今日状态看板（可复制填写）

| 项目 | 状态 | 备注 |
|------|------|------|
| 今日 08:30 政策采集 | ☐ 成功 ☐ 失败 | 看 `logs/policy-collector.launchd.err.log` |
| 今日 `__POLICY__` 新增行数 |  | `heartbeat_check.sh` 会打印 |
| 政策 news-api :8001 | ☐ 可达 ☐ 未起 | 可选服务 |
| Gateway :8000 | ☐ 可达 | |
| launchd `news-api` | ☐ 运行中 ☐ 仅加载 ☐ 未装 | 见 §5 |
| launchd `policy-collector` | ☐ 运行中 ☐ 仅加载 ☐ 未装 | Calendar 任务无常驻 PID 为正常 |
| 外网 / DNS | ☐ gov.cn 可达 | |
| Ragflow / 外挂卷 | ☐ 已挂载 ☐ 不适用 | 见 §6 |

---

## 一、一键命令（推荐）

```bash
cd /Users/apple/Ahope/newhigh   # 勿用占位符 /path/to/newhigh
chmod +x scripts/*.sh
bash scripts/heartbeat_check.sh          # 只检查
bash scripts/heartbeat_recover.sh        # 补采 + kickstart 用户域 Agent
```

**政策采集入口（唯一）**：`scripts/run_policy_news_collect.sh`（内部 `.venv` + `PYTHONPATH` + `.env`）。  
**带 DNS 重试（定时任务推荐）**：`scripts/run_policy_news_collect_retry.sh`（默认最多 3 次、间隔 120s，可用环境变量 `POLICY_COLLECT_DNS_RETRIES`、`POLICY_COLLECT_RETRY_SLEEP_SEC` 调整）。

---

## 二、每日检查项（约 2 分钟）

| 序号 | 项 | 通过条件 | 失败时 |
|------|----|----------|--------|
| 1 | 外网 / DNS | `curl -sf --max-time 15 https://www.gov.cn` | 查 DNS、代理、路由器 |
| 2 | 政策当日写入 | DuckDB `news_items` 中 `symbol='__POLICY__'` 且 `ts` 日期为**今天**有新增；**或** 确认为去重导致 0 条 | §4 |
| 3 | news-api（可选） | `curl -sf http://127.0.0.1:8001/news/stats` | kickstart 或前台起 API |
| 4 | Gateway（可选） | `curl -sf http://127.0.0.1:8000/health` | `bash scripts/restart_gateway_frontend.sh` |
| 5 | launchd | 使用 **用户域** `gui/$(id -u)/...`，且 plist 指向 **本机绝对路径** + **.venv** | §5 |

---

## 三、launchd：**gui** 与 **system**（常见错误）

- **推荐**：plist 放在 **`~/Library/LaunchAgents/`**，用：
  - `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.newhigh.xxx.plist`
  - 重载：`launchctl kickstart -k "gui/$(id -u)/com.newhigh.news-api"`
- **避免**：把用户仓库路径写进 **`system`** 域（`sudo launchctl bootstrap system ...`）。无登录会话或权限不符时，易出现「已加载但未运行 / exit 1」。
- 若文档里出现 `system/com.newhigh.*`，请改为你本机的 **`gui/$(id -u)/com.newhigh.*`**。

查看最近一次退出信息：

```bash
launchctl print "gui/$(id -u)/com.newhigh.policy-collector" 2>/dev/null | head -50
launchctl print "gui/$(id -u)/com.newhigh.news-api" 2>/dev/null | head -50
```

**示例 plist（复制后 sed 替换路径）**：

| 服务 | 文件 |
|------|------|
| 政策 API 常驻 | `integrations/hongshan/policy-news/com.newhigh.news-api.plist.example`（**`.venv/bin/python`**） |
| 每日 08:30 采集 | `integrations/hongshan/policy-news/com.newhigh.policy-collector.plist.example`（调用 **`run_policy_news_collect_retry.sh`**） |

---

## 四、政策采集失败（DNS / 写入 0 / exit 1）

1. **DNS 瞬断**：08:30 窗口内解析失败 → 整次失败；恢复后执行 `bash scripts/heartbeat_recover.sh` 或只跑采集脚本。
2. **系统 Python 无依赖**：禁止定时任务直接 `/usr/bin/python3 ...news_collector.py`，必须用 **`run_policy_news_collect.sh`**。
3. **写入 0 条**：常为**去重**（标题/URL 已存在），不一定是故障；对照日志与源站。

---

## 五、Ragflow / 外部挂载（可选）

本仓库不内置 Ragflow。若本机有 Docker / NFS：

```bash
# 示例：有 compose 时
docker compose -f infra/docker-compose.yml ps 2>/dev/null || true
mount | head -20
```

将你们实际 compose 路径记在团队 MEMORY 中；每日心跳只需确认「依赖的外部卷/容器」未挂。

---

## 六、网络变更时

- 记录出口 IP/MAC（若与 ACL 绑定）。
- 复查：`.env`、`config.yaml`、Cloudflare Tunnel 目标是否仍指向本机。

---

## 七、飞书 / 通知链接

公网 URL 规范见 `.cursor/rules/feishu-links.mdc`（如 `https://htma.newhigh.com.cn/...`），勿发 `localhost`。

---

## 八、变更记录

| 日期 | 说明 |
|------|------|
| 2026-04-03 | 初版：venv、用户域 kickstart、政策路径 |
| 2026-04-03 | 重写：状态看板、`heartbeat_recover.sh`、DNS 重试采集、`gui`/`system` 说明、plist 走 retry 脚本 |
