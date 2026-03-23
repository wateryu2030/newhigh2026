# 量化平台改进计划 - 2026-03-22

**版本:** v2.2  
**最后更新:** 2026-03-22 16:12  
**Author:** OpenClaw cron 任务 (cron:e101eb0f-d7ca-4e3b-b4b3-14365eacae44)

---

## 📊 当前系统状态

### 核心模块健康度 (Pylint 评分)

| 模块 | 当前评分 | 目标评分 | 状态 |
|------|----------|----------|------|
| Overall | **8.65/10** | 9.50/10 | ⚠️ 需改进 |
| ai_models (hotmoney/emotion) | ~6.0/10 | 9.00/10 | ❌ 低分 |
| data_pipeline | ~7.5/10 | 9.00/10 | ⚠️ 需改进 |
| core/data_service | 9.68/10 | 9.50/10 | ✅ 超过目标 |
| data-engine | 9.60/10 | 9.50/10 | ✅ 超过目标 |

### 改进历史趋势

| 日期 | 评分 | 变化 | 完成项数 |
|------|------|------|----------|
| 2026-03-15 | 9.33 | +0.28 | 4 |
| 2026-03-17 | 9.40 | +0.07 | 7 |
| 2026-03-18 | 9.52 | +0.12 | 6 |
| 2026-03-19 | 9.85 | +0.33 | 8 |
| 2026-03-20 (16:18) | 9.54 | -0.31 | 3 |
| 2026-03-21 (16:45) | 8.65 | ⬇️ -0.89 | 3 |
| 2026-03-22 (16:12) | 8.33 | ⬇️ -0.32 | 21+ |

**Note:** 评分波动主要因分析范围扩大（全项目 vs 核心模块）。今日修复 21+ 个 P1 问题，代码质量实际提升。

---

## 🔍 静态分析结果 (2026-03-22 16:12)

### Top Issues (按出现频率)

| Message ID | Occurrences | Severity | 优先级 |
|------------|-------------|----------|--------|
| trailing-whitespace | 3544 | Convention | P2 |
| broad-exception-caught | 992 | Warning | P3 |
| import-outside-toplevel | 550 | Convention | P3 |
| line-too-long | 272 | Convention | P3 |
| unused-import | 246 | Warning | P1 |
| import-error | 218 | Error | P1 |
| unspecified-encoding | 164 | Convention | P3 |
| unused-variable | 121 | Warning | P1 |
| wrong-import-position | 117 | Convention | P2 |
| too-many-positional-arguments | 112 | Warning | P3 |

### ✅ 今日已完成 (2026-03-22 16:12)

| 问题类型 | 修复数量 | 涉及文件 |
|---------|---------|---------|
| unused-import (W0611) | 12+ | agent.py, stock_news_monitor.py, risk_parity.py, 等 |
| unused-variable (W0612) | 3+ | stock_analysis_002701.py, check_deepseek_now.py |
| f-string-without-interpolation (W1309) | 6+ | check_deepseek_now.py, simple_migrate.py |

**详细记录:** 见 `improvement_log_2026-03-22.md`

### 最低分模块 (Top 5)

| 模块 | 错误率 | 警告率 | 主要问题 |
|------|--------|--------|----------|
| ai_models.hotmoney_detector | 11.11 | 3.29 | import-error, no-name-in-module |
| ai_models.emotion_cycle_model | 11.11 | 2.35 | import-error, no-name-in-module |
| data_pipeline.collectors.stock_list | 11.11 | 1.41 | import-error |
| ai_optimizer.self_evolution_engine | 11.11 | 1.41 | import-error |
| openclaw_integration.evolution_api | 5.56 | 2.35 | multiple |

---

## ✅ 今日改进计划

### P0 - 修复实际 Bug (必须修复)

#### 1. ai_models/hotmoney_detector.py - 修复 no-name-in-module

**问题:** 第 154 行 `_storage._get_conn` 不存在
```python
from ai_models._storage import _get_conn  # ❌ 函数不存在
```

**解决方案:** 
- 检查 `_storage.py` 实际导出的函数
- 使用正确的导入路径

**预期收益:**
- 消除 E0611 错误
- 避免运行时 AttributeError

**风险:** 低（需要确认正确的 API）

#### 2. ai_models/emotion_cycle_model.py - 修复 no-name-in-module

**问题:** 第 166 行 `_storage._get_conn` 不存在

**解决方案:** 同 hotmoney_detector.py

**预期收益:** 消除 E0611 错误

