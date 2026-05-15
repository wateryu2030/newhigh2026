# 鸿山咨询 · 微信外网与主站（htma.newhigh.com.cn）对接说明

本文说明在微信公众平台 **须手工配置** 的入口、菜单路径与填写值。公网基准域名与飞书/通知规范一致：**`https://htma.newhigh.com.cn`**（Next 反代 Gateway，浏览器与小程序统一请求该域名的 `/api/*`）。

**安全**：AppSecret 仅在 [微信公众平台](https://mp.weixin.qq.com/) 查看，写入服务器环境变量或密钥管理，**禁止提交 Git**。

---

## 1. 官方入口（请收藏）

| 用途 | 链接 |
|------|------|
| **微信公众平台**（小程序 / 公众号后台，同一登录页） | https://mp.weixin.qq.com/ |
| **微信开放平台**（UnionID、移动应用、网站应用绑定，可选） | https://open.weixin.qq.com/ |
| **微信开发者工具下载**（小程序调试） | https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html |
| **小程序开发文档（合法域名等）** | https://developers.weixin.qq.com/miniprogram/dev/framework/ |

使用 **管理员微信** 扫码登录后，在首页顶部切换要管理的账号（鸿山咨询对应小程序或公众号）。

---

## 2. 微信小程序「鸿山咨询」（本仓库 `integrations/hongshan/wechat-miniprogram`）

### 2.1 AppID（公开标识）

- 当前工程内 `project.config.json` 的 `appid` 与后台一致即可。
- **鸿山咨询小程序 AppID**：`wx3af1eaaa70ed49e6`（与微信后台「开发设置」中的开发者 ID 一致）。

### 2.2 在公众平台手工配置（菜单路径）

登录 **https://mp.weixin.qq.com/** → 选择 **小程序** → 左侧：

1. **开发 → 开发管理 → 开发设置**
   - **开发者 ID**：核对 AppID。
   - **AppSecret**：点击「生成」或「重置」后复制，仅用于服务器：环境变量 **`WECHAT_MINIPROGRAM_SECRET`**（勿入库）。
   - **服务器域名**（同一页面向下滚动，进入「服务器域名」配置区/弹窗）——按界面逐项填写：

#### 服务器域名配置方法（与后台表单一致）

1. 登录 [微信公众平台](https://mp.weixin.qq.com/) → 选择 **小程序**（鸿山咨询）。
2. 左侧菜单：**开发** → **开发管理** → **开发设置** → 找到 **服务器域名** → 点击 **修改**（若首次配置会进入编辑状态）。
3. **request 合法域名**（`wx.request` 等 HTTPS 请求）：
   - 填写：**`https://htma.newhigh.com.cn`**
   - 当前小程序后台输入框通常要求 **带 `https://` 的完整 URL**（与您截图一致）；若你方界面仅允许裸域名，则改为只填 **`htma.newhigh.com.cn`**，以页面提示为准。
   - **多个域名**时，用英文分号 **`;`** 分隔，例如：`https://a.example.com;https://b.example.com`（末尾分号可省略）。
4. 其余类型按需填写（本栈若仅用 REST API，可暂留空）：
   - **socket 合法域名**：WebSocket，须 **`wss://`** 开头。
   - **uploadFile / downloadFile 合法域名**：须 **`https://`** 开头。
   - **udp / tcp 合法域名**：按业务与文档格式填写。
   - **DNS 预解析域名 / 预连接域名**：按后台说明填写，可提升首包速度，非必选。
5. 点击 **「保存并提交」**；微信会校验域名备案与 HTTPS 等要求，通过后生效（每月有修改次数限制，请谨慎操作）。

   - **业务域名**（若页面内嵌 **web-view**）：在「业务域名」中按指引下载校验文件并放到 **`https://htma.newhigh.com.cn/`** 可访问路径（与运维约定）。

2. **开发 → 开发管理 → 接口设置**（按需）  
   若使用用户信息、手机号等能力，按类目与隐私协议要求打开对应接口。

### 2.3 小程序代码侧（已对齐公网）

- `integrations/hongshan/wechat-miniprogram/config.js`：`apiBase: 'https://htma.newhigh.com.cn'`
- 真机/体验版/正式版：**必须**在后台配置好 request 合法域名；仅靠「开发者工具里勾选不校验合法域名」仅适用于本机调试。

### 2.4 与 Gateway 的接口

- 登录：`POST /api/auth/wechat/miniprogram`，body：`{"code":"<wx.login 返回的 code>"}`
- 完整 URL：`https://htma.newhigh.com.cn/api/auth/wechat/miniprogram`

---

## 3. 微信公众号网页授权（仅当使用 Web「微信登录」H5）

若 **仅使用小程序**，可跳过本节；若 Next 前端使用 **`GET /api/auth/wechat/url`** 做公众号 OAuth，需配置：

1. **微信公众平台** → 选择 **公众号**（非小程序）→  
   **设置与开发 → 公众号设置 → 功能设置**：
   - **网页授权域名**：填写 **`htma.newhigh.com.cn`**（不带 `https://`，按页面说明下载校验文件并放到站点根目录，与运维确认）。
   - 若使用 JSSDK：**JS 接口安全域名** 同样填 **`htma.newhigh.com.cn`**。

2. 服务器环境变量示例（密钥只在后台查看）：
   - `WECHAT_MP_APPID` = 公众号 AppID  
   - `WECHAT_MP_SECRET` = 公众号 AppSecret  
   - **`WECHAT_OAUTH_REDIRECT_URI=https://htma.newhigh.com.cn/api/auth/wechat/callback`**

授权回调须与上述 **redirect_uri** 完全一致（协议、域名、路径）。

---

## 4. 与主站共用的环境变量（`.env` / 部署环境）

详见仓库根目录 **`.env.example`**。与公网域名相关的推荐值：

```bash
FRONTEND_BASE_URL=https://htma.newhigh.com.cn
OAUTH_LOGIN_REDIRECT_BASE=https://htma.newhigh.com.cn

# 鸿山咨询小程序（示例 AppID；Secret 仅在 mp 后台配置）
WECHAT_MINIPROGRAM_APPID=wx3af1eaaa70ed49e6
# WECHAT_MINIPROGRAM_SECRET=在公众平台生成，勿提交仓库
```

---

## 5. 联调自检

| 检查项 | 方法 |
|--------|------|
| 域名 HTTPS | 浏览器打开 `https://htma.newhigh.com.cn/` |
| Gateway | `GET https://htma.newhigh.com.cn/api/health` |
| 小程序登录 | 真机调用 `wx.login` 后 POST 上述 `/api/auth/wechat/miniprogram`，确认返回 JWT |
| 公众号 OAuth（若启用） | `GET https://htma.newhigh.com.cn/api/auth/wechat/url` 返回 `authorize_url` 且能完成回调 |

---

## 6. 免责声明

微信侧类目、隐私、审核规则以 **微信官方** 为准；本文档仅描述与本项目 Gateway / 域名 **对接方式**，不构成对微信政策的承诺。
