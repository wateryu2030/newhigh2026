# 量化平台改进计划
## 2026-03-15

基于对 `newhigh` 项目的静态分析（pylint），识别出以下可落地的改进点。

---

## ✅ 已完成改进（历史回溯）

### 2026-03-12
- 自动代码格式化（autopep8）
- pylint 评分：8.15 → 8.70/10

### 2026-03-14
- 修复 `ai_decision.py`, `notification.py` 的 logging-fstring 问题
- 修复 `ai_fusion_strategy.py` 的导入问题
- pylint 评分：8.87 → 9.33/10

---

## 2026-03-15 静态分析结果

**当前 pylint 评分：9.33/10** (本月内提升 1.18 分)

### 问题统计总计 59 个问题

| 问题代码 | 数量 | 说明 |
|---------|------|------|
| C0415 (import-outside-toplevel) | 6 | 函数内的导入语句 |
| C0301 (line-too-long) | 11 | 行超过 100 字符 |
| R0917 (too-many-positional-arguments) | 9 | 函数参数过多 |
| R0912 (too-many-branches) | 4 | 分支过多 |
| R1702 (too-many-nested-blocks) | 2 | 嵌套过深 |
| W0407 (preferred-module) | 8 | 应使用别名导入 (np, dt) |
| W0611 (unused-import) | 4 | 未使用的导入 |
| C0207 (use-maxsplit-arg) | 5 | split 应指定 maxsplit |
| W0404/W0412 (reimported/ungrouped) | 2 | 重复导入/分组问题 |
| R0801 (duplicate-code) | 2 | 重复代码块 |
| E1101/E1123/E1120 (no-member/keyword-arg/value) | 4 | 代码逻辑问题 |

### 问题文件 Top 5

| 排名 | 文件 | 问题数 | 主要问题 |
|------|------|--------|----------|
| 1 | `data-engine/src/data_engine/connector_akshare.py` | 9 | 参数过多、嵌套深、maxsplit |
| 2 | `data-engine/src/data_engine/connector_tushare.py` | 8 | 参数过多、return 语句多 |
| 3 | `data-engine/src/data_engine/connector_astock_duckdb.py` | 8 | 参数过多、分支多、长行 |
| 4 | `core/src/core/data_service/db.py` | 2 | 导入位置不当 |
| 5 | `strategy-engine/src/strategy_engine/ai_fusion_strategy.py` | 5 | 参数过多、嵌套深 |

---

## 改进点优先级排序

### 🔴 高优先级：修复代码逻辑问题（今日实施）

**问题 1：`data-engine/src/data_engine/connector_akshare.py:146` - 嵌套过深**
- **问题**：6 层嵌套（限制 5）
- **预期收益**：提高可读性
- **具体方案**：使用提前返回（early return）减少嵌套
- **风险**：低 (需验证逻辑)
- **成本**：30 分钟

**问题 2：`connector_akshare.py:11` 等处 - 使用 maxsplit 参数**
- **问题**：`split('.')[0]` 应为 `split('.', maxsplit=1)[0]`
- **预期收益**：避免意外分割
- **具体方案**：全局替换为 maxsplit=1
- **风险**：极低
- **成本**：10 分钟

**实施计划**：
```bash
# 修复嵌套问题
autopep8 --in-place --max-per-line 120 \
  data-engine/src/data_engine/connector_akshare.py
```

---

### 🟡 中优先级：统一导入规范（本周内实施）

**问题：`W0407` 警告 - 应使用别名导入**
- **文件**：`connector_akshare.py`, `connector_tushare.py`, `connector_yahoo.py`, `clickhouse_storage.py`, `realtime_stream.py`, `mean_reversion.py`, `breakout.py`
- **问题**：`import datetime` → `import datetime as dt`, `import pandas` → `import pandas as pd`, `import numpy` → `import numpy as np`
- **预期收益**：符合行业规范，提高代码简洁性
- **具体方案**：
  1. 运行 `autopep8 --in-place --aggressive` 自动修复
  2. 手动检查保留项
- **风险**：极低
- **成本**：20 分钟

---

### 🟢 低优先级：长行优化（下周计划）

**问题：`C0301` 警告 - 行超过 100 字符**
- **文件**：`connector_astock_duckdb.py` (6 处), `data_pipeline.py` (1 处), `ai_fusion_strategy.py` (1 处)
- **预期收益**：提高可读性，符合 lint 规范
- **具体方案**：
  1. 使用 `black` 格式化自动拆分
  2. 手动优化复杂表达式
- **风险**：低
- **成本**：30 分钟

---

## 每日改进计划（2026-03-15）

### 第一阶段：安全检查（5 分钟）
```bash
cd ./newhigh
git add .
git commit -m "Backup before 2026-03-15 auto-improvement"
```

### 第二阶段：修复高优先级问题（60 分钟）
1. 修复 `connector_akshare.py` 的嵌套问题
2. 修复所有 `split()` 使用 maxsplit=1
3. 运行 pylint 验证修复效果

### 第三阶段：代码格式化（30 分钟）
```bash
source .venv/bin/activate
autopep8 --in-place --aggressive --max-line-length 120 \
  data-engine/src/data_engine/*.py \
  strategy-engine/src/strategy_engine/*.py
```

### 第四阶段：验证测试（30 分钟）
```bash
python -m pytest data-engine/tests/ -v --tb=short
python -m pytest strategy-engine/tests/ -v --tb=short
```

### 第五阶段：记录结果（15 分钟）
- 更新 `improvement_log.md`
- 若有成功经验，写入 `LEARNINGS.md`
- 若有失败，写入 `ERRORS.md`

---

## 成功标准

- [ ] pylint 评分提升至 9.5/10 以上
- [ ] 消除所有嵌套深度警告（R1702）
- [ ] 消除所有 `split` 未指定 maxsplit 的警告（C0207）
- [ ] 所有测试通过
- [ ] 无破坏性更改

---

## 备注

- 所有修改前必须 git add + commit 备份
- 优先修复高优先级问题（嵌套、maxsplit），影响代码逻辑
- 格式化工具可能无法完全解决所有问题，需要人工 review
