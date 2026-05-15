# 移动端与微信生态（迭代记录）

## 已实现（本迭代）

- **触控目标**：`globals.css` 中 `.min-h-touch` / `.min-w-touch`（约 44px）。
- **PWA**：`public/manifest.json` 含 192/512 图标；`public/sw.js` 缓存同源静态；`ServiceWorkerRegister` 仅生产注册。
- **股票问答**：首屏 20 条卡片，「加载更多」每次 +20；加载中 `PageSkeleton`。
- **账户**：`/profile` — 资料、配额、改密（依赖 Gateway `/api/user/*`）。
- **运维页**：`/admin/ops` — 展示 `/api/health/detailed` JSON。

## 微信小程序（鸿山咨询）

- **实现目录**：`integrations/hongshan/wechat-miniprogram/`（原生小程序；公网 API 基址见其中 `config.js`）。
- **登录**：`POST /api/auth/wechat/miniprogram`（需配置 `WECHAT_MINIPROGRAM_APPID` / `WECHAT_MINIPROGRAM_SECRET`）。
- **外网域名与公众平台手工配置**（含 `htma.newhigh.com.cn`、合法域名、OAuth 回调）：见 **`docs/WECHAT_HONGSHAN_EXTERNAL.md`**。
- 根目录 **`wechat-miniprogram/`** 为占位/Taro 指引，与红山对接以 `integrations/hongshan/wechat-miniprogram` 为准。

## 共享 API 客户端

- **`packages/api-client/`**：轻量 `fetchJson` 封装，供 Next 与 Taro 复用（按需 `npm link` 或复制）。