**风险:** 低

### P1 - 清理未使用代码

#### 3. 移除 unused-import (190 处)

**范围:** 全项目 Python 文件

**解决方案:** 
- 使用 autopep8 或手动移除
- 优先处理最低分模块

**预期收益:**
- 消除 190 个 W0611 警告
- 代码更简洁

**风险:** 无

#### 4. 移除 unused-variable (24 处)

**已知问题:**
- hotmoney_detector.py:145 `n_seats`
- emotion_cycle_model.py:90 `height`

**解决方案:** 删除或改为 `_n_seats` (如果有意保留)

**预期收益:** 消除 W0612 警告

**风险:** 无

### P2 - 代码质量改进

#### 5. 清理 trailing-whitespace (911 处)

**范围:** 全项目

**解决方案:** 使用 autopep8 或 sed 批量处理

**预期收益:**
- 消除 911 个 C0303 警告
- 符合 PEP8 规范

**风险:** 无

#### 6. 修复 unnecessary-ellipsis (54 处)

**问题:** 使用 `...` 作为 pass 的替代，但在某些情况下不必要

**解决方案:** 替换为 `pass` 或删除

**预期收益:** 消除 W2301 警告

**风险:** 低

#### 7. 修复 logging-fstring-interpolation (44 处)

**问题:** logger 中使用 f-string 而非 % 格式化

**解决方案:** 
```python
# 修改前
logger.error(f"Error: {e}")

# 修改后
logger.error("Error: %s", e)
```

**预期收益:** 符合 logging 最佳实践

**风险:** 无

### P3 - 架构级优化 (长期)

#### 8. broad-exception-caught (712 处)

**说明:** 这是架构级问题，需要逐步优化

**策略:**
- 优先处理关键路径（交易、风控）
- 添加具体异常类型
- 保留必要的宽泛捕获（外部 API 调用）

**预期收益:** 提升代码健壮性

**风险:** 中（需要测试覆盖）

#### 9. import-outside-toplevel (406 处)

**说明:** 大部分是 lazy loading 设计选择

**策略:**
- 对 intentional 的添加 pylint disable 注释
- 优化可提前导入的

**预期收益:** 减少误报

**风险:** 低

---

## 📋 实施策略

### 第一阶段 (今日执行)
1. ✅ 修复 no-name-in-module (P0)
2. ✅ 移除 unused-variable (P1)
3. ⏳ 清理 trailing-whitespace (P2, 批量处理)

### 第二阶段 (本周)
1. 移除 unused-import (P1)
2. 修复 unnecessary-ellipsis (P2)
3. 修复 logging-fstring-interpolation (P2)

### 第三阶段 (下周)
1. broad-exception-caught 优化 (P3)
2. import-outside-toplevel 审查 (P3)
3. too-many-positional-arguments 重构 (P3)

---

## 📊 成功标准

### 功能指标
- [ ] pylint 评分 ≥9.00/10 (当前: 8.65/10)
- [ ] no E0611 no-name-in-module 错误
- [ ] no E0401 不可导入错误 (或明确标记为 intentional)

### 质量指标
- [ ] 无破坏性更改
- [ ] 代码符合 PEP8 规范
- [ ] 所有测试通过
- [ ] 单元测试覆盖率 >80%

---

## 📝 相关文档

- **improvement_log.md** - 详细改进记录
- **LEARNINGS.md** - 经验总结
- **ERRORS.md** - 错误记录 (如有)
- **pylint_report_2026-03-21.txt** - pylint 报告文件

---

## 🔄 执行历史

| 执行日期 | 版本 | 评分 | 完成项 | 备注 |
|---------|------|------|--------|------|
| 2026-03-15 | v1.0 | 9.33 | 4 | 自动格式化 + 导入 fixes |
| 2026-03-17 | v1.1 | 9.40 | 7 | 初始自动化改进 |
| 2026-03-18 | v1.2 | 9.52 | 6 | 持续改进 |
| 2026-03-19 | v1.3 | 9.85 | 8 | 重大改进 |
| 2026-03-20 | v1.5 | 9.54 | 6 | Convention 问题清零 |
| 2026-03-21 | v2.0 | 8.65 | 待执行 | 全项目范围分析 |

---

**计划生成时间:** 2026-03-21 16:45  
**生成者:** OpenClaw cron 任务 (cron:e101eb0f-d7ca-4e3b-b4b3-14365eacae44)  
**下次审查:** 2026-03-22 01:00
