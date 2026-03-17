# 学习记录

## 2026-03-17

### 问题
1. **f-string 语法错误**：`duration:.2f` 错误地将格式说明符放在参数位置
2. **f-string 缺少 f 前缀**：`logger.error("...{e}")` 缺少 `f` 前缀，导致变量不插值
3. **未定义变量**：循环中使用 `topic` 但实际应使用 `topics[i % len(topics)]`
4. **未使用的导入和变量**：`Optional` 导入未使用，`timestamp`、`current_stock` 变量提取后未使用
5. **no-else-return 模式**：`if: return` 后的 `else` 不必要，增加代码嵌套

### 解决方案
1. **修复 f-string 格式说明符位置**
   - 错误：`logger.info("耗时： %s 秒", duration:.2f)`
   - 正确：`logger.info("耗时：%.2f 秒", duration)`
   - 或：`logger.info(f"耗时：{duration:.2f}秒")`

2. **统一使用 lazy % formatting**
   - 错误：`logger.error("失败：{e}")` (缺少 f 前缀)
   - 正确：`logger.error("失败：%s", e)` (与项目规范一致)
   - 日志模块的 % formatting 支持 lazy evaluation，性能更好

3. **修复未定义变量**
   - 错误：`f"对{topic}进行深入分析"` (topic 未定义)
   - 正确：`f"对{topics[i % len(topics)]}进行深入分析"`
   - 使用循环索引访问列表元素

4. **清理死代码**
   - 移除未使用的 `Optional` 导入
   - 移除提取但未使用的 `timestamp`、`current_stock` 变量
   - 保持代码简洁

5. **应用 no-else-return 模式**
   - 错误：
     ```python
     if response.text:
         return ai_text
     else:
         logger.error("...")
         return mock_response
     ```
   - 正确：
     ```python
     if response.text:
         return ai_text
     logger.error("...")
     return mock_response
     ```

### 效果
1. daily_stock_analysis 模块 pylint 评分：9.40 → 9.47/10 (+0.07)
2. 消除 E0001 Parsing failed 错误 (语法错误)
3. 消除 E0602 Undefined variable 错误
4. 消除 W1309 f-string-without-interpolation 警告
5. 所有 12 个测试用例通过 (strategy-engine 2/2, data-engine 10/10)

### 经验教训
1. **f-string 语法要准确**：格式说明符 `:.2f` 必须在花括号内 `{duration:.2f}`，不能放在参数位置
2. **日志格式化优先使用 %**：`logger.info("...", arg)` 支持 lazy evaluation，比 f-string 性能更好
3. **循环变量要准确**：在循环中使用列表元素时，确保使用正确的索引表达式
4. **及时清理死代码**：未使用的导入和变量不仅产生警告，还会误导阅读代码的人
5. **no-else-return 提高可读性**：提前返回后不需要 else，直接写后续逻辑更清晰

### 常见 f-string 错误模式
```python
# 错误 1: 格式说明符位置错误
logger.info("耗时： %s 秒", duration:.2f)  # SyntaxError
# 正确:
logger.info("耗时：%.2f 秒", duration)
logger.info(f"耗时：{duration:.2f}秒")

# 错误 2: 缺少 f 前缀
logger.error("错误：{e}")  # 输出字面量 "{e}"
# 正确:
logger.error(f"错误：{e}")
logger.error("错误：%s", e)  # 推荐 (lazy evaluation)

# 错误 3: getLogger 使用 f-string 无插值
logger = logging.getLogger(f"module.name")  # W1309
# 正确:
logger = logging.getLogger("module.name")
```

### 代码审查检查清单
- [ ] f-string 是否有 f 前缀？
- [ ] 格式说明符是否在花括号内？
- [ ] 日志是否使用 lazy % formatting？
- [ ] 循环变量是否正确定义？
- [ ] 是否有未使用的导入或变量？
- [ ] `if: return` 后是否有不必要的 `else`？

---

## 2026-03-15

### 问题
1. **嵌套过深**：`ai_fusion_strategy.py` 的 `generate_signals` 方法有 6 层嵌套，难以阅读和维护
2. **导入规范不统一**：10 个文件使用 `import datetime` 而非 `import datetime as dt`
3. **变量命名冲突**：局部变量 `dt` 和 `ts` 遮蔽模块名，导致混淆和潜在 bug
4. **OHLCV 构造函数误用**：传递不存在的参数，缺少必需参数

### 解决方案
1. **提取辅助方法减少嵌套**
   - 将条件分支逻辑提取到独立方法：`_get_candidate_codes_bullish`, `_get_candidate_codes_normal`
   - 使用提前返回（early return）替代深层嵌套
   - 嵌套层级从 6 层降至 3 层

