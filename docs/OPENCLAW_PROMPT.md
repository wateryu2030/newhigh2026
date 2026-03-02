# OpenClaw 自动执行提示词（机构级 A 股系统）

复制以下内容到 OpenClaw（或 Z.AI / 其他支持 OpenClaw 的自动执行环境）作为任务描述，用于自动执行机构级升级。

**环境准备（自动执行前）**：若本机未安装 OpenClaw，先执行一键安装（自动安装 Node.js 与依赖）：
```bash
curl -fsSL https://clawd.org.cn/install.sh | bash
```
安装完成后新开终端即可使用 `openclaw`。

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
# 前端（可选，若需独立前端开发）
cd frontend && npm install && npm run dev

# 后端主站（项目根目录）
python web_platform.py
```
或 `.venv/bin/python web_platform.py`、项目约定的后端入口（如 `python main.py`）。

**注意**：
- 不删除现有可用的回测、扫描、数据拉取逻辑。  
- 新模块与现有 `backend/ai`、`backend/trading`、`backend/execution` 通过接口或桥接复用。  
- 前端在现有 React 路由与 API client 基础上新增 chart/trading/portfolio/ai 页面与组件。

---

## 情绪+龙虎榜 自动执行（单次/每日）

若只需执行「情绪周期 + 龙虎榜」刷新并写入 JSON，使用以下任务描述（详见 `docs/EMOTION_LHB_AUTO_EXEC.md`）：

```
任务：执行情绪周期与龙虎榜每日刷新。
步骤：1) 进入项目根目录；2) 若 Web 已运行则 POST http://127.0.0.1:5050/api/emotion/refresh；否则执行 python scripts/run_emotion_lhb_daily.py；3) 验证 data/daily_emotion.json 与 data/dragon_lhb_pool.json 已更新。
成功标准：两文件存在且含 emotion_cycle、resonance_list。参考 docs/EMOTION_LHB_AUTO_EXEC.md
```

