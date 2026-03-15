# 学习记录

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