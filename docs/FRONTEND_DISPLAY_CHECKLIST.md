# 前端显示问题排查清单（本项目的实际情况）

本项目**不是** React + Vite，而是 **Flask + 单页 HTML + static/app.js**（原生 JS + ECharts）。以下按概率从高到低排查「改动在前端没显示」的原因。

---

## 1. 决策驾驶舱 / 回测结果区不显示（最常见）

**现象**：运行回测后只有日志，没有「回测结果」卡片或「决策驾驶舱」区块。

**原因**：决策驾驶舱的显示依赖接口返回的 `result.kline` 或 `result.curve`（及可选 `result.holdCurve`）。  
若后端返回的 `result` 里没有这些字段或为空，前端会隐藏驾驶舱（现已改为显示提示文案）。

**排查**：
- 使用**左侧插件策略**（MA 均线、RSI、MACD、Breakout、波段新高）运行回测，这些走 `run_backtest_plugins.py`，会返回完整 `kline`、`curve`、`holdCurve`。
- 若使用「策略文件」（如某 .py），回测走 `run_backtest_db.py` 子进程，需确认其写出的 `output/last_backtest_result.json` 中是否包含 `kline`、`curve`、`holdCurve`。
- 浏览器 F12 → Network → 查看 `/api/run_backtest` 响应里的 `result` 是否含上述字段。

**本次已做修改**：
- 当无 kline/curve 时，决策驾驶舱区块仍会显示，并提示「请使用插件策略运行回测」。
- 仅有 `curve` 无 `holdCurve` 时，也会绘制「策略净值」曲线（单线）。

---

## 2. 后端接口未挂到前端

**现象**：新增了 API（如机构组合、AI 预测），但页面上没有入口。

**原因**：本系统主页面是 `web_platform.py` 里内联的 `HTML_TEMPLATE`，所有交互在 `static/app.js` 中。新增 API 若没有在 HTML 里加按钮/表单，或在 app.js 里加 `fetch` 调用，前端就不会用到。

**排查**：
- 在 `web_platform.py` 里搜索是否渲染了对应按钮/区块。
- 在 `static/app.js` 里搜索是否有 `fetch('/api/xxx')` 或对应点击逻辑。

**说明**：strategies_pro、AI 选股、机构组合引擎等目前主要是**命令行/脚本**（如 `run_strategy_demo.py`、`train_ai_model.py`、`engine`），未接入当前 Web 页面的，属于「未挂到前端」，不是 bug。若要在页面上用，需要在 HTML 中加入口并在 app.js 中调用对应 API。

---

## 3. 缓存 / 未刷新

**现象**：改了 `static/app.js` 或模板，页面仍像旧版。

**处理**：
- 模板里已对 app.js 使用 `?v={{ version }}`（版本为时间戳），理论上会绕过缓存；若未生效可强刷：Ctrl+Shift+R 或 Cmd+Shift+R。
- 若改了 `web_platform.py` 的 HTML_TEMPLATE，需**重启 Flask 服务**（`python web_platform.py`）后刷新页面。

---

## 4. 路径与静态资源

**说明**：本项目没有 `@/` 这种路径别名，也没有 Vite/React。静态资源是 Flask 的 `static_folder`，脚本引用为 `/static/app.js`。只要不改 Flask 的 static 配置，一般不会有「路径错导致不显示」的问题。

---

## 5. 控制台报错导致整块不渲染

**现象**：回测成功但结果区空白。

**排查**：F12 → Console，看是否有红色报错（如 `Cannot read property of undefined`、`map is not a function`）。若有，会阻止后续 JS 执行，结果区或驾驶舱可能不渲染。根据报错行号在 `static/app.js` 里对 `result` 做空值判断或兼容。

---

## 6. 分支/文件是否改对

若用 Git：确认当前分支和当前打开的文件就是你在改的那份（例如不是改的 dev 却在看 main 启动的页面）。

---

## 总结（结合本项目）

| 情况                     | 可能性 | 建议 |
|--------------------------|--------|------|
| 决策驾驶舱不显示         | 高     | 用插件策略回测；看接口是否返回 kline/curve；已加「无数据」提示与单曲线支持 |
| 新功能（机构/AI）页面上没有 | 高     | 属未接入前端，需在 HTML + app.js 中加入口与请求 |
| 改完 JS/模板没变化       | 中     | 强刷、重启 Flask |
| 控制台报错导致空白       | 中     | F12 看 Console，修 result 空值或类型 |

如需把「机构组合」或「AI 推荐」做到当前 Web 页面上，需要：在 `web_platform.py` 的 HTML 里增加对应区块与按钮，并在 `static/app.js` 里增加调用 `/api/xxx` 和渲染逻辑。
