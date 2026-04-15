# 微信小程序跑通检查清单（鸿山咨询）

## 1. 仓库根目录 `.env`（本机 Gateway）

以下键须存在，且 **勿提交 Git**（已在 `.gitignore`）：

```bash
WECHAT_MINIPROGRAM_APPID=wx3af1eaaa70ed49e6
WECHAT_MINIPROGRAM_SECRET=<微信公众平台「开发设置」中的 AppSecret>
```

修改后 **必须重启 Gateway**，否则仍为 `501 未配置`。

```bash
# 本机一键重启（仓库根目录）
bash scripts/restart_gateway_frontend.sh
```

自测（无效 code 应返回微信侧错误，而非 501）：

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/auth/wechat/miniprogram" \
  -H "Content-Type: application/json" \
  -d '{"code":"bad1"}'
# 期望: ok:false, error 含 invalid code（说明密钥已生效）
```

## 2. 公网 `htma.newhigh.com.cn`（线上）

浏览器/小程序请求的是 **Next 反代后的 `/api/*`**，与 **运行 Gateway 的进程** 必须加载 **同一套** `WECHAT_MINIPROGRAM_*`。

若 `POST https://htma.newhigh.com.cn/api/auth/wechat/miniprogram` 仍返回 **501**：

1. 登录部署机，在 **实际启动 uvicorn 的环境**（systemd `EnvironmentFile`、Docker `env_file`、PM2 `env` 等）写入上述变量。
2. 重启 Gateway 服务。
3. 勿把 Secret 写进前端或小程序代码。

## 3. 微信公众平台

- **request 合法域名**：`https://htma.newhigh.com.cn`（与 `config.js` 的 `apiBase` 一致）。
- 详见仓库根目录 **`docs/WECHAT_HONGSHAN_EXTERNAL.md`**。

## 4. 微信开发者工具

1. 导入目录：`integrations/hongshan/wechat-miniprogram`。
2. `project.config.json` 中 `appid` 与公众平台一致。
3. 真机调试前须上传体验版或已配置合法域名；仅开发者本机可临时勾选「不校验合法域名」。

## 5. DuckDB 被占用（登录返回 503）

若接口提示「数据库不可用」或 health 为 degraded，请避免 **多进程同时写** 同一 `quant_system.duckdb`；单机只保留一个 Gateway 写库实例，或按运维拆分库路径环境变量。
