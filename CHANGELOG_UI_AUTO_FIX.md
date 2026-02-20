# UI 优化与自动补齐功能更新日志

## 更新内容

### 1. UI 优化：移除重复的策略选择

**问题**：
- 左侧有策略列表（可点击）
- 右侧有策略下拉框（也可选择）
- 两个选择控件容易引起歧义

**解决方案**：
- ✅ 移除右侧策略下拉框
- ✅ 改为只读输入框，显示"已选策略"
- ✅ 提示："请在左侧列表中选择策略"
- ✅ 点击左侧列表时，自动设置到右侧输入框
- ✅ 格式：`策略名称 (文件名.py)`
- ✅ 使用 `data-file` 属性保存实际文件名

**文件修改**：
- `web_platform.py`：HTML 模板和 JavaScript 逻辑

### 2. 自动补齐策略所需数据文件

**功能**：
- ✅ 回测前自动检查策略所需的数据文件
- ✅ 如果文件不存在或文件太小（<50字节），自动生成
- ✅ 如果用户选择了股票，确保该股票在策略的股票池中
- ✅ 在回测日志中显示补齐结果

**支持的策略**：

| 策略 | 所需数据文件 |
|------|------------|
| 行业轮动 (`strategy1_industry_rotation.py`) | `industry_stock_map.csv`, `industry_score.csv` |
| 动量+均值回归 (`strategy2_momentum_meanreversion.py`) | `tech_leader_stocks.csv`, `consume_leader_stocks.csv` |
| 财报超预期 (`strategy3_earnings_surprise.py`) | `earnings_events.csv` |
| ETF网格 (`strategy4_etf_grid.py`) | `etf_list.csv` |

**实现**：
- 新增 `database/auto_fix_strategy_data.py`：自动补齐模块
- 在 `web_platform.py` 的 `/api/run_backtest` 中集成
- 自动将用户选择的股票添加到对应股票池

### 3. 股票池自动添加

**功能**：
- ✅ 运行策略2（动量+均值回归）时，如果用户选择的股票不在股票池中，自动添加
- ✅ 从数据库获取股票名称（如果有）
- ✅ 避免覆盖已有的股票池数据

**示例**：
- 用户选择 `002701.XSHE`
- 系统自动将其添加到 `tech_leader_stocks.csv` 和 `consume_leader_stocks.csv`

## 使用方式

### UI 使用

1. **选择策略**：点击左侧策略列表中的任意策略
2. **查看已选**：右侧"已选策略"输入框会显示：`策略名称 (文件名.py)`
3. **配置回测**：选择股票、日期等参数
4. **运行回测**：点击"运行回测"按钮

### 自动补齐

无需手动操作，系统自动执行：
1. 选择策略和股票
2. 点击"运行回测"
3. 系统检查并补齐所需数据文件
4. 在回测日志中查看补齐结果

## 测试验证

### UI 测试

```bash
# 启动 Web 平台
python web_platform.py

# 在浏览器中：
# 1. 点击左侧策略列表，确认右侧"已选策略"正确显示
# 2. 确认不再有重复的策略选择控件
```

### 自动补齐测试

```bash
# 删除某个策略的数据文件
rm data/tech_leader_stocks.csv

# 选择策略2运行回测（通过 Web 平台）
# 确认文件自动生成

# 或使用命令行测试
python database/auto_fix_strategy_data.py
```

## 文件清单

### 新增文件

- `database/auto_fix_strategy_data.py` - 自动补齐模块
- `docs/UI_IMPROVEMENTS.md` - UI 优化说明
- `docs/STRATEGY_REQUIREMENTS.md` - 策略数据要求说明

### 修改文件

- `web_platform.py` - UI 优化和自动补齐集成
- `strategies/strategies_meta.json` - 策略说明（已存在）

## 向后兼容

- ✅ 完全向后兼容
- ✅ 不影响已有策略和数据文件
- ✅ 如果数据文件已存在，不会覆盖（除非文件损坏）

## 注意事项

1. **数据文件格式**：自动生成的文件使用 UTF-8-sig 编码，与现有格式一致
2. **股票池合并**：如果文件已存在，会合并新旧数据，避免覆盖
3. **错误处理**：如果自动补齐失败，会在日志中显示警告，但不阻止回测
