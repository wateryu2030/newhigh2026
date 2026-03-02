# AI 基金经理系统（Portfolio Brain）

## 架构

```
strategy_layer/  策略注册、策略指标
capital_layer/   风险预算、仓位优化、资金分配
risk_layer/      组合风险、回撤控制、市场状态
ai_layer/        AI 分配器、强化学习分配（占位）
execution_layer/ 订单路由
manager_engine   主引擎：再平衡
```

## 使用

### 1. 命令行

```bash
# 从策略池加载策略指标并执行再平衡，结果写 logs/YYYYMMDD_manager.json
python3 run_manager.py
```

### 2. API

- **POST /api/fund_manager/rebalance**  
  Body: `{ "capital": 1000000, "current_max_drawdown": 0 }`  
  返回: `allocation`, `orders`, `risk_scale`, `weights`

### 3. 前端

- 首屏「🧠 AI 基金经理再平衡」卡片，点击「执行再平衡」调用上述 API 并展示分配与订单。

## 风控规则（DrawdownControl）

- 最大回撤 ≥ 20% → 仓位缩放 0（空仓）
- 最大回撤 ≥ 15% → 按比例降仓
- 可扩展：连续亏损 N 天进入风险模式、波动率异常暂停交易

## OpenClaw 验证步骤

1. 启动平台（推荐用项目 venv）：
   ```bash
   cd /path/to/astock
   python3 -m venv .venv
   .venv/bin/pip install -r requirements-web.txt
   .venv/bin/python web_platform.py
   ```
   访问 http://127.0.0.1:5050
2. 打开浏览器：若未安装 OpenClaw，先执行  
   `curl -fsSL https://clawd.org.cn/install.sh | bash`（自动安装 Node.js 与依赖），然后  
   `openclaw browser --browser-profile openclaw open http://127.0.0.1:5050`
3. 快照：`openclaw browser --browser-profile openclaw snapshot`  
   确认首屏有「机构组合结果」「AI 推荐列表」「AI 基金经理再平衡」
4. 点击「执行再平衡」：在快照中找到对应 button ref，执行  
   `openclaw browser --browser-profile openclaw click <ref>`  
   或手动在浏览器中点击，确认结果区展示分配与订单。

## 自检（不启动 Web）

```bash
python3 scripts/verify_platform.py
```

通过则 ai_fund_manager、evolution、run_manager 可正常导入与运行。
