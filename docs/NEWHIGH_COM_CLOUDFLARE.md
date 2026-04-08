# newhigh.com.cn + Cloudflare + 本地运行 — 配置安排

在 **域名 newhigh.com.cn** 上展示本项目，通过 **Cloudflare** 对外发布，**源站跑在你本机**。推荐用 **Cloudflare Tunnel（cloudflared）**，无需家庭宽带开端口、自动 HTTPS。

---

## 1. 架构示意

```
访客 → Cloudflare 边缘 (CDN/WAF/HTTPS) → cloudflared（本机常驻）
                                              ↓
                                    本机 HTTP 服务（见下文选一种）
```

- **不要**把路由器 80/443 直接映射到家里（安全风险大）。
- Tunnel 从本机**主动出站**连 Cloudflare，只转发到你指定的 `127.0.0.1:端口`。

---

## 2. Cloudflare 侧（一次性）

1. **把域名接入 Cloudflare**  
   - 在 Cloudflare 添加站点 `newhigh.com.cn`，按提示把域名 NS 改到 Cloudflare。

2. **创建 Tunnel（推荐）**  
   - 控制台：**Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel**。  
   - 命名例如 `newhigh-local`。  
   - 按页面提示在本机安装 `cloudflared` 并执行登录、绑定隧道（会得到一串 token）。

3. **公网主机名（重要）**  
   - **必须**把 Tunnel 指到 **Next.js**（`next dev` 或 `next start` 的端口，如 **3000** 或 **4173**），**不要**只指纯静态 HTML 目录。  
   - 前端会通过 **同源 `/api`** 访问数据，由 Next **rewrites** 转发到本机 `127.0.0.1:8000` 的 Gateway；外网浏览器**绝不能**直接请求 `http://127.0.0.1:8000`（会 Failed to fetch）。  
   - 配置示例：**URL** → `http://127.0.0.1:3000`（与本地 Next 端口一致）。  
   - 本机须**同时运行**：Gateway `:8000` + Next `:3000`（Tunnel 只暴露 Next 即可）。

4. **DNS**  
   - 使用 Tunnel 时，Cloudflare 通常会为 `newhigh.com.cn` 自动写 **CNAME** 指向 `xxxx.cfargotunnel.com`，保持 **代理状态（橙色云）** 即可。

5. **SSL/TLS**  
   - 一般 **Full** 即可（源站是 HTTP localhost，由 Tunnel 加密到边缘）。

6. **可选加固**  
   - **WAF** 规则、**Rate limiting**、**Access**（仅允许指定邮箱/OTP 访问后台路径）。

---

## 3. 本机跑什么（三选一或组合）

| 方案 | 适用 | 本机命令 / 说明 |
|------|------|-----------------|
| **A. 仅项目介绍（静态）** | 对外只展示文案、架构、开源说明 | `python3 -m http.server 8090 --directory site`（需自建 `site/` 目录放 `index.html`） |
| **B. 前端构建预览** | 展示现有 React 控制台界面 | `cd frontend && npm ci && npm run build && npm run preview -- --host 127.0.0.1 --port 4173` |
| **C. API + 前端** | 需要在线演示接口（**风险高**） | 本机 Nginx 反代：`/` → 4173，`/api` → 8000；**务必**开启 JWT、勿暴露密钥 |

**建议**：公网仅开放 **A 或 B**；量化 API、数据库、密钥仅内网使用。

---

## 4. cloudflared 安装与运行（macOS 示例）

```bash
brew install cloudflared
# 按 Zero Trust 隧道页面复制「安装命令」，通常类似：
# cloudflared service install <TOKEN>
```

或使用配置文件（见仓库 `config/cloudflare/config.example.yml`），本机复制为 `config.yml` 后：

```bash
cloudflared tunnel --config /path/to/config.yml run
```

**长期运行**：可用 `launchctl` 加载 plist（见下节示例），保证开机或登录后隧道自动拉起。

---

## 5. 与仓库对齐的端口建议

| 服务 | 默认端口 | 说明 |
|------|----------|------|
| Gateway（FastAPI） | 8000 | `uvicorn gateway.app:app --host 127.0.0.1 --port 8000` |
| 前端 dev | 3000 | 开发用，不建议直接对公网 |
| 前端 preview（构建后） | 4173 | **推荐**作为 Tunnel 后端 |
| 静态展示 | 8090 | 自建 `site/index.html` |

Tunnel 的 **Public Hostname** 填：`http://127.0.0.1:4173` 或 `http://127.0.0.1:8090`。

