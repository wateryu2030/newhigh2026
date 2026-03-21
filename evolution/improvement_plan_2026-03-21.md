# 量化平台改进计划 - 2026-03-21

**执行时间:** 2026-03-21 16:00 (Asia/Shanghai)  
**Pylint 评分:** core/src 9.59/10, data/src 7.95/10  
**任务类型:** 每日自我进化任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)

---

## 📊 当前系统状态

### 核心模块健康度

| 模块 | Pylint 评分 | 变化 | 状态 |
|------|------------|------|------|
| core/src | 9.59/10 | ➡️ | ✅ 优秀 |
| data/src | 7.95/10 | ⬆️ +0.15 | 🟡 需改进 |
| **整体** | **8.19/10** | ⬆️ +0.39 | 🟢 良好 |

### 昨日改进回顾 (2026-03-20)

**已完成:**
- ✅ core/src trailing whitespace 清理 (+1.36 分)
- ✅ core/src unused-import 修复
- ✅ core 包安装 (消除 import-error)

**遗留问题:**
- data/src 仍有大量 broad-exception-caught (W0718)
- unused-import (W0611) 待清理
- import-outside-toplevel (C0415) 部分为 lazy loading 设计

---

## 🔧 改进点 (按优先级排序)

### P1: 修复 ashare_longhubang.py 的 unused-import 和 broad-exception-caught

**当前问题:**
- W0611: Unused datetime imported as dt (line 7)
- W0718: Catching too general exception Exception (7 处)
- C0415: Import outside toplevel (多处)
- 评分：6.02/10 (最低)

**预期收益:**
- 消除 1 个 unused-import 警告
- 优化异常处理，提高代码健壮性
- 目标评分：7.5/10+

**具体修改方案:**
1. 移除未使用的 `import datetime as dt` (实际使用 `dt.datetime.now()`)
2. 将部分 `except Exception` 改为更具体的异常类型
3. 保持 lazy loading 设计 (C0415 为设计选择)

**可能的风险:** 低 (异常类型需准确判断)

---

### P2: 修复 binance_source.py 的 unused-import 和 line-too-long

**当前问题:**
- W0611: Unused List imported from typing
- C0301: Line too long (126/120)
- W0718: broad-exception-caught (6 处)

**预期收益:**
- 消除 unused-import 警告
- 符合行宽规范
- 目标评分：7.0/10+

**具体修改方案:**
1. 移除未使用的 `List` 导入
2. 拆分超长行
3. 优化异常处理

**可能的风险:** 无

---

### P3: 修复 financial_report_job.py 的 f-string 和 broad-exception-caught

**当前问题:**
- W1309: f-string without interpolation (3 处)
- W0718: broad-exception-caught (4 处)
- E0401: import-error (lib.database 未安装)

**预期收益:**
- 消除 f-string 警告
- 优化异常处理
- 目标评分：7.5/10+

**具体修改方案:**
1. 将 `f"static text"` 改为 `"static text"`
2. 细化异常类型
3. 安装 lib 包 (如存在)

**可能的风险:** 低

---

### P4: 清理 data/src 的 trailing whitespace

**当前问题:**
- C0303: trailing-whitespace (估计 100+ 处)

**预期收益:**
- 符合 PEP8 规范
- 提升代码可读性

**具体修改方案:**
```bash
find data/src -name "*.py" -exec sed -i '' 's/[[:space:]]*$//' {} \;
```

**可能的风险:** 无

---

## 📅 执行计划

### 今日重点 (2026-03-21)
1. ✅ 修复 ashare_longhubang.py (P1)
2. ✅ 修复 binance_source.py (P2)
3. ✅ 修复 financial_report_job.py (P3)
4. ⏳ 清理 trailing whitespace (P4)
5. ⏳ 验证测试

### 明日计划 (2026-03-22)
1. 修复其他低分文件
2. 继续优化 broad-exception-caught
3. 检查 unused-import 剩余问题

### 本周目标
- data/src 评分提升至 8.5/10+
- 消除所有 unused-import 警告
- 减少 30% 的 broad-exception-caught 警告

---

## 📈 预期成果

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| data/src 评分 | 7.95/10 | 8.5/10 | +0.55 |
| unused-import | ~20 | 0 | -100% |
| f-string-without-interpolation | 48 | 40 | -17% |
| broad-exception-caught | 840 | 750 | -11% |

---

**生成时间:** 2026-03-21 16:00 (Asia/Shanghai)  
**下次更新:** 2026-03-22 16:00 (Asia/Shanghai)