2. **统一导入别名**
   - 批量修改：`from datetime import datetime, timezone` → `import datetime as dt`
   - 更新所有用法：`datetime.now()` → `dt.datetime.now()`, `timezone.utc` → `dt.timezone.utc`
   - 使用 `dt.datetime.strptime` 替代 `datetime.strptime`

3. **避免变量命名冲突**
   - 局部变量不使用模块别名（避免 `dt = ...`, `ts = ...`）
   - 使用描述性名称：`date_val`, `ts_utc`, `dt_obj`

4. **修复构造函数调用**
   - 检查 dataclass 定义，确认必需参数和可选参数
   - 移除不存在的参数，添加缺失参数
   - 使用 `_normalize_symbol` 确保 symbol 格式正确

### 效果
1. pylint 评分：9.33 → 9.60/10 (+0.28)
2. 嵌套警告消除（R1702）
3. 所有 14 个测试用例通过
4. 代码可读性显著提高

### 经验教训
1. **嵌套是代码复杂度的信号**：超过 5 层嵌套应该考虑重构，提取辅助方法是有效手段
2. **导入规范要统一**：量化行业惯例是 `dt`, `pd`, `np`，统一规范提高代码一致性
3. **变量命名要避免遮蔽**：局部变量不要与模块名、导入名冲突，使用描述性名称
4. **测试是重构的安全网**：每次修改后运行测试，确保功能不受影响
5. **pylint 配置很重要**：`.pylintrc` 中的 `preferred-modules` 配置可以强制导入规范

### 重构模式
```python
# 重构前：深层嵌套
def generate_signals(...):
    if state == "主升":
        if DUCKDB_MANAGER_AVAILABLE:
            try:
                if db_path and os.path.isfile(db_path):
                    # ... 更多嵌套

# 重构后：提取方法 + 提前返回
def generate_signals(...):
    if state == "主升":
        candidate_codes = self._get_candidate_codes_bullish(hotmoney)
    else:
        candidate_codes = self._get_candidate_codes_normal(hotmoney)

def _get_candidate_codes_bullish(self, hotmoney: list) -> List[str]:
    if not DUCKDB_MANAGER_AVAILABLE:
        return [c for c in candidate_codes if c]
    # ... 扁平化逻辑
```

---

## 2026-03-12

### 问题
量化平台代码存在以下常见问题：
1. 尾随空格（trailing whitespace） - 特别是在数据连接器文件中
2. 导入顺序混乱 - 标准库、第三方库、本地模块混合
3. 缺少文档字符串 - 模块、类、函数缺少说明
4. 异常处理过于宽泛 - 使用 `except Exception:` 而不是具体异常类型

### 解决方案
1. **使用自动化工具**：`autopep8` 可以自动修复大多数代码规范问题
2. **分阶段改进**：先修复简单问题（格式化），再处理复杂问题（重构）
3. **安全第一**：修改前确保版本控制备份

### 效果
1. 代码可读性显著提高
2. 符合Python PEP8规范
3. 测试通过率保持100%
4. 为后续重构奠定基础

### 经验教训
1. **自动化工具的价值**：手动修复代码规范问题耗时且容易出错，自动化工具效率更高
2. **渐进式改进**：先解决简单问题，再处理复杂重构，降低风险
3. **测试保障**：每次修改后运行测试，确保功能不受影响
4. **文档记录**：详细记录修改内容和结果，便于追踪和复盘

---

## 2026-03-14

### 问题
`ai_fusion_strategy.py` 存在严重的导入问题：
1. 所有导入语句都在函数内部（违反 Python 规范）
2. 导致 15+ 个 C0415 (import-outside-toplevel) 警告
3. 导致 8+ 个 E0401 (import-error) 警告（模块路径问题）
4. pylint 评分仅 6.27/10

### 解决方案
1. **模块级导入**：将所有导入移至文件顶部
2. **可选依赖处理**：使用 try/except ImportError + 标志变量
   ```python
   try:
       from ai_models.emotion_cycle_model import EmotionCycleModel
       EMOTION_MODEL_AVAILABLE = True
   except ImportError:
       EmotionCycleModel = None
       EMOTION_MODEL_AVAILABLE = False
   ```
3. **优雅降级**：在函数开始时检查标志变量，不可用时返回默认值
4. **自动格式化**：使用 autopep8 修复格式问题

### 效果
1. pylint 评分：6.27 → 9.75/10 (+55.8%)
2. 消除 23+ 个导入相关警告
3. 依赖关系更清晰，启动时即可发现导入错误
4. 所有测试通过，功能正常

### 经验教训
1. **导入位置的重要性**：模块级导入是 Python 最佳实践，便于静态分析和依赖追踪
2. **可选依赖模式**：try/except + 标志变量是处理可选依赖的标准模式
3. **早期错误检测**：导入错误在模块加载时即可发现，而非运行时
4. **重构收益**：即使是大改动，只要有测试保障，也可以安全进行