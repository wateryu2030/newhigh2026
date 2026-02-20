# 设计目标检查状态

## 数据同步情况 ✅

| 股票 | 合约代码 | 日线条数 |
|------|----------|----------|
| 600745 | 600745.XSHG | 1472 |
| 000001 | 000001.XSHE | 245 |

数据来源：`data/astock.db`（由 `database/sync_data.py` 同步）。

## Web 平台设计目标 ✅

- **策略下拉**：8 个策略可选（如 universal_ma_strategy、strategy_wentai_demo 等）。
- **股票代码选择**：下拉显示数据库中股票（600745、000001），支持输入自定义代码。
- **数据源**：可选「数据库」或「AKShare」。
- **运行回测**：前端调用 `/api/run_backtest`，后端使用 `run_backtest_db.py`（数据库数据源）或 `run_backtest.py`。

## 回测机制 ✅

- 命令行：`python run_backtest_db.py strategies/universal_ma_strategy.py 2024-01-01 2024-12-31` 可正常完成回测。
- Web 端选择「数据库」数据源并点击「运行回测」时，会调用上述脚本，可完成回测。

## 本次改进

1. **前端**：将策略代码编辑框的 `placeholder` 改为 HTML 实体（`&#10;`、`&quot;`），避免多行与引号导致浏览器报 `Invalid or unexpected token`。
2. **自检脚本**：新增 `scripts/check_design_goals.py`，可一键检查数据同步、Web 接口、回测是否达标。
3. **README**：补充「设计目标自检与浏览器测试」步骤，并说明回测请使用 `run_backtest_db.py`（避免 `run_file` 导入错误）。

## 浏览器自测步骤

1. 启动：`python web_platform.py`
2. 打开：http://127.0.0.1:5050
3. 确认策略下拉有 8 个策略、股票下拉有 2 只股票（或先同步更多）。
4. 选择策略（如「universal_ma_strategy.py」）、股票（如 600745.XSHG）、日期与「数据库」数据源，点击「运行回测」。
5. 在回测日志中查看输出与是否完成。

若控制台出现 `content.js` 等与扩展相关的报错，可忽略（来自浏览器扩展，非本平台页面脚本）。
