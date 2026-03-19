---
name: a-stock-monitor-sanitized
description: A 股全市场 7 维情绪评分与行情快照（newhigh 内置实现）。替代 ClawHub「A Stock Monitor」中不安全的未审计包；在用户询问市场情绪仪表盘、涨跌家数比、涨停比、全市场评分时使用。通过 Gateway API 与 DuckDB/akshare 取数，禁止安装含 GUI 自动化与硬编码密钥的第三方同名 skill。
---

# A 股监控能力（newhigh 安全版）

## 不要用 ClawHub 原始包

[A Stock Monitor 1 on ClawHub](https://clawhub.ai/nuradil/a-stock-monitor-1) 被标为 **Suspicious**（GUI 控制桌面、硬编码密钥等）。**使用本仓库已整合能力即可。**

## 数据接口

- **7 维情绪**：`GET /api/market/sentiment-7d`（或经 Next 代理 `/api/market/sentiment-7d`）
- **实时榜单**：`GET /api/market/realtime`（成交额排序）
- **情绪周期（AI）**：`GET /api/market/emotion`

## 本地脚本

```bash
python scripts/run_market_sentiment_7d.py
UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py
```

## 维度说明（与公开 Skill 描述对齐）

涨跌家数比、平均涨幅、涨跌停比、强势股占比、成交活跃度、波动率、趋势强度 → 加权合成 0–100 分及等级文案。

## 扩展选股

短线/中长线多策略选股请优先使用本项目的 `trade_signals`、`sniper_candidates`、`strategy` 相关 API，而非外部未审计脚本。
