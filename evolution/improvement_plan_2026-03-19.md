# 量化平台改进计划 - 2026-03-19

**执行时间:** 2026-03-19 16:40 (Asia/Shanghai)  
**Pylint 评分:** 9.52-9.89/10 (各模块分散)  
**任务类型:** 每日自我进化任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)

---

## 📊 当前系统状态

### 核心模块健康度

| 模块 | Pylint 评分 | 主要问题 | 状态 |
|------|------------|----------|------|
| core | 9.89/10 | 2 issues (import outside toplevel, unused import) | ✅ 优秀 |
| data-engine | 9.71/10 | line-too-long (8), positional args (7), duplicate code | 🟡 良好 |
| strategy-engine | 9.52/10 | no-member (6), f-string (3), import issues | 🟡 需改进 |

### 近期趋势 (对比 2026-03-18)

| 模块 | 3-18 评分 | 3-19 评分 | 变化 |
|------|-----------|-----------|------|
| core | 9.89 | 9.89 | ➡️ 稳定 |
| data-engine | 9.71 | 9.71 | ➡️ 稳定 |
| strategy-engine | 8.82 | 9.52 | ⬆️ +0.70 |

**结论:** 3-18 的修复大幅提升了 strategy-engine (-0.39 → +0.70)，但 data-engine 仍有长行和重复代码问题。

### 新问题总结

**高频问题类别:**
1. **C0301 line-too-long** (8处) - SQL语句、长字符串、多参数函数
2. **R0917 too-many-positional-arguments** (7处) - 函数参数超过5个
3. **E1101 no-member** (6处) - AI模块方法名不匹配
4. **C0415 import-outside-toplevel** (5处) - 懒加载设计 vs pylint规范
5. **重复代码** (R0801) - akshare/tushare 共享函数

---

## 🔴 高优先级改进 (今日完成)

### 1. 修复 daily_stock_analysis/main.py 的 no-member 警告

**问题:** 6 处 E1101 no-member 警告
```
main.py:105: AIDecisionMaker 无 'analyze' 方法
main.py:112: AIDecisionMaker 无 'generate_recommendations' 方法
main.py:119: AIDecisionMaker 无 'generate_summary' 方法
main.py:153: AIDecisionMaker 无 'generate_recommendations' 方法
main.py:180: NotificationSender 无 'send_all' 方法
```

**根因:** 
- `AIDecisionMaker` 类的方法名是 `analyze_market_data`, `generate_recommendations_v2`, `generate_summary_v2` (实际定义)
- `NotificationSender` 的方法可能是 `send` 而非 `send_all`

**改进方案:**
```python
# main.py - 修正方法调用
# line 105: analyzer.ai_decision_maker.analyze
# 改为: analyzer.ai_decision_maker.analyze_market_data(data)

# line 112/153: analyzer.ai_decision_maker.generate_recommendations
# 改为: analyzer.ai_decision_maker.generate_recommendations_v2()

# line 119: analyzer.ai_decision_maker.generate_summary
# 改为: analyzer.ai_decision_maker.generate_summary_v2()

# line 180: analyzer.notification_sender.send_all
# 改为: analyzer.notification_sender.send() 或检查实际方法名
```

**预期收益:**
- 消除 6 个 E1101 警告
- 修复潜在的运行时 AttributeError
- 提高代码可维护性

**风险:** 中 (需验证调用方与定义的一致性)

**实施成本:** 中 (15 分钟)

---

### 2. 修复 daily_stock_analysis/test_basic.py 的导入问题

**问题:** 
```
test_basic.py:160: C0415 import outside toplevel
test_basic.py:160: E0401 import-error (strategy_engine.strategies.daily_stock_analysis)
test_basic.py:160: E0611 no-name-in-module (no 'strategies' in strategy_engine)
```

**根因:** 
- `from strategy_engine.strategies.daily_stock_analysis.config import DailyStockConfig` 路径错误
- 正确路径应为 `strategy_engine.strategies.daily_stock_analysis.config`

**改进方案:**
```python
# test_basic.py - 修正导入
# line 160: from strategy_engine.strategies.daily_stock_analysis.config import DailyStockConfig
# 改为:
from strategy_engine.strategies.daily_stock_analysis import config

# 或将 import 移至模块顶部 (line 17-20)
```

**预期收益:**
- 消除 C0415, E0401, E0611 警告
- 提高测试模块可读性

**风险:** 低 (纯路径修正)

**实施成本:** 低 (5 分钟)

---

### 3. 统一 akshare/tushare 数据源重复代码

**问题:**
```
R0801: Similar lines in 2 files (connector_akshare.py vs connector_tushare.py)
- get_blacklist_stock_list() 共享逻辑 (split(".", maxsplit=1)[:0])
- _to_utc() 时间转换重复
```

**改进方案:**
```python
# strategy-engine/src/strategies/daily_stock_analysis/common_utils.py (新建)
def format_stock_code(code: str) -> str:
    """统一股票代码格式化逻辑"""
    code = str(code).strip().split(".", maxsplit=1)[0]
    if not code:
        return code
    if code.startswith(("4", "8", "9")) or len(code) == 8:
        return f"{code}.BSE"
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def to_utc(dt_obj: dt.datetime) -> dt.datetime:
    """统一时间转换逻辑"""
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
    return dt_obj
```

**预期收益:**
- 消除 R0801 重复代码警告
- 降低未来维护成本 (一处修改,全局生效)
- 提高代码一致性

**风险:** 低 (纯抽象提取)

**实施成本:** 中 (10 分钟)

---

## 🟡 中优先级改进 (待排期)

### 4. 拆分超长行 (connector_astock_duckdb.py)

