# 手机 / 其他设备 / Cloudflare（解决 Failed to fetch）

## Cloudflare 外网（HTTPS）

页面能打开但 **Failed to fetch**：多半是浏览器仍在请求 **`http://127.0.0.1:8000`** 或 **http 内网 IP**，在 HTTPS 下会被拦截。

**正确做法**（已写进前端逻辑）：

1. **Tunnel 指向 Next**（如 `http://127.0.0.1:3000`），不要只托管纯静态 HTML。  
2. 本机同时跑 **Gateway :8000** + **Next :3000**。  
3. 前端默认请求 **同源 `/api/...`**，由 Next `rewrites` 转到本机 Gateway。  
4. 在 **设置** 里若曾填写过 `http://...` 或 `127.0.0.1`，请 **清除**，否则会覆盖默认行为。

详见 **`docs/NEWHIGH_COM_CLOUDFLARE.md`**。

---

## 手机直连局域网 IP

浏览器里的 API 若仍指向 **`http://127.0.0.1:8000`**，在手机上 `127.0.0.1` 是**手机自己**，不是你的电脑。

## 步骤

### 1. Gateway 监听局域网

在跑项目的电脑上：

```bash
cd /path/to/newhigh
source .venv/bin/activate
uvicorn gateway.app:app --host 0.0.0.0 --port 8000
```

勿只用 `--host 127.0.0.1`，否则外网设备连不上。

### 2. 前端监听局域网

```bash
cd frontend
npx next dev -H 0.0.0.0 -p 3000
```

手机浏览器打开：`http://你的电脑局域网IP:3000`  
（Mac 可查：`ipconfig getifaddr en0` 或 系统设置 → 网络）

### 3. 在网页「设置」里填 Gateway

打开 **设置**，在 **Gateway 地址** 填：

```text
http://你的电脑局域网IP:8000
```

保存后会刷新；之后所有 API 会打到你的电脑。

### 4. 防火墙

若仍不通，在电脑上允许 **8000**、**3000** 端口的入站连接（macOS：系统设置 → 网络 → 防火墙）。

## 一键脚本（可选）

```bash
bash scripts/dev_lan.sh
```

会打印本机 IP 与推荐命令。

## 与统一调度

`python -m system_core.system_runner` 与 Gateway **无关**；系统监控页报错是因为 **API 连不上**。按上文配置好 Gateway 地址后，监控页即可拉取状态（仍需本机已跑 Gateway）。