---

## 6. LaunchAgent 示例（本机常驻 Tunnel）

将 `TUNNEL_TOKEN` 换成你在 Cloudflare 隧道页拿到的 token；若用 **config 文件 + 命名隧道**，可改用 `cloudflared tunnel run <隧道名>`。

路径：`~/Library/LaunchAgents/com.newhigh.cloudflared.plist`（示例）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.newhigh.cloudflared</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/cloudflared</string>
    <string>tunnel</string>
    <string>run</string>
    <string>--token</string>
    <string>YOUR_TUNNEL_TOKEN_HERE</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/cloudflared-newhigh.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/cloudflared-newhigh.err</string>
</dict>
</plist>
```

加载：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.newhigh.cloudflared.plist
```

### 浏览器控制台：`/_next/static/...` 404（main-app.js、layout.css、error.js 等）

含义：页面 HTML 里引用的前端资源在**当前域名**下拿不到。常见原因：

1. **Tunnel 指错端口**：必须指向 **Next（3000）**，不能指向 **Gateway（8000）**；8000 没有 `/_next/static`。  
2. **`output: 'standalone'` 与启动方式不一致**：应用 `cd frontend && npm run start:standalone`（或 `NEWHIGH_FRONTEND_PROD=1` 的 `restart_gateway_frontend.sh`），确保 `.next/static` 已复制进 `.next/standalone/.next/static`。本仓库 **`scripts/run_tunnel_stack.sh` 已改为 `start:standalone`**。  
3. **Cloudflare 缓存了旧 HTML**：边缘仍返回上一版 HTML，但 chunk 名已变 → 404。对 `htma.newhigh.com.cn` 做一次 **Purge Everything**（或至少清理 HTML），并避免对站根套「Cache Everything」长缓存。  
4. **扩展注入**：控制台里 `content.js`、`tongyi` 等与本项目无关，可忽略。

本机快速自检（Next 已监听 3000 时）：`bash scripts/verify_next_static_local.sh`

---

## 7. 合规与备案提示

- **.cn 域名**在中国大陆访问常涉及 **ICP 备案**；Cloudflare 不能替代备案。若主要访客在境内，请自行咨询接入商/法务。
- 对外页面避免展示 **API Key、内网地址、客户数据**。

---

## 8. 开机自启（Tunnel → `http://127.0.0.1:3000`）

本机登录后自动拉起 **Gateway :8000** + **Next :3000**（与 Tunnel 一致）：

```bash
cd /path/to/newhigh
bash scripts/install_tunnel_stack_launchagent.sh
```

- 使用 **LaunchAgent**：`com.newhigh.tunnel-stack`  
- 首次会执行 `npm run build`；日志：`logs/gateway_boot.log`、`logs/next_boot.log`、`logs/tunnel_stack.log`  
- **卸载**：`launchctl bootout gui/$(id -u)/com.newhigh.tunnel-stack`，并删除 `~/Library/LaunchAgents/com.newhigh.tunnel-stack.plist`  
- **cloudflared** 仍需单独配置开机启动（见第 6 节 plist 示例）；Tunnel 与 Next 栈相互独立。

若项目路径不是 `/Users/apple/Ahope/newhigh`，**必须**运行上述安装脚本（会用 `sed` 写入实际路径）。

---

## 9. 检查清单

- [ ] 域名 NS 已在 Cloudflare  
- [ ] Tunnel 创建并完成 `cloudflared` 连接  
- [ ] Public Hostname → **`http://127.0.0.1:3000`**（Next），本机同时跑 Gateway :8000  
- [ ] （可选）已安装 `com.newhigh.tunnel-stack` 开机自启  
- [ ] 浏览器访问 `https://你的域名` 可打开且接口正常（同源 `/api`）  
- [ ] 未将 `.env`、数据库端口暴露到公网  
- [ ] **子域控制台**：若使用 `https://htma.newhigh.com.cn`，在 Tunnel 的 **Public Hostname**（或 `config.yml` 的 `ingress`）里**单独增加一条** `htma.newhigh.com.cn` → `http://127.0.0.1:3000`；仅配置 `newhigh.com.cn` 时，子域不会自动继承，常表现为 **404** 或 Cloudflare 默认错误页。  
- [ ] **DNS**：`htma` 子域为 **CNAME** 指向隧道（与主域一致），并保持**橙色云**代理。  

### 子域 `htma.newhigh.com.cn` 英文「This page could not be found」

