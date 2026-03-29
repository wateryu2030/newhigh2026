# 量化平台改进计划 - 2026-03-29

**版本:** v3.0  
**最后更新:** 2026-03-29 16:00  
**Author:** OpenClaw cron 任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)

---

## 📊 当前系统状态

### 核心模块健康度 (Pylint 评分)

| 模块 | 当前评分 | 目标评分 | 状态 |
|------|----------|----------|------|
| Overall | **9.42/10** | 9.50/10 | ⚠️ 略低于目标 |
| ai_models (整体) | ~9.60/10 | 9.50/10 | ✅ 超过目标 |
| data-engine (整体) | ~9.30/10 | 9.50/10 | ⚠️ 需改进 |
| core/data_service | 9.68/10 | 9.50/10 | ✅ 超过目标 |

### 改进历史趋势

| 日期 | 评分 | 变化 | 完成项数 |
|------|------|------|----------|
| 2026-03-25 (Afternoon) | 9.65/10 | ⬆️ +0.39 | 3 |
| 2026-03-26 | - | - | - |
| 2026-03-27 | - | - | - |
| 2026-03-28 | - | - | - |
| 2026-03-29 (Today) | 9.42/10 | ⬇️ -0.23 | 待执行 |

**Note:** 今日评分下降是因为新增了一些 data-engine 模块的问题。需要修复 broad-exception-caught 和 line-too-long 问题。

---

## 🔍 静态分析结果 (2026-03-29 16:00)

### Top Issues (按出现频率)

| Message ID | Occurrences | Severity | 优先级 |
|------------|-------------|----------|--------|
| broad-exception-caught | 45 | Warning | P2 |
| import-error | 19 | Error | P1 |
| too-many-positional-arguments | 17 | Warning | P3 |
| line-too-long | 12 | Convention | P3 |
| import-outside-toplevel | 12 | Convention | P2 |
| fixme | 1 | Warning | P2 |

### 最低分模块 (Top 3 - 按问题数量)

| 模块 | 问题数 | 主要问题 |
|------|--------|----------|
| connector_astock_duckdb.py | 11 | line-too-long (3), broad-exception-caught (5), too-many-positional-arguments (1) |
| wechat_collector.py | 10 | broad-exception-caught (9), fixme (1) |
| connector_akshare.py | 7 | broad-exception-caught (5), too-many-positional-arguments (2) |

---

## ✅ 今日改进计划

### P1 - 修复实际错误 (import-error)

#### 1. 调查 import-error (19 处)

**问题:** 多个文件存在 `data_pipeline.storage.duckdb_manager` 导入错误

**解决方案:** 
- 检查模块路径是否正确
- 如为误报，添加正确的 pylint disable 注释

**预期收益:**
- 消除 E0401 错误
- 避免运行时 ImportError

**风险:** 中（需要确认模块路径）

### P2 - 代码质量改进

#### 2. connector_astock_duckdb.py - 修复 line-too-long (3 处)

**问题:** 第 236, 239, 242 行超过 120 字符

**解决方案:** 
```python
# 修改前：超长 SQL 语句
query = "SELECT ... (very long query)"

# 修改后：使用括号隐式连接
query = (
    "SELECT ... "
    "FROM ... "
    "WHERE ..."
)
```

**预期收益:** 符合 PEP8 规范，提升可读性

**风险:** 低

#### 3. connector_astock_duckdb.py - 优化异常处理 (5 处)

**问题:** 5 处 broad-exception-caught

**解决方案:** 
```python
# 修改前
except Exception:

# 修改后
except (RuntimeError, ValueError, OSError):
```

**预期收益:** 符合最佳实践，提升代码健壮性

**风险:** 低

#### 4. wechat_collector.py - 优化异常处理 (9 处)

**问题:** 9 处 broad-exception-caught

**解决方案:** 同上，使用具体异常类型

**预期收益:** 符合最佳实践

**风险:** 低（需要测试覆盖）

#### 5. connector_akshare.py - 优化异常处理 (5 处)

**问题:** 5 处 broad-exception-caught

**解决方案:** 同上

**预期收益:** 符合最佳实践

**风险:** 低

### P3 - 架构级优化 (本周)

#### 6. too-many-positional-arguments (17 处)

**策略:**
- 审查函数签名
- 考虑使用 dataclass 或配置对象
- 对合理情况添加 pylint disable 注释

**预期收益:** 提升代码可维护性

**风险:** 中（可能需要重构）

---

## 📋 实施策略

### 第一阶段 (今日执行)
1. ✅ 修复 connector_astock_duckdb.py line-too-long (P2)
2. ✅ 修复 connector_astock_duckdb.py broad-exception-caught (P2)
3. ⏳ 调查 import-error (P1)

### 第二阶段 (本周)
1. wechat_collector.py broad-exception-caught 优化 (P2)
2. connector_akshare.py broad-exception-caught 优化 (P2)
3. import-error 批量标记 (P1)

### 第三阶段 (下周)
1. too-many-positional-arguments 审查 (P3)
2. 架构级重构规划

---

## 📊 成功标准

### 功能指标
- [ ] pylint 评分 ≥9.50/10 (当前: 9.42/10)
- [ ] connector_astock_duckdb ≥9.50/10
- [ ] wechat_collector ≥9.50/10
- [ ] 无 E0401 错误（或正确标记）

### 质量指标
- [ ] 无破坏性更改
- [ ] 代码符合 PEP8 规范
- [ ] 所有测试通过

---

## 📝 相关文档

- **improvement_log.md** - 详细改进记录
- **LEARNINGS.md** - 经验总结
- **ERRORS.md** - 错误记录 (如有)
- **pylint_report_2026-03-29.txt** - pylint 报告文件

---

**计划生成时间:** 2026-03-29 16:00  
**生成者:** OpenClaw cron 任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)  
**下次审查:** 2026-03-30 01:00
