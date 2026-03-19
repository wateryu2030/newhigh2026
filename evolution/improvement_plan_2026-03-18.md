# 量化平台改进计划 - 2026-03-18

**执行时间:** 2026-03-18 16:15 (Asia/Shanghai)  
**Pylint 评分:** 9.60/10 (整体)  
**任务类型:** 每日自我进化任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)

---

## 📊 当前系统状态

### 核心模块健康度

| 模块 | Pylint 评分 | 问题数 | 状态 |
|------|------------|--------|------|
| core | 9.89/10 | ~2 | ✅ 优秀 |
| data-engine | 9.29/10 | ~15 | 🟡 良好 |
| strategy-engine | 8.82/10 | ~12 | 🟡 需改进 |
| daily_stock_analysis | 9.47/10 | ~11 | ✅ 良好 |

### 问题最严重的 3 个文件

| 文件 | 问题数 | 主要问题 |
|------|--------|----------|
| `strategy-engine/src/strategies/daily_stock_analysis/test_basic.py` | 11 | f-string-without-interpolation (6), import-outside-toplevel (2), redefined-outer-name (1), import-error (1) |
| `data-engine/src/data_engine/connector_astock_duckdb.py` | 9 | line-too-long (7), too-many-positional-arguments (1), too-many-branches (1) |
| `strategy-engine/src/strategies/daily_stock_analysis/main.py` | 7 | no-member (5), redefined-outer-name (2) |

### 上次计划完成情况 (2026-03-17)

- [x] 修复 daily_stock_analysis.main.py 语法错误 (已完成)
- [x] 修复 daily_stock_analysis.news_analyzer.py 未定义变量 (已完成)
- [x] 修复 daily_stock_analysis.ai_decision.py f-string 错误 (已完成)
- [x] 清理未使用的导入和变量 (已完成)
- [x] 优化代码结构 (no-else-return) (已完成)
- [ ] 修复 connector_astock_duckdb.py 超长 SQL (部分完成)
- [ ] 优化 ai_fusion_strategy.py 参数 (未完成)

---

## 🔴 高优先级改进 (今日完成)

### 1. 修复 test_basic.py f-string 警告

**问题:** 6 处 f-string 没有插值变量 (W1309)

**位置:**
- 第 61 行: `print(f"   ✅ 初始化成功")`
- 第 69 行: `print(f"   配置: {analyzer.config.name}")` (这个有插值，但可能格式不对)
- 第 86 行: `print(f"   ✅ 数据获取成功")`
- 第 99 行: `print(f"   ✅ AI分析成功")`
- 第 138 行: `print(f"   ✅ 单个股票分析成功")`

**改进方案:**
```python
# 移除不必要的 f 前缀
print("   ✅ 初始化成功")
print(f"   配置: {analyzer.config.name}")  # 保留 f 前缀，因为有插值
print("   ✅ 数据获取成功")
print("   ✅ AI分析成功")
print("   ✅ 单个股票分析成功")
```

**预期收益:**
- 消除 5 个 W1309 f-string-without-interpolation 警告
- 代码更简洁

**风险:** 无 (纯语法修复)

**实施成本:** 低 (5 分钟)

---

### 2. 修复 test_basic.py 导入位置问题

**问题:**
- 第 17 行: `import importlib.util` 不在模块顶部 (C0413)
- 第 119 行: `import traceback` 在函数内部 (C0415)
- 第 163 行: 导入错误和重新定义变量

**改进方案:**
```python
# 将所有导入移到模块顶部
import asyncio
import sys
import os
import importlib.util
import traceback

# 修复第 163 行导入
# 当前: from strategy_engine.strategies.daily_stock_analysis.config import DailyStockConfig
# 改为使用已导入的模块
```

**预期收益:**
- 消除 C0413 wrong-import-position 警告
- 消除 C0415 import-outside-toplevel 警告
- 消除 E0401 import-error 警告
- 消除 W0621 redefined-outer-name 警告

**风险:** 中 (需要确保导入路径正确)

**实施成本:** 中 (10 分钟)

---

### 3. 修复 connector_astock_duckdb.py 超长 SQL 语句

**问题:** 7 处行超过 100 字符限制 (最长 226 字符)

**位置:**
- 第 12 行: 111 字符
- 第 16 行: 103 字符
- 第 31 行: 105 字符
- 第 101 行: 108 字符
- 第 222 行: 226 字符 (SQL 语句)
- 第 225 行: 192 字符 (SQL 语句)
- 第 228 行: 188 字符 (SQL 语句)

