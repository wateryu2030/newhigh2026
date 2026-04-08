# 主题标的 · 妙想批量核查（自动生成）

> 输出由脚本根据用户粘贴内容抽取标的并调用妙想 API 生成，**不构成投资建议**。

## 1. 用户输入摘录

> pbpaste | python scripts/theme_stock_mx_batch.py -o report.md

## 2. 智能解析结果（用于后续查数）

- **主题摘要**：未从粘贴内容中解析出明确主题句，请检查是否包含 A 股代码或打开 LLM 抽取。
- **关注点关键词**：（无）
- **抽取说明**：大模型未参与或失败（dashscope_http_401:{"error":{"message":"Incorrect API key provided. For details, see: https://help.aliyun.com/zh/model-studio/error-code#apikey-error","type":"invalid_request_error","param":null,"code":"invalid_api_key"},"request_id":"9a13b9eb-7a92-9e70-8067-4be41c05cb00"}），标的以正则/模型可用部分合并。

### 识别标的清单

| 代码 | 名称 | 市场 | 依据摘录 |
|------|------|------|----------|

## 3. 妙想数据快照

（本节未填充：常见原因包括未设置 `MX_APIKEY`、使用了 `--mx-skip`、或未识别到标的。配置密钥并去掉 `--mx-skip` 后重跑即可。）

---

## 4. 使用建议

- 将 **关注点关键词** 用于前端投研 `POST /api/research/news-summary` 的 `focus` 字段，或站内 `GET /api/news?symbol=` 人工扩展阅读。
- **重大合同、海外大单** 以交易所 **临时公告** 与 **定期报告分部附注** 为准；妙想表格多为财务指标与分部，不等于订单认证。
- 再次运行：`python scripts/theme_stock_mx_batch.py -i your.txt -o report.md`