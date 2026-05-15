# 微信小程序（Taro + React 占位）

本目录为 **MVP 框架占位**：推荐在本机执行官方脚手架生成完整工程后，将页面迁入。

## 1. 初始化 Taro（示例）

```bash
cd wechat-miniprogram
npx @tarojs/cli init .
# 选择 React + TypeScript；模板选默认即可
```

## 2. 合法域名

在微信公众平台配置 **request 合法域名** 为你的 Gateway HTTPS 根域（如 `https://api.example.com`），**不可**使用 IP 或未备案域名。

## 3. 登录流程

1. 小程序 `wx.login` 取 `code`。
2. `POST /api/auth/wechat/miniprogram`，body：`{ "code": "<code>" }`。
3. 响应中带 `token`，后续请求头：`Authorization: Bearer <token>`。

需环境变量：`WECHAT_MINIPROGRAM_APPID`、`WECHAT_MINIPROGRAM_SECRET`（见 Gateway）。

## 4. 共享请求封装

复用仓库根目录 **`packages/api-client`** 中的 `createApiClient`，在 Taro 侧传入 `Taro.request` 适配器（见该包 `src/index.ts` 注释）。

## 5. 导入微信开发者工具

「导入项目」→ 选择本目录下由 Taro 生成的 `dist`（或 CLI 提示的目录）→ 填写测试号 AppID。
