# 红山量化（微信小程序）

与 newhigh **Gateway** 对接的量化主题小程序：**首页看板**（`/api/dashboard`、`/api/market/emotion`、`/api/strategy/signals`）、**策略订阅展示页**、**资讯列表**（`GET /api/news`）、**我的**（微信登录 `POST /api/auth/wechat/miniprogram`、资料 `GET /api/user/profile`）、关于页。

**一键跑通**：环境变量、重启、自测命令见同目录 **`RUNBOOK.md`**。

**侧栏以外的桌面页**：**`config/extra_web_paths.js`** 在「全部功能」页追加 Web 内嵌入口（投研/研报/交易等），与主菜单 **`config/navigation_manifest.json`** 互补。

**菜单对齐（单源）**：仓库根目录 **`config/navigation_manifest.json`** → Web 由 `frontend/src/config/menu.ts` 直接引用；小程序侧运行 **`make sync-nav`**（或 `python3 scripts/gen_miniprogram_menu.py`）生成 **`config/menu.generated.js`**，**`config/menu.js`** 仅 re-export。改菜单勿只改一端；详见 **`docs/OPENCLAW_ORCHESTRATION.md` §4.5**。Web 内嵌能力见 **`utils/menu-nav.js`** / **`pages/web-page/`**。

## UI 主题

深色终端风：`#0A0F14` 背景、`#FF4444` 品牌红、`#00C087` 涨跌绿、`#E5E2E1` 主文案；底部 **Tab** 四栏（首页 / 策略 / 资讯 / 我的），图标见 `assets/tabbar/`。

## 本地调试

1. 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)。
2. 导入本项目目录 `integrations/hongshan/wechat-miniprogram`（须包含 `app.json`）。
3. **开发阶段**可勾选「不校验合法域名…」（仅本机调试）。
4. `config.js` 中 `apiBase` 须为可 HTTPS 访问的 Gateway（默认 `https://htma.newhigh.com.cn`）。

## 对外发布（概要）

1. **类目与资质**以微信公众平台审核为准。
2. **AppID**：`project.config.json` 中 `appid`（鸿山咨询：`wx3af1eaaa70ed49e6`），须与 [微信公众平台](https://mp.weixin.qq.com/) 一致。
3. **服务器域名**：在公众平台将 **`htma.newhigh.com.cn`** 加入 **request 合法域名**（与 `config.js` 的 `apiBase` 同域）；详见 **`docs/WECHAT_HONGSHAN_EXTERNAL.md`**。
4. **隐私指引**：登录等能力需按平台要求配置。

## 与主仓库关系

- 接口见 `gateway/API_CONTRACT.md`；小程序与 Web 共用 JWT 存储键 `newhigh_jwt_token`。
- 主 Web 前端为 `frontend/`；本目录为**独立小程序**，样式与交互为原生 WXML/WXSS。