**问题:** 8 处 C0301, 最长 226 字符
```
line 12/16/31/101: SQL 查询
line 236/239/242: 超长 SQL 语句 (226/192/188 字符)
```

**改进方案:**
```python
# 拆分长 SQL 列表
sql = (
    "SELECT stock_basic.symbol, stock_basic.name, stock_basic.industry, "
    "daily_quotes.close, daily_quotes.volume, daily_quotes.amount "
    "FROM stock_basic "
    "JOIN daily_quotes ON stock_basic.symbol = daily_quotes.symbol "
    "WHERE daily_quotes.trade_date = %s "
    "AND daily_quotes.close > %s "
    "ORDER BY daily_quotes.volume DESC "
    "LIMIT 100"
)
```

**预期收益:**
- 消除 8 个 C0301 警告
- 提高 SQL 可读性

**风险:** 低

**实施成本:** 中 (15 分钟)

---

### 5. 减少函数参数数量 (connector_astock_duckdb.py, data_pipeline.py)

**问题:** R0917 too-many-positional-arguments (7/5)
```
data_pipeline.py:53/91: _fetch_hist_df 7 个位置参数
connector_astock_duckdb.py:53: 同样问题
```

**改进方案:**
```python
# 方案 A: 使用配置对象
@dataclass
class FetchConfig:
    code: str
    start_date: str
    end_date: str
    period: str = "daily"
    adjust: str = "qfq"
    limit: int = 1000
    timeout: int = 30

def _fetch_hist_df(config: FetchConfig) -> pd.DataFrame:
    ...

# 方案 B: 将后置参数改为关键字参数 (调用方修改)
def _fetch_hist_df(code, start_date, end_date, period="daily", adjust="qfq", limit=1000, timeout=30):
    ...
```

**预期收益:**
- 消除 R0917 警告
- 提高 API 可读性

**风险:** 中 (需检查调用方)

**实施成本:** 中 (15 分钟)

---

### 6. 优化 ai_fusion_strategy.py 的 long line + seq-lock

**问题:**
```
line 248: C0301 line-too-long (101/100)
line 134: R0917 too-many-positional-arguments (6/5)
line 191/220: W1404 implicit string concatenation
```

**改进方案:**
```python
# 拆分超长行
message = (
    f"Running backtest for {strategy_id} on {symbol} "
    f"from {start_date} to {end_date} "
    f"with {n_test_days} test days"
)
```

**预期收益:**
- 符合代码规范

**风险:** 低

**实施成本:** 低 (5 分钟)

---

## 🟢 低优先级改进 (可选)

### 7. 修复 connector_astock_duckdb.py 的 too-many-branches

**问题:** R0912 too-many-branches (16/15) - line 53

**改进方案:** 
- 使用工厂模式替代多个 if/elif 分支
- 提取 `_get_quote_type()` 辅助函数

**风险:** 中 (涉及核心逻辑)

---

### 8. 消除 unused import 警告

**问题:**
```
core/src/core/data_service/strategy_service.py:5: W0611 Unused List
data-engine/src/data_engine/connector_tushare.py:12: W0611 Unused Dict
data-engine/src/data_engine/connector_astock_duckdb.py:6: W0611 Unused os
```

**改进方案:** 简单移除

**风险:** 无

**实施成本:** 低 (2 分钟)

---

## 📋 执行计划 (2026-03-19)

### 今日优先级 1-3 (约 35 分钟)
- [ ] P1: 修复 daily_stock_analysis/main.py no-member 警告
- [ ] P2: 修复 daily_stock_analysis/test_basic.py import 路径
- [ ] P3: 提取 akshare/tushare 重复代码

### 今日优先级 4-6 (约 35 分钟, 可选)
- [ ] P4: 拆分 connector_astock_duckdb.py 超长行
- [ ] P5: 减少 _fetch_hist_df 参数数量
- [ ] P6: 优化 ai_fusion_strategy.py 长行

### 验证测试
- [ ] `pytest core/tests/ -v` - 全部通过
- [ ] `pytest data-engine/tests/ -v` - 全部通过
- [ ] `pytest strategy-engine/tests/ -v` - 全部通过
- [ ] `pylint core/ data-engine/ strategy-engine/` - 评分 >9.60

---

## 📊 成功标准

### 功能指标
- [ ] pylint 总评分 >9.65/10 (当前 9.52-9.89)
- [ ] 无 E1101 no-member 警告
- [ ] 无 C0415 import-outside-toplevel (核心模块)
- [ ] 无 R0801 重复代码 (akshare/tushare)

### 质量指标
- [ ] 所有测试通过 (pytest -q)
- [ ] 无破坏性更改 (git diff 确认)
- [ ] 代码符合 PEP8 + 项目规范

---

## 📝 备注

**参考文档:**
- `evolution/improvement_log.md` - 历史改进记录
- `evolution/improvement_plan_2026-03-18.md` - 上轮计划
- `evolution/LEARNINGS.md` - 经验总结
- `evolution/ERRORS.md` - 错误记录

**最近完成项 (2026-03-18):**
- ✅ 修复 daily_stock_analysis.main.py 语法错误
- ✅ 修复 daily_stock_analysis.news_analyzer.py 未定义变量
- ✅ 修复 daily_stock_analysis.ai_decision.py f-string 错误

**本次改进重点:**
1. **策略模块方法名不匹配** (P1) - 可能导致运行时错误,优先级最高
2. **测试模块导入路径** (P2) - 影响测试可维护性
3. **重复代码清理** (P3) - 长期可维护性收益高

---

**计划生成时间**: 2026-03-19 16:40  
**生成者**: OpenClaw 心跳任务 (cron:17633133-2461-4649-8b9c-6509ceb5ef6a)  
**下次审查**: 2026-03-20 01:00
