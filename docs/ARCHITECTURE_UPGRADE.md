# 架构升级说明（五层架构雏形）

围绕「技术形态选股 + 动态高频能力 + 市场热点 + 仓位控制」做的升级，与现有回测、AI 评分、GA 优化衔接。

---

## 一、已实现模块

### 1. 数据层（沿用现有）
- 数据库 / AKShare / data_loader 不变。

### 2. 市场理解层（Market）

- **`market/sector_strength.py`**：板块强度（涨幅排名），AKShare 东方财富板块。
- **`market/money_flow.py`**：个股/板块资金流向（主力净流入等）。
- **`market/hot_theme_detector.py`**：热点强度 = 板块强度权重 + 资金流权重 + 换手权重，输出 0~100。

**API**：`GET /api/market/sector_strength`，`GET /api/market/regime`（市场状态 BULL/BEAR/NEUTRAL）。

### 3. 形态层（Pattern Engine）

- **`patterns/trend_patterns.py`**：多头排列、上升通道、突破平台、新高突破、均线粘合发散。
- **`patterns/reversal_patterns.py`**：双底、V 反、超跌反弹。
- **`patterns/volume_patterns.py`**：放量突破、缩量回踩、主力吸筹。
- **`patterns/pattern_engine.py`**：统一跑上述形态，输出 `pattern_score`、`pattern_tags`。

### 4. 策略层（沿用 + 多周期）

- **`core/multitimeframe.py`**：多周期共振 `multi_tf_signal(daily, m30, m5)`，日线趋势 + 30m 回调 + 5m 突破。

### 5. 组合与风控层

- **`risk/position_sizing.py`**：风险预算仓位  
  `position_size(capital, risk_pct, stop_loss_pct)` → 仓位 = 单笔风险 / 止损幅度；  
  `position_size_with_atr(...)` 支持 ATR 止损。
- 现有 `risk/RiskEngine`、`position_control` 不变。

### 6. 专业扫描流水线

- **`scanner/scanner_pipeline.py`**：  
  全市场扫描 → 技术形态过滤 → 热点过滤 → 风险预算 → AI 评分排序。  
  输出：标的、买点概率、风险等级、建议仓位%、形态标签、热点强度。

**API**：`POST /api/scan/professional`。

---

## 二、前端（Web）

- **市场状态**：AI 推荐页「刷新市场状态」调用 `/api/market/regime`，展示 BULL/BEAR/NEUTRAL。
- **专业扫描**：AI 推荐页「运行专业扫描」调用 `/api/scan/professional`，表格展示买点概率、风险、建议仓位、形态/热点。

---

## 三、使用与扩展建议

1. **形态**：在选股或扫描中接入 `PatternEngine().get_latest_patterns(df)` 做过滤或打分。
2. **热点**：用 `get_hot_strength(symbol)` 或 `HotThemeDetector` 做板块/个股热度过滤。
3. **仓位**：下单前用 `position_size(capital, risk_pct, stop_loss_pct)` 算建议仓位。
4. **多周期**：有 30m/5m 数据时，用 `multi_tf_signal(daily, m30, m5)` 做共振过滤。

---

## 四、后续可做（未实现）

- 30m/5m 数据源与定时拉取。
- 定时任务（APScheduler/Celery）收盘后自动扫描、报告。
- UI：买卖点标注、未来概率、风险仪表盘（部分已有，可再强化）。

---

**结论**：趋势、资金、风险三个核心已接入；形态引擎、热点、风险预算、专业扫描与现有回测/AI/GA 协同，形成准机构级流水线雏形。
