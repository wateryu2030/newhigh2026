# 决策驾驶舱 API 与数据结构说明

与 [DECISION_COCKPIT_DESIGN.md](DECISION_COCKPIT_DESIGN.md) 配套，供前后端对接使用。

---

## 回测结果 JSON 扩展（`/api/run_backtest` 返回的 `result`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `summary` | object | 已有。总收益率、年化、回撤、夏普等 |
| `curve` | array | 已有。策略净值曲线 `[{date, value}, ...]` |
| `holdCurve` | array | 新增。买入持有净值曲线，格式同 `curve` |
| `buyZones` | array | 新增。最优买入区间 `[{start, end}, ...]`，日期 `YYYY-MM-DD` |
| `sellZones` | array | 新增。最优卖出区间，格式同 `buyZones` |
| `signals` | array | 新增。买卖信号列表，见下表 |
| `kline` | array | 新增。K 线数据，见下表 |
| `futureProbability` | object | 新增。`{ up, sideways, down }` 概率，0–1 |
| `futurePriceRange` | object | 新增。`{ low, high, horizonDays }` |

### `signals[]` 单条结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 信号日期 `YYYY-MM-DD` |
| `type` | string | `"buy"` \| `"sell"` |
| `score` | number | 0–100 评分，可选 |
| `winRate` | number | 历史胜率 0–1，可选 |
| `avgReturn` | number | 平均收益，可选 |
| `reasons` | string[] | 技术原因列表，用于「信号原因解释」面板 |

### `kline[]` 单条结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | `YYYY-MM-DD` |
| `open` | number | 开 |
| `high` | number | 高 |
| `low` | number | 低 |
| `close` | number | 收 |
| `volume` | number | 成交量，可选 |

---

## 前端使用建议

- 若 `buyZones` / `sellZones` 为空，则不渲染区间高亮。
- 若 `signals` 为空，则不渲染买卖标记；有则用 `reasons` 驱动「信号原因解释」面板。
- 若 `futureProbability` 全为 `null`，则不展示概率区；若有值则展示扇形/条形图。
- `holdCurve` 与 `curve` 同图双线，展示「策略 vs 持有」。

当前后端已输出上述所有键，未实现逻辑前为空数组/空对象，前端可据此做兼容与占位 UI。
