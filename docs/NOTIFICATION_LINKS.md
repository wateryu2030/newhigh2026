# 推送/通知中的前端链接规范

## 通过飞书 newhigh 控制本机开发

当你**通过飞书 newhigh** 触发本机修改、并收到「修改完成」等回复时，回复中的**任何可点击链接**都必须使用公网 URL（`https://htma.newhigh.com.cn/...`），**不能**使用 `localhost` 或 `127.0.0.1`。否则在手机或其它设备上点击会打不开。项目已通过 Cursor 规则（`.cursor/rules/feishu-links.mdc`）约束 AI 生成的链接格式，确保从飞书发起的开发流程里给出的链接均可点击。

## 问题

在飞书、企业微信、Server 酱等渠道发送的通知里，若包含「前端新闻页」或「查看新闻」的链接，**必须使用带协议的完整 URL**。否则用户点击时，客户端可能把 `htma.newhigh.com.cn/news` 当作相对路径或搜索关键词，导致无法打开。

## 正确写法

| 用途       | 推荐链接 |
|------------|----------|
| 前端新闻页 | `https://htma.newhigh.com.cn/news` |
| 投研页     | `https://htma.newhigh.com.cn/research` |
| 策略市场   | `https://htma.newhigh.com.cn/strategies` |
| 首页       | `https://htma.newhigh.com.cn` |
| API 说明   | 同源下可写相对路径 `/api/news` 或完整 `https://htma.newhigh.com.cn/api/news` |

通知文案示例：

```
采集结果可通过以下方式查看：
前端：https://htma.newhigh.com.cn/news
API：/api/news 或 /api/system/data-overview
```

## 错误写法（会导致点击异常）

- `htma.newhigh.com.cn/news`（缺少 `https://`）
- `http://htma.newhigh.com.cn/news`（若站点已强制 HTTPS，部分环境会跳转或报错，建议统一用 https）

## 配置方式（可选）

若发送逻辑在项目内（如 `personal_assistant`、自定义脚本或 OpenClaw 流程），建议：

1. 在 `.env` 中增加：`FRONTEND_NEWS_URL=https://htma.newhigh.com.cn/news`
2. 在代码中读取：`os.getenv("FRONTEND_NEWS_URL", "https://htma.newhigh.com.cn/news")`
3. 拼接文案时使用该变量，避免硬编码域名。

这样以后若域名或子域变更，只需改一处配置。
