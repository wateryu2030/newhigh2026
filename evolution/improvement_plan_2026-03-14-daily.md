# 量化平台每日改进计划
## 2026-03-14 (周六)

### 上次计划完成情况回顾

**2026-03-12 计划完成情况：**
- ✅ 代码格式化完成 (autopep8)
- ✅ pylint 评分从 8.15 → 8.70/10
- ✅ 核心测试全部通过
- ⏳ 异常处理优化 - 部分完成
- ⏳ 文档字符串添加 - 进行中

**当前 pylint 评分：8.87/10** (较上次 +0.17)

---

## 本次静态分析结果

### 问题文件 Top 5 (按问题数量排序)

| 排名 | 文件 | 问题数 | 主要问题类型 |
|------|------|--------|-------------|
| 1 | `strategy-engine/src/strategy_engine/ai_fusion_strategy.py` | 25 | 导入错误、导入位置、行过长、复杂度 |
| 2 | `strategy-engine/src/strategies/daily_stock_analysis/ai_decision.py` | 17 | 导入位置、未使用变量 |
| 3 | `strategy-engine/src/strategies/daily_stock_analysis/main.py` | 16 | 导入位置、行过长 |
| 4 | `data-engine/src/data_engine/connector_tushare.py` | 13 | 导入位置、异常处理 |
| 5 | `strategy-engine/src/strategies/daily_stock_analysis/test_basic.py` | 11 | 测试代码规范 |

### 问题类型分布

| 问题代码 | 数量 | 说明 |
|---------|------|------|
| C0415 (import-outside-toplevel) | 15+ | 导入语句在函数内部而非模块顶层 |
| E0401 (import-error) | 8+ | 无法导入模块 (ai_models, data_pipeline) |
| C0301 (line-too-long) | 5+ | 行超过 100 字符 |
| R0912/R0917 (too-many-branches/arguments) | 3+ | 函数复杂度过高 |
| W0612 (unused-variable) | 3+ | 未使用的变量 |
| R0801 (duplicate-code) | 3 | 重复代码 |
| W0407 (preferred-module) | 3 | 应使用别名导入 (如 np) |

---

## 改进点优先级排序

### 🔴 高优先级：修复模块导入问题（今日实施）

**当前问题：**
- `ai_fusion_strategy.py` 中多处导入 `ai_models.emotion_cycle_model` 和 `data_pipeline.storage.duckdb_manager` 失败
- 导入语句放在函数内部而非模块顶层，违反 Python 规范
- 导致 E0401 (import-error) 和 C0415 (import-outside-toplevel) 警告

**预期收益：**
- 消除 15+ 个 pylint 警告
- 提高代码可维护性和可读性
- 确保模块依赖关系清晰

**具体修改方案：**
1. 检查 `ai_models/emotion_cycle_model.py` 是否存在，若不存在则创建或修正导入路径
2. 检查 `data_pipeline/storage/duckdb_manager.py` 路径是否正确
3. 将所有函数内部的导入移到模块顶层
4. 使用 try/except ImportError 处理可选依赖

**可能的风险：**
- 循环依赖可能导致导入失败
- 需要验证修改后功能正常

**实施成本：** 低 (1-2 小时)
**风险等级：** 低

---

### 🟡 中优先级：简化复杂函数（本周内实施）

**当前问题：**
- `ai_fusion_strategy.py:107` 函数有 16 个分支 (限制 15) 和 6 个参数 (限制 5)
- 函数逻辑复杂，难以测试和维护
- 缺少文档字符串说明函数用途

**预期收益：**
- 降低认知复杂度
- 提高代码可测试性
- 符合 pylint 规范

**具体修改方案：**
1. 将长函数拆分为多个小函数（每个函数单一职责）
2. 使用数据类 (dataclass) 封装多个参数
3. 提取条件分支为独立的策略函数
4. 添加完整的文档字符串

**可能的风险：**
- 重构可能引入逻辑错误
- 需要充分测试验证

**实施成本：** 中 (3-4 小时)
**风险等级：** 中

---

### 🟢 低优先级：消除重复代码（下周计划）

**当前问题：**
- `mean_reversion.py`, `core.data_service`, `data_engine.connector_astock_duckdb` 中有重复的代码块
- 股票代码转换逻辑在多处重复
- DuckDB 连接函数重复定义

**预期收益：**
- 减少代码维护成本
- 提高代码复用率
- 降低 bug 风险

**具体修改方案：**
1. 提取公共代码到 `core/utils/symbol_utils.py`
2. 提取 DuckDB 连接到 `core/utils/db_utils.py`
3. 更新所有引用点使用新的工具函数

**可能的风险：**
- 需要确保所有调用点兼容
- 可能需要调整接口

**实施成本：** 中 (2-3 小时)
**风险等级：** 低

---

### 🔵 优化项：代码规范细节（持续进行）

**当前问题：**
- 部分文件使用 `import numpy` 而非 `import numpy as np`
- 少量行超过 100 字符
- 未使用的变量残留

**具体修改方案：**
1. 运行 `autopep8 --in-place` 自动修复格式问题
2. 手动修复长行（拆分或重构）
3. 删除未使用的变量

**实施成本：** 低 (30 分钟)
**风险等级：** 极低

---

## 今日实施计划

### 第一阶段：安全检查（5 分钟）
```bash
cd ./newhigh
git status
git add .
git commit -m "Backup before 2026-03-14 auto-improvement"
```

### 第二阶段：修复导入问题（60 分钟）
1. 检查并修复 `ai_models/emotion_cycle_model.py` 路径
2. 检查并修复 `data_pipeline/storage/duckdb_manager.py` 路径
3. 移动所有函数内导入到模块顶层
4. 运行 pylint 验证

### 第三阶段：代码格式化（30 分钟）
```bash
source .venv/bin/activate
autopep8 --in-place --aggressive strategy-engine/src/strategy_engine/ai_fusion_strategy.py
autopep8 --in-place --aggressive strategy-engine/src/strategies/daily_stock_analysis/*.py
```

### 第四阶段：验证测试（30 分钟）
```bash
python -m pytest strategy-engine/tests/ -v --tb=short
python -m pytest core/tests/ -v --tb=short
```

### 第五阶段：记录结果（15 分钟）
- 更新 `improvement_log.md`
- 若有成功经验，写入 `LEARNINGS.md`
- 若有失败，写入 `ERRORS.md`

---

## 成功标准

- [ ] pylint 评分达到 9.0/10 以上
- [ ] 消除所有 E0401 (import-error) 警告
- [ ] 减少 C0415 (import-outside-toplevel) 警告 80% 以上
- [ ] 所有核心测试通过
- [ ] 无破坏性更改

---

## 备注

- 若遇到无法立即解决的问题，记录到 `ERRORS.md` 并加入下次计划
- 优先保证功能正常，其次优化代码质量
- 所有修改必须有 git 备份
