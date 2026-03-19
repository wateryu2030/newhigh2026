# ClawHub「A Stock Monitor 1」整合说明

## 为何不直接安装该 Skill 压缩包

[ClawHub 页面](https://clawhub.ai/nuradil/a-stock-monitor-1) 对该 Skill 做了**安全扫描**，标记为 **Suspicious**，主要包括：

- 含 **GUI 自动化**（`computer_control.py`：截图、键盘、可驱动「自动交易」），与「监控」描述不一致，权限过大。
- **硬编码 Tushare Token、默认 Web 密码** 等敏感信息。
- **依赖声明不完整**（代码使用 pyautogui、pandas 等但未在元数据中列出）。

因此 **不在本仓库内安装其原始代码包**，避免引入上述风险。

## 我们在 newhigh 中已整合的能力

| ClawHub Skill 能力 | newhigh 对应实现 |
|--------------------|------------------|
| 7 维市场情绪 0–100 | `data-pipeline/sentiment_7d.py` + `GET /api/market/sentiment-7d` |
| 全市场现货数据 | 已有 `a_stock_realtime`（`realtime_quotes`）或 akshare 兜底 |
| Web 展示 | 前端 **行情** 页增加「7 维情绪」卡片 |
| 定时更新 | 已有管道/调度；可选 `UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py` |

**未在本阶段搬运的部分**（可后续用自有策略引擎扩展）：

- 短线 5 策略 / 中长线 7 策略选股 → 与 `strategy-engine`、`market_scanner` 能力重叠，避免重复维护两套逻辑。
- 独立 Flask `:5000` → 统一走 Gateway `:8000` + Next 前端。

## 使用方式

```bash
# 仅打印 JSON
python scripts/run_market_sentiment_7d.py

# 先拉一次全市场实时再计算（交易时段更有意义）
UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py
```

前端：打开 **行情**，查看 **全市场 7 维情绪**。

## Cursor Skill

见 `.cursor/skills/a-stock-monitor-sanitized/SKILL.md`（说明如何用本仓库 API，**不要**从 ClawHub 安装未审计 zip）。

---

## 另：AI 投研 Skill（Benign / 纯指令）

[ClawHub · a-stock-ai-research](https://clawhub.ai/haohanyang92/ai-research-assistant) 为 **instruction-only**，无代码、扫描为 Benign。已在仓库落地：

- **`.cursor/skills/a-stock-ai-research/SKILL.md`** — 研报/公告/新闻/回测解读工作流，并绑定 mx_data、Gateway `/api/news`、personal_assistant、回测 API。
