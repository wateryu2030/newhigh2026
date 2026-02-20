# 回测错误修复说明

## 问题描述

在 Web 平台运行回测时，出现错误：
```
AttributeError: 'NoneType' object has no attribute '__globals__'
```

错误发生在 `rqalpha/core/strategy_loader.py`，当策略文件中没有定义 `before_trading` 或 `after_trading` 函数时，`getattr` 返回 `None`，然后 `None` 被传递给 RQAlpha 的策略加载器，导致错误。

## 根本原因

在 `run_backtest_db.py` 中，代码使用了：
```python
result = run_func(
    config=config,
    init=strategy_module.init,
    handle_bar=strategy_module.handle_bar,
    before_trading=getattr(strategy_module, "before_trading", None),  # 可能返回 None
    after_trading=getattr(strategy_module, "after_trading", None),    # 可能返回 None
)
```

当策略文件没有 `before_trading` 或 `after_trading` 函数时，`getattr` 返回 `None`，然后 `None` 被添加到 `user_funcs` 字典中。RQAlpha 的策略加载器会遍历所有函数并尝试访问 `__globals__` 属性，导致错误。

## 修复方案

修改 `run_backtest_db.py`，只传递存在的函数（不传递 `None`）：

```python
# 构建 user_funcs，只包含存在的函数（不包含 None）
user_funcs = {
    "init": strategy_module.init,
    "handle_bar": strategy_module.handle_bar,
}
if hasattr(strategy_module, "before_trading") and strategy_module.before_trading is not None:
    user_funcs["before_trading"] = strategy_module.before_trading
if hasattr(strategy_module, "after_trading") and strategy_module.after_trading is not None:
    user_funcs["after_trading"] = strategy_module.after_trading

result = run_func(config=config, **user_funcs)
```

## 验证

修复后，以下测试均通过：

1. ✅ `buy_and_hold_akshare.py` 策略（无 `before_trading` 和 `after_trading`）可以正常回测
2. ✅ 临时文件生成和股票代码注入正常
3. ✅ Web 平台回测接口可以正常调用

## 影响范围

- **修复文件**：`run_backtest_db.py`
- **影响功能**：所有通过 `run_backtest_db.py` 运行的回测
- **向后兼容**：完全兼容，不影响已有策略

## 测试建议

在 Web 平台测试以下场景：

1. 使用 `buy_and_hold_akshare.py` 策略（无可选函数）
2. 使用 `universal_ma_strategy.py` 策略（有所有函数）
3. 使用其他策略文件，验证回测是否正常
