# 量化平台改进计划 - 2026-04-05

**版本:** v4.0  
**最后更新:** 2026-04-05 17:00  
**Author:** OpenClaw cron 任务 (cron:e101eb0f-d7ca-4e3b-b4b3-14365eacae44)

---

## 📊 当前系统状态

### 核心模块健康度 (Pylint 评分)

| 模块 | 当前评分 | 目标评分 | 状态 |
|------|----------|----------|------|
| **核心模块 (core/data-engine/strategy)** | **9.21/10** | 9.50/10 | ⚠️ 需改进 |
| Previous Run (2026-04-04) | 9.90/10 | - | - |
| Change | -0.69 | - | ⬇️ 评分下降 (扫描范围扩大) |

**Note:** 今日评分下降是因为扫描范围从部分核心模块扩大到 `core/ data-engine/ strategy/` 全量目录，包含了更多测试文件和边缘模块。实际代码质量未下降。

### 改进历史趋势

| 日期 | 评分 | 变化 | 完成项数 | 备注 |
|------|------|------|----------|------|
| 2026-03-25 (Afternoon) | 9.65 | ⬆️ +0.39 | 3 | 最低分模块优化 |
| 2026-04-01 | 8.39 | - | 8 | P0 修复 |
| 2026-04-02 | 8.42 | +0.03 | 23 | P2 优化 |
| 2026-04-03 (Morning) | 9.79 | +1.37 | 25 | P0/P1 修复 |
| 2026-04-03 (Afternoon) | 9.84 | +0.05 | 5 | P0/P1/P2 修复 |
| 2026-04-04 | 9.90 | +0.06 | 16 | P2/P3 优化 |
| **2026-04-05** | **9.21** | **-0.69** | **0** | **扫描范围扩大** |

---

## 🔍 静态分析结果 (2026-04-05 17:00)

### 问题统计 (按出现频率)

| Message ID | Occurrences | Severity | 优先级 |
|------------|-------------|----------|--------|
| import-error | 127 | Error | P3 (测试文件误报) |
| import-outside-toplevel | 76 | Convention | P3 |
| consider-using-with | 40 | Refactor | P2 |
| too-many-positional-arguments | 21 | Refactor | P3 |
| unused-import | 16 | Warning | P2 |
| unused-argument | 16 | Warning | P3 |
| protected-access | 16 | Warning | P3 |
| broad-exception-caught | 10 | Warning | P2 |
| wrong-import-order | 8 | Convention | P3 |
| disallowed-name | 8 | Convention | P3 |

### 错误统计

| 类别 | 数量 | 状态 |
|------|------|------|
| Error | 37 | ⚠️ 主要为测试文件 import-error 误报 |
| Warning | 21 | 持续优化中 |
| Refactor | 13 | 持续优化中 |
| Convention | 23 | 持续优化中 |

### 最低分模块 (Top 3)

| 模块 | 评分 | 主要问题 |
|------|------|----------|
| tests.test_data_service | 低 | 13.51% error, 9.52% warning |
| tests.test_connector_astock_duckdb | 低 | 13.51% error (import-error) |
| tests.test_connector_yahoo | 低 | 10.81% error (import-error) |

---

## 📋 今日改进计划 (2026-04-05)

### P2 - 代码质量优化

#### 1. consider-using-with 审查 (40 处)

**问题:** 资源分配操作未使用 `with` 语句，可能导致资源泄露

**影响文件:**
- core/tests/test_data_service.py (多处)
- data-engine/ 和 strategy/ 中的文件

**解决方案:** 
- 审查每个案例，对文件/数据库连接操作添加 `with` 语句
- 对测试文件中的 mock 对象可添加 pylint disable 注释

**预期收益:** 提升资源管理安全性，避免资源泄露

**风险:** 中（需要仔细审查每个案例，测试文件可能需特殊处理）

---

#### 2. broad-exception-caught 审查 (10 处)

**问题:** 过多使用 `except Exception` 可能掩盖真实错误

**影响文件:**
- data-engine/src/data_engine/data_pipeline.py (1 处)
- strategy/src/strategies/daily_stock_analysis/test_basic.py (4 处)
- strategy/src/strategies/daily_stock_analysis/config.py (1 处，可能已有注释)
- 其他文件 (4 处)

**解决方案:** 
- 审查每个案例，评估是否需要更具体的异常类型
- 对合理的广泛捕获添加注释说明原因
- 考虑添加日志记录

**预期收益:** 提升错误诊断能力

**风险:** 低（主要是添加注释，少量代码修改）

---

#### 3. unused-import 清理 (16 处)

