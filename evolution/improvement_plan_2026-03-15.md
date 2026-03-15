# 量化平台改进计划 - 2026-03-15

**执行时间:** 2026-03-15 21:25 (Asia/Shanghai)
**Pylint 评分:** 9.37/10 (较上次 9.60 下降 0.23)

---

## 📊 静态分析结果

### 问题文件 Top 5

| 排名 | 文件 | 问题数 | 主要问题 |
|------|------|--------|----------|
| 1 | `data-engine/src/data_engine/connector_tushare.py` | 12 | 导入别名、参数过多 |
| 2 | `data-engine/src/data_engine/connector_astock_duckdb.py` | 11 | 参数过多、分支多、长行 |
| 3 | `strategy-engine/src/strategy_engine/ai_fusion_strategy.py` | 4 | 参数过多、嵌套深 |
| 4 | `data-engine/src/data_engine/data_pipeline.py` | 4 | 参数过多、导入别名 |
| 5 | `data-engine/src/data_engine/connector_akshare.py` | 3 | 参数过多、嵌套深 |

### 问题类型统计

| 问题代码 | 数量 | 说明 | 优先级 |
|---------|------|------|--------|
| W0407 (preferred-module) | 8 | 应使用别名导入 (np, dt) | 🟡 中 |
| R0917 (too-many-positional-arguments) | 9 | 函数参数过多 | 🟡 中 |
| C0301 (line-too-long) | 2 | 行超过 100 字符 | 🟢 低 |
| R1702 (too-many-nested-blocks) | 1 | 嵌套过深 (6/5) | 🔴 高 |
| C0415 (import-outside-toplevel) | 1 | 函数内导入 | 🟡 中 |
| R0801 (duplicate-code) | 1 | 重复代码块 | 🟢 低 |

---

## ✅ 上次计划完成情况 (2026-03-14)

- [x] 修复 `ai_fusion_strategy.py` 的导入问题 (6.27→9.75/10)
- [x] 修复 logging f-string 问题
- [x] 运行测试验证
- [ ] 统一导入规范 (部分完成)

---

## 🔴 高优先级改进（今日实施）

### 1. 修复 `ai_fusion_strategy.py` 嵌套过深问题

**问题:** `strategy-engine/src/strategy_engine/ai_fusion_strategy.py:151` - 6 层嵌套（限制 5）

**当前代码结构:**
```python
def generate_signals(...):
    if condition_a:
        if condition_b:
            if condition_c:
                if condition_d:
                    if condition_e:
                        # 实际逻辑
```

**改进方案:** 使用提前返回（early return）和守卫子句（guard clauses）

```python
def generate_signals(...):
    if not condition_a:
        return []
    if not condition_b:
        return []
    if not condition_c:
        return []
    if not condition_d:
        return []
    if not condition_e:
        return []
    # 实际逻辑（现在只有 1 层嵌套）
```

**预期收益:**
- 提高代码可读性
- 降低认知负担
- 符合 pylint 规范

**风险:** 低（逻辑等价转换）
**成本:** 30 分钟

---

### 2. 统一导入别名规范（W0407）

**问题:** 8 个文件使用 `import datetime` / `import numpy` 而非标准别名

**受影响文件:**
- `data-engine/src/data_engine/data_pipeline.py` - datetime
- `data-engine/src/data_engine/realtime_stream.py` - datetime
- `core/src/core/types.py` - datetime
- `strategy-engine/src/strategy_engine/breakout.py` - numpy
- `strategy-engine/src/strategy_engine/mean_reversion.py` - numpy
- `strategy-engine/src/strategy_engine/trend_following.py` - numpy

**改进方案:**
```python
# 修改前
import datetime
import numpy

# 修改后
import datetime as dt
import numpy as np
```

**预期收益:**
- 符合 Python 量化行业规范
- 代码更简洁
- 消除 8 个 pylint 警告

**风险:** 极低（仅别名变更）
**成本:** 15 分钟

---

## 🟡 中优先级改进（本周内实施）

### 3. 优化函数参数过多问题（R0917）

**问题:** 9 个函数参数超过 5 个（pylint 限制）

**典型示例:**
```python
def fetch_klines_from_astock_duckdb(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str = "daily",
    adjust: str = "qfq",
    limit: int = 1000,
    read_only: bool = True
) -> List[OHLCV]:
```

**改进方案:** 使用配置对象或 dataclass 封装参数

```python
from dataclasses import dataclass

@dataclass
class KlineQuery:
    symbol: str
    start_date: str | None = None
    end_date: str | None = None
    period: str = "daily"
    adjust: str = "qfq"
    limit: int = 1000
    read_only: bool = True

def fetch_klines_from_astock_duckdb(query: KlineQuery) -> List[OHLCV]:
```

**预期收益:**
- 提高 API 可读性
- 便于扩展新参数
- 消除 pylint 警告

**风险:** 中（需要更新所有调用点）
**成本:** 60 分钟

---

### 4. 修复 `trade_signal_aggregator.py` 导入问题

**问题:** `C0415` - 函数内导入 `core.Signal`

**改进方案:** 移至模块顶层导入

**风险:** 低
**成本:** 5 分钟

---

## 🟢 低优先级改进（下周计划）

### 5. 拆分长行（C0301）

**问题:** 2 行超过 100 字符

**改进方案:** 使用 black 格式化或手动拆分

**风险:** 极低
**成本:** 10 分钟

---

### 6. 消除重复代码（R0801）

**问题:** `connector_akshare.py` 和 `connector_tushare.py` 有重复的 `_normalize_symbol` 逻辑

**改进方案:** 提取到公共模块 `data_engine/utils.py`

**风险:** 中（需要测试两个连接器）
**成本:** 45 分钟

---

## 📋 今日执行计划

### 第一阶段：安全检查（5 分钟）
```bash
cd ./newhigh
git add .
git commit -m "Backup before 2026-03-15 auto-improvement"
```

### 第二阶段：修复嵌套问题（30 分钟）
- 修改 `ai_fusion_strategy.py` 的 `generate_signals` 函数
- 使用 early return 减少嵌套
- 运行测试验证

### 第三阶段：统一导入别名（15 分钟）
- 修改 6 个文件的导入语句
- 运行 pylint 验证

### 第四阶段：修复导入位置（5 分钟）
- 修改 `trade_signal_aggregator.py`

### 第五阶段：验证与记录（15 分钟）
- 运行相关测试
- 更新 `improvement_log.md`
- 更新 `LEARNINGS.md`

---

## 📈 成功标准

- [ ] pylint 评分恢复至 9.60/10 以上
- [ ] 消除 R1702 嵌套警告
- [ ] 消除所有 W0407 导入别名警告
- [ ] 所有测试通过
- [ ] 无破坏性更改

---

## 📝 备注

- 所有修改前必须 git commit 备份
- 优先修复高优先级问题（嵌套、导入规范）
- 参数过多问题需要重构 API，留待本周内完成
