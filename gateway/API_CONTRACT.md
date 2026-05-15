# Gateway API 契约摘要

> 完整 OpenAPI：`/docs`、`/openapi.json`。以下为「公开只读」与「需 JWT」的约定，供 H5/小程序对齐。

## 环境

- `JWT_AUTH_REQUIRED=1` 时，除白名单外所有 `/api/*` 需 `Authorization: Bearer <token>`。
- 白名单见 `gateway/src/gateway/auth/auth_middleware.py` 中 `_SKIP_PATHS`。

## 公开只读（典型）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health`、`/api/health` | 健康检查 |
| GET | `/api/health/detailed` | 详细健康（与 `/api/system/health-detail` 等价） |
| GET | `/api/market/sentiment-7d`、`/api/market/klines`、`/api/market/ashare/stocks`、`/api/market/emotion` | 行情只读 |
| GET | `/api/dashboard`、`/api/system/data-overview`、`/api/system/status`、`/api/system/health-detail` | 控制台只读 |
| GET | `/api/news`、`/api/news/*`（部分） | 新闻快讯 |
| GET | `/api/stocks`、`/api/market/sniper-candidates` | 股票池/狙击候选 |
| GET | `/api/data/status` | 数据状态 |
| GET | `/api/user/quota` | 今日配额（无 JWT 时按客户端 IP 计数） |
| POST | `/api/auth/login`、`/api/auth/register` | 登录注册 |
| GET/POST | `/api/auth/wechat/url`、`/api/auth/wechat/callback`、`/api/auth/wechat/miniprogram` | 微信相关（需配置） |

## 需 JWT（启用时）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/user/profile` | 当前用户资料 |
| POST | `/api/user/change-password` | 修改密码 |
| POST | `/api/stock-qa/analyze` | 股票问答（含日配额，超限 429） |
| POST | `/api/backtest/run` | 单策略回测（含日配额） |
| POST | `/api/pipeline/*`（部分） | 管道写操作 |

## 配额（默认，可环境变量覆盖）

- `FREE_STOCK_QA_PER_DAY`（默认 20）：`/api/stock-qa/analyze` 每用户/每 IP 每日次数。
- `FREE_BACKTEST_PER_DAY`（默认 10）：`/api/backtest/run` 每用户/每 IP 每日次数。

## 响应信封（多数 JSON 接口）

成功：`{ "ok": true, "data": ..., "source": "..." }`  
失败：`{ "ok": false, "error": "...", "source": "..." }` 或 HTTP 4xx/5xx。
