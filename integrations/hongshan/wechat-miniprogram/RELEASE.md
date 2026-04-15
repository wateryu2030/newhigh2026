# 红山量化微信小程序 — 迭代发布说明

## 开放浏览（小程序正式上架前）

- `config.js` 中 **`publicBrowseMode: true`**（默认）：首页、行情、资讯、策略展示页对**未登录用户**同样拉取公开接口；**股票问答**可进入页面，提交分析需登录（上架后再全面开放）。
- 上架并需区分注册/非注册用户时：将 **`publicBrowseMode` 改为 `false`**，并按产品策略恢复各页登录校验；Gateway 侧可收紧 `gateway/auth/auth_middleware.py` 中的 **`_PUBLIC_GET_*`** 白名单。

## 功能摘要（与 Gateway 对齐）

- **登录**：`wx.login` → `POST /api/auth/wechat/miniprogram`；JWT 存 `newhigh_jwt_token`（兼容 `token`）；`user_level` 写入 `globalData` / `user_level` 存储。
- **请求**：`utils/request.js` 自动 `Authorization: Bearer`，`401` 清票并 `reLaunch` 至 `pages/login/login`。
- **我的**：`GET /api/user/profile`、`GET /api/user/quota`；展示角色、级别、配额；trial 显示「升级权益」；入口：行情 / 问答 / 信号。
- **首页**：登录后快捷入口（行情、问答、信号）。
- **资讯**：`GET /api/news` 分页（递增 `limit`）、骨架屏、下拉刷新、触底加载、详情页（复制原文链接）。
- **行情**：`GET /api/stocks/quotes`、`/api/stocks/search`；自选存本地 `watchlist_codes`；详情 `GET /api/market/klines`。
- **股票问答**：`POST /api/stock-qa/analyze`（关闭 LLM 走势以控时）；配额来自 `/api/user/quota`。
- **策略信号**：`GET /api/strategy/signals`。
- **合规**：`pages/about/about` 免责声明；登录页风险提示。

## 配置与发布前检查

1. **合法域名**：微信公众平台 → 开发 → 服务器域名 → `request`：`https://htma.newhigh.com.cn`（与 `config.js` 一致）。
2. **后端**：配置 `WECHAT_MINIPROGRAM_APPID` / `WECHAT_MINIPROGRAM_SECRET`；生产可设 `JWT_AUTH_REQUIRED=1`。
3. **AppID**：见 `project.config.json`（勿将 Secret 提交仓库）。
4. **隐私政策**：按微信要求上传《隐私保护指引》全文链接（可托管于已备案 H5）。

## 测试

- 后端：仓库根目录 `python3 -m pytest gateway/tests/`（含 `test_wechat_miniprogram.py`、`test_quota_limits.py`）。
- 小程序：微信开发者工具打开本目录，真机预览前确认域名与 HTTPS。

## 待办 / 可选增强

- 自选同步服务端 `watchlist`（若 Gateway 增加专用接口）。
- K 线图表（`ec-canvas`）与问答长文 Markdown 渲染。
- 用户级别与支付/运营后台打通。