1. **Tunnel 路由**：在 Zero Trust → 隧道 → **Public Hostname** 中确认存在 **`htma.newhigh.com.cn`**，服务 URL 与当前本机 Next 一致（开发多为 **`http://127.0.0.1:3000`**，构建预览可为 **4173**）。  
2. **本地监听**：前端已使用 `next dev -H 0.0.0.0 -p 3000`（见 `frontend/package.json`），避免仅绑定 localhost 时部分环境下访问异常。  
3. **YAML ingress**：若用 `config/cloudflare/config.yml`，须为 `htma.newhigh.com.cn` 增加 `hostname` 规则；否则请求会落到示例文件末尾的 `http_status:404`（见 `config.example.yml` 注释）。  
4. **与 inpa 域名区分**：对外控制台应为 **`htma.newhigh.com.cn`**；`htma.inpa.com.cn` 为另一主机名，需在 **该域名** 的 DNS/Tunnel 中同样单独配置，否则会指向错误源站或 502/404。  
5. 仍异常时：本机执行 `curl -sI -H 'Host: htma.newhigh.com.cn' http://127.0.0.1:3000/`，应返回 **200**；若为 200 而公网仍 404，问题在 **Tunnel/DNS**；若本机也非 200，先 **`bash scripts/restart_gateway_frontend.sh`** 再起 Tunnel。  

---

## 10. 仓库内文件

| 文件 | 说明 |
|------|------|
| `config/com.newhigh.tunnel-stack.plist` | LaunchAgent：开机跑 Gateway + Next |
| `scripts/run_tunnel_stack.sh` | 上述 plist 调用的主脚本 |
| `scripts/install_tunnel_stack_launchagent.sh` | 一键安装到 `~/Library/LaunchAgents/` |
| `config/cloudflare/config.example.yml` | 命名隧道 + 多域名示例（需先 `cloudflared tunnel create`） |
| `docs/NEWHIGH_COM_CLOUDFLARE.md` | 本文 |

如需 **仅静态展示**，可在项目根建 `site/index.html`，内容可从 `README.md`、`OPENCLAW_PLAN.md`、`docs/ARCHITECTURE.md` 摘取，再用 Tunnel 指向 `8090`。

---

## 11. 502 Bad Gateway 排查（Cloudflare 正常、源站异常）

若访问 `https://htma.newhigh.com.cn/news` 等出现 **502 Bad Gateway**，说明 Cloudflare 已连上隧道，但**本机源站未正常响应**（Tunnel 指向的端口无服务或进程崩溃）。

### 常见原因与处理

| 原因 | 处理 |
|------|------|
| **Next 未跑起来** | 本仓库用 `com.newhigh.tunnel-stack` 同时起 Gateway :8000 与 Next :3000。若 `.next` 目录不完整（缺少 `BUILD_ID`），`next start` 会立即退出，3000 无监听 → 502。**处理**：在项目根执行 `cd frontend && npm run build`，再 `launchctl stop com.newhigh.tunnel-stack && launchctl start com.newhigh.tunnel-stack`。 |
| **tunnel stack 崩溃循环** | 查看 `logs/tunnel_stack.log`、`logs/next_boot.log`。若反复出现 “one process died” 或 “Could not find a production build”，按上一条先完整构建再重启。 |
| **cloudflared 未跑或未指对端口** | Tunnel 的 Public Hostname 必须指到本机 **http://127.0.0.1:3000**（与 Next 端口一致）。确认 cloudflared 进程在跑、且配置里端口为 3000。 |
| **本机休眠/断网** | 唤醒或恢复网络后，LaunchAgent 会重拉 tunnel stack；若 cloudflared 未自启，需手动启动一次。 |

**一键重启源站（Gateway + Next）**：

```bash
launchctl stop com.newhigh.tunnel-stack
sleep 3
launchctl start com.newhigh.tunnel-stack
# 约 10 秒后检查
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/
# 应输出 200
```

---

## 12. 推送/通知中的前端链接

飞书、微信等推送里若包含「前端新闻页」链接，**必须使用带协议的完整 URL**，否则点击可能无法打开：

- **正确**：`https://htma.newhigh.com.cn/news`
- **错误**：`htma.newhigh.com.cn/news`（缺少 `https://`，部分客户端不会自动补全）

若你有定时任务或 OpenClaw 流程在发送「午间新闻采集」等通知，请把「前端：」后的链接改为上述完整 URL。可选：在 `.env` 中配置 `FRONTEND_NEWS_URL=https://htma.newhigh.com.cn/news`，发送逻辑中引用该变量。详见 `docs/NOTIFICATION_LINKS.md`。
