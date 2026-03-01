# OpenClaw 自动执行提示词（机构级 A 股系统）

复制以下内容到 OpenClaw 作为任务描述，用于自动执行机构级升级。

---

你是顶级量化工程师。

**目标**：把项目升级为机构级 A 股交易系统。

**要求**：
1. 代码可运行  
2. 前后端联通  
3. 有示例数据或 mock  
4. 页面可操作交易（下单、撤单、仓位、资金）  
5. AI 可输出组合决策（策略权重、市场状态）  
6. 支持模拟交易  

**优先级**：
- **P0** 交易闭环（订单、仓位、资金、券商适配）
- **P1** 策略组合（龙头突破、趋势机构、Alpha 因子 + 组合优化）
- **P2** AI 基金经理（市场状态、策略权重、可解释）
- **P3** 图表系统（TradingView 级、指标、信号叠加）

**任务清单**：按 `docs/CURSOR_UPGRADE_TASKS.md` 中任务 1～13 顺序执行；目录与模块命名与 `.cursor/rules/INSTITUTIONAL_UPGRADE.md` 一致。

**完成后自动运行**：
```bash
npm install
npm run dev
```
```bash
python web_platform.py
```
或项目约定的后端入口（如 `python main.py`）。

**注意**：
- 不删除现有可用的回测、扫描、数据拉取逻辑。  
- 新模块与现有 `backend/ai`、`backend/trading`、`backend/execution` 通过接口或桥接复用。  
- 前端在现有 React 路由与 API client 基础上新增 chart/trading/portfolio/ai 页面与组件。