**改进方案:**
```python
# 使用括号拆分超长 SQL 语句
# 例如:
sql = (
    "SELECT a.symbol, a.name, a.industry, b.close, b.volume "
    "FROM stock_basic a JOIN daily_quotes b ON a.symbol = b.symbol "
    "WHERE b.trade_date = %s AND b.close > %s"
)
```

**预期收益:**
- 消除 7 个 C0301 line-too-long 警告
- 提高 SQL 可读性
- 符合 PEP8 规范

**风险:** 低 (纯格式修改)

**实施成本:** 中 (15 分钟)

---

## 🟡 中优先级改进 (待实施)

### 4. 修复 main.py no-member 警告

**问题:** 5 处 E1101 no-member 警告

**位置:**
- 第 105 行: `analyzer.ai_decision_maker.analyze` (应为 `analyze_market_data`)
- 第 112 行: `analyzer.ai_decision_maker.generate_recommendations`
- 第 119 行: `analyzer.ai_decision_maker.generate_summary`
- 第 153 行: `analyzer.ai_decision_maker.generate_recommendations`
- 第 180 行: `analyzer.notification_sender.send_all`

**改进方案:**
- 检查 AIDecisionMaker 和 NotificationSender 类的实际方法名
- 更新调用以匹配实际方法名
- 或添加缺失的方法定义

**预期收益:**
- 消除 E1101 no-member 警告
- 修复可能的运行时错误

**风险:** 中 (需要检查实际实现)

**实施成本:** 中 (15 分钟)

---

### 5. 优化 connector_astock_duckdb.py 函数参数

**问题:** `_fetch_hist_df` 方法有 7 个位置参数 (超过 5 个)

**改进方案:**
```python
# 将部分参数改为关键字参数
def _fetch_hist_df(
    code: str,
    start_date: str,
    end_date: str,
    period: str = "daily",
    adjust: str = "qfq",
    limit: int = 1000,
    timeout: int = 30
):
```

**预期收益:**
- 消除 R0917 too-many-positional-arguments 警告
- 提高 API 可读性

**风险:** 中 (需要检查调用方)

**实施成本:** 中 (10 分钟)

---

## 🟢 低优先级改进

### 6. 清理未使用的导入

**问题:** config.py 中未使用的 `os` 导入

**改进方案:**
```python
# 移除未使用的导入
# from config.py: remove `import os`
```

**预期收益:**
- 消除 W0611 unused-import 警告
- 代码更简洁

**风险:** 无

**实施成本:** 低 (2 分钟)

---

### 7. 修复 notification.py 超长行

**问题:** 第 203 行: 112 字符

**改进方案:**
```python
# 拆分超长行
message = (
    f"股票 {stock_info.get('name', '未知')} ({symbol}) "
    f"当前价格: {current_price:.2f}, 涨跌幅: {pct_change:.2%}"
)
```

**预期收益:**
- 消除 C0301 line-too-long 警告
- 提高可读性

**风险:** 无

**实施成本:** 低 (3 分钟)

---

## 📋 执行计划

### 今日完成 (2026-03-18)
- [ ] 修复 test_basic.py f-string 警告 (优先级 1)
- [ ] 修复 test_basic.py 导入位置问题 (优先级 2)
- [ ] 修复 connector_astock_duckdb.py 超长 SQL (优先级 3)
- [ ] 修复 main.py no-member 警告 (优先级 4)
- [ ] 优化 connector_astock_duckdb.py 函数参数 (优先级 5)
- [ ] 清理未使用的导入 (优先级 6)
- [ ] 修复 notification.py 超长行 (优先级 7)

### 验证测试
- [ ] strategy-engine 测试：2/2 通过
- [ ] data-engine 测试：10/10 通过
- [ ] 运行完整集成测试

---

## 📊 成功标准

### 功能指标
- [ ] 无 f-string 错误 (W1309)
- [ ] 无导入位置错误 (C0413, C0415)
- [ ] 无超长行 (C0301)
- [ ] pylint 评分 >9.65/10 (当前 9.60)

### 质量指标
- [ ] 所有测试通过
- [ ] 无破坏性更改
- [ ] 代码符合项目规范

---

## 📝 备注

**参考文档:**
- `evolution/improvement_log.md` - 历史改进记录
- `evolution/LEARNINGS.md` - 经验总结
- `evolution/ERRORS.md` - 错误记录

**相关命令:**
```bash
# 运行质量检查
pylint strategy-engine/src/strategies/daily_stock_analysis/test_basic.py
pylint data-engine/src/data_engine/connector_astock_duckdb.py

# 运行测试
pytest strategy-engine/tests/ -v
pytest data-engine/tests/ -v
```

---

**计划生成时间**: 2026-03-18 16:15  
**生成者**: OpenClaw 心跳任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)  
**下次审查**: 2026-03-19 01:00