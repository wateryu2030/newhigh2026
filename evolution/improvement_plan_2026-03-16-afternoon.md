# 量化平台改进计划 - 2026-03-16 (下午)

**执行时间:** 2026-03-16 16:20 (Asia/Shanghai)  
**Pylint 评分:** 9.47/10 (核心模块)  
**任务类型:** 每日自我进化任务 (cron)

---

## 📊 当前系统状态

### 核心模块健康度

| 模块 | Pylint 评分 | 问题数 | 状态 |
|------|------------|--------|------|
| core | 9.88/10 | ~5 | ✅ 优秀 |
| data-engine | 9.15/10 | ~50 | 🟡 良好 |
| strategy-engine | 9.75/10 | ~8 | ✅ 优秀 |
| **整体** | **9.47/10** | **~63** | ✅ 良好 |

### 问题最严重的 3 个文件

| 文件 | 问题数 | 主要问题 |
|------|--------|----------|
| `wechat_collector.py` | 34 | logging-fstring, redefined-outer-name, unused-import |
| `connector_astock_duckdb.py` | 10 | line-too-long, import-outside-toplevel, too-many-arguments |
| `ai_fusion_strategy.py` | 4 | line-too-long, too-many-positional-arguments |

### 上次计划完成情况 (2026-03-16 早间)

- [x] 修复 core/types.py 导入 (已确认代码正确，pylint 误报)
- [x] 安装 feedparser (已确认安装)
- [ ] 修复失效数据源选择器 (进行中，需分析实际 HTML)

---

## 🔴 高优先级改进

### 1. 修复 wechat_collector.py 代码质量问题

**问题:** 新添加的微信采集器有 34 个 pylint 问题

**主要问题分类:**
- W1203 (logging-fstring-interpolation): 15+ 处
- W0621 (redefined-outer-name): 7 处 (变量 `article` 重复定义)
- W0611 (unused-import): 4 处 (os, sys, Tuple, 未使用的导入)
- C0415 (import-outside-toplevel): 2 处
- W1309 (f-string-without-interpolation): 1 处
- W0612 (unused-variable): 1 处

**改进方案:**

```python
# 1. 移除未使用的导入
# 删除：import os, import sys, 以及 typing.Tuple

# 2. 修复 logging f-string → lazy % formatting
# 前：logger.info(f"处理文章：{title}")
# 后：logger.info("处理文章：%s", title)

# 3. 修复变量重定义问题
# 将内部循环的 article 变量重命名为 article_data 或 item

# 4. 修复顶层导入
# 将函数内的 time, duckdb 导入移至模块顶部（在 try/except 块内）
```

**预期收益:**
- pylint 问题数减少 34 个
- 代码质量评分提升至 9.6+/10
- 日志性能优化 (lazy evaluation)
- 消除潜在的变量作用域 bug

**风险:** 低 (纯代码规范修复，不改变功能)

**实施成本:** 低 (约 15-20 分钟)

---

### 2. 修复 connector_tushare.py 导入规范

**问题:** `connector_tushare.py:18` - 应使用 `import pandas as pd`

**当前代码:**
```python
import pandas
```

**改进方案:**
```python
import pandas as pd
# 并更新所有用法：pandas.DataFrame → pd.DataFrame
```

**预期收益:**
- 符合项目导入规范
- 与 data-engine 其他文件保持一致
- 消除 W0407 警告

**风险:** 低

**实施成本:** 低 (约 5 分钟)

---

### 3. 修复 connector_astock_duckdb.py 长行问题

**问题:** 4 处行超过 100 字符限制 (最长 226 字符)

**改进方案:**
- 使用 black 或 autopep8 自动格式化
- 手动拆分超长 SQL 语句

**预期收益:**
- 符合 PEP8 规范
- 提高代码可读性

**风险:** 低

**实施成本:** 低 (约 5 分钟)

---

## 🟡 中优先级改进

### 4. 优化 ai_fusion_strategy.py 函数参数

**问题:** `generate_signals` 方法有 6 个位置参数 (超过 5 个)

**改进方案:**
- 将部分参数改为关键字参数
- 或使用配置对象封装

**预期收益:**
- 提高 API 可读性
- 便于后续扩展

**风险:** 中 (需要检查调用方)

**实施成本:** 中 (约 20 分钟)

---

### 5. 修复 wechat_collector.py 变量作用域问题

**问题:** 多处 `article` 变量遮蔽外层作用域

**改进方案:**
- 将内部循环变量重命名为 `article_data`, `item`, 或 `record`
- 确保变量名清晰表达用途

**预期收益:**
- 消除 W0621 警告
- 提高代码可读性
- 避免潜在的 bug

**风险:** 低

**实施成本:** 低 (约 10 分钟)

---

## 🟢 低优先级改进

### 6. 添加 wechat_collector.py 文档字符串

**问题:** 部分公共方法缺少文档字符串

**改进方案:**
- 为 `fetch_article`, `fetch_album`, `save_to_db` 添加完整 docstring
- 包含参数说明、返回值、异常

**预期收益:**
- 提高代码可维护性
- 便于 IDE 自动补全

**风险:** 无

**实施成本:** 低 (约 10 分钟)

---

## 📋 执行计划

### 今日完成 (2026-03-16 下午)
- [x] 运行 pylint 静态分析
- [x] 识别问题最严重的文件
- [ ] 修复 wechat_collector.py (优先级 1)
- [ ] 修复 connector_tushare.py 导入 (优先级 2)
- [ ] 修复 connector_astock_duckdb.py 长行 (优先级 3)

### 本周剩余时间 (2026-03-17 ~ 2026-03-22)
- [ ] 优化 ai_fusion_strategy.py 参数 (优先级 4)
- [ ] 添加缺失的文档字符串 (优先级 6)
- [ ] 修复新闻采集器数据源选择器 (早间计划遗留)

---

## 📊 成功标准

### 功能指标
- [ ] pylint 评分 >9.6/10
- [ ] wechat_collector.py 问题数 <5
- [ ] 无严重警告 (E 级错误)

### 质量指标
- [ ] 所有测试通过
- [ ] 无破坏性更改
- [ ] 代码符合项目规范

---

## 📝 备注

**参考文档:**
- `evolution/improvement_log.md` - 历史改进记录
- `evolution/LEARNINGS.md` - 经验总结
- `scripts/run_quality_automation.sh` - 自动化脚本

**相关命令:**
```bash
# 自动格式化
autopep8 --in-place --aggressive data-engine/src/data_engine/wechat_collector.py

# 运行测试
pytest data-engine/tests/ -v

# 重新评估
pylint data-engine/src/data_engine/wechat_collector.py
```

---

**计划生成时间**: 2026-03-16 16:20  
**生成者**: OpenClaw 心跳任务 (cron:e101eb0f-d7ca-4e3b-b4b3-14365eacae44)  
**下次审查**: 2026-03-17 01:00