**问题:** 未使用的导入语句增加加载时间，降低代码可读性

**影响文件:**
- data-engine/tests/test_connector_akshare.py (3 处)
- data-engine/tests/test_connector_binance.py (1 处)
- 其他测试文件

**解决方案:** 
- 删除未使用的导入语句
- 对测试文件中故意保留的导入添加 pylint disable 注释

**预期收益:** 减少不必要的导入，提升代码清晰度

**风险:** 低

---

### P3 - 代码风格优化

#### 4. too-many-positional-arguments 审查 (21 处)

**问题:** 函数参数过多，可能影响可读性

**影响文件:**
- core/src/core/data_service/emotion_service.py (1 处)
- data-engine/src/data_engine/clickhouse_storage.py (1 处)
- data-engine/src/data_engine/connector_yahoo.py (1 处)
- data-engine/src/data_engine/data_pipeline.py (2 处)
- data-engine/src/data_engine/connector_binance.py (1 处)
- strategy/src/strategy_engine/ai_fusion_strategy.py (1 处)

**解决方案:** 
- 审查每个案例，评估是否需要重构
- 考虑使用 dataclass 或命名参数
- 对合理情况（如构造函数）添加 disable 注释

**预期收益:** 提升代码可维护性

**风险:** 中（重构可能影响调用方）

---

#### 5. import-outside-toplevel 审查 (76 处)

**问题:** 导入语句不在文件顶层

**分析:** 大部分是合理的延迟导入（避免循环依赖、减少启动时间）

**解决方案:** 
- 审查每个案例，对合理的延迟导入添加 pylint disable 注释
- 对可移动到顶层的导入进行调整

**预期收益:** 符合 PEP 8 规范

**风险:** 低

---

## 📊 成功标准

### 功能指标
- [ ] pylint 评分 ≥9.50/10 (当前: 9.21/10)
- [ ] consider-using-with 修复 ≥20 处
- [ ] broad-exception-caught 审查完成
- [ ] unused-import 清理完成

### 质量指标
- [ ] 无真实 error 级别问题（测试文件误报可忽略）
- [ ] 所有修改通过 `python3 -m py_compile` 验证
- [ ] Git 提交记录清晰

---

## 📝 执行策略

### 优先级顺序

1. **unused-import 清理** (16 处) - 低风险，快速修复
2. **broad-exception-caught 审查** (10 处) - 添加注释为主
3. **consider-using-with 修复** (40 处) - 分批次修复
4. **too-many-positional-arguments 审查** (21 处) - 选择性处理

### 验证流程

每个修改后执行：
```bash
python3 -m py_compile <file>.py
git diff <file>.py
```

### 回滚方案

如修改引入问题：
```bash
git restore <file>.py
```

---

## 📅 执行历史

| 执行日期 | 版本 | 评分 | 完成项 | 备注 |
|---------|------|------|--------|------|
| 2026-03-15 | v1.0 | 9.33 | 4 | 自动格式化 + 导入 fixes |
| 2026-03-17 | v1.1 | 9.40 | 7 | 初始自动化改进 |
| 2026-03-18 | v1.2 | 9.52 | 6 | 持续改进 |
| 2026-03-19 | v1.3 | 9.85 | 8 | 重大改进 |
| 2026-03-20 | v1.5 | 9.54 | 6 | Convention 问题清零 |
| 2026-03-21 | v2.0 | 8.65 | 3 | 全项目范围分析 |
| 2026-03-22 | v2.1 | 8.33 | 21+ | Convention 问题修复 |
| 2026-03-24 | v2.2 | 9.26 | 10+ | broad-exception-caught 优化 |
| 2026-03-25 (AM) | v2.3 | 9.26 | 3 | unknown-option-value 修复 |
| 2026-03-25 (PM) | v2.4 | 9.65 | 3 | 最低分模块优化 |
| 2026-04-01 | v2.5 | 8.39 | 8 | P0 修复 |
| 2026-04-02 | v2.6 | 8.42 | 23 | P2 优化 |
| 2026-04-03 (AM) | v3.0 | 9.79 | 25 | P0/P1 修复 |
| 2026-04-03 (PM) | v3.1 | 9.84 | 5 | P0/P1/P2 修复 |
| 2026-04-04 | v3.2 | 9.90 | 16 | P2/P3 优化 |
| **2026-04-05** | **v4.0** | **9.21** | **0** | **扫描范围扩大** |

---

**计划生成时间:** 2026-04-05 17:00  
**生成者:** newhigh-01 (OpenClaw cron 任务)  
**下次审查:** 2026-04-05 18:00
