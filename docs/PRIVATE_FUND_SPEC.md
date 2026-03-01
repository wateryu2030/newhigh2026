# 私募级版本说明（Private Fund Spec）

在生产级机构量化系统基础上，已扩展以下模块，支持**私募级风控与实盘扩展**。

---

## 一、Kelly 与波动率约束仓位

- **`backend/portfolio/kelly.py`**
  - `kelly_fraction(win_prob, win_loss_ratio, fraction)`：单标的 Kelly 比例，支持半凯利等保守系数。
  - `kelly_weights_from_returns(returns_dict, fraction, target_vol)`：多标的 Kelly 权重 + 目标波动率缩放。
  - `vol_target_scale(current_vol, target_vol)`：按目标波动率缩放总仓位。
- **`PortfolioOptimizer.kelly_weights()`**：组合优化器内调用 Kelly 权重接口。

---

## 二、私募级风控体系

- **VaR**（`backend/risk/var_engine.py`）
  - `var_historical(returns, confidence)`：历史法 VaR。
  - `var_covariance(returns, confidence)`：方差-协方差法（正态假设）。
  - `check_var_breach(current_pnl_pct, var_limit_pct)`：VaR 熔断检查。
- **集中度**（`backend/risk/concentration.py`）
  - `ConcentrationLimit`：单标的、前 3、前 10 权重上限；`check_weights` / `filter_orders`。
- **熔断器**（`backend/risk/circuit_breaker.py`）
  - `CircuitBreaker`：单日亏损、回撤、连续亏损天数触发熔断，冷却期禁止交易。
- **RiskEngine 扩展**
  - 集成 VaR 检查、集中度过滤、熔断；`check_var`、`trip_circuit`、`is_circuit_tripped`。

---

## 三、AI 择时模型（LSTM / Transformer 骨架）

- **`backend/ai/timing_model.py`**
  - `TimingModelBase`：`predict_regime(features)`、`predict_position_pct(features)`。
  - `RuleBasedTiming`：规则择时（均线），无深度学习依赖。
  - `load_lstm_timing(model_path)` / `load_transformer_timing(model_path)`：占位，可接 PyTorch/ONNX。
  - `get_timing_model(kind="rule"|"lstm"|"transformer", model_path)`：工厂入口。

---

## 四、强化学习仓位模型

- **`backend/ai/rl_position_model.py`**
  - `RLPositionModelBase`：`predict(state)` → 仓位比例 [0, 1]。
  - `RuleBasedPosition`：按回撤/波动缩仓规则。
  - `load_rl_position_model(model_path)`：占位，可接 rl_trading 或 SB3。
  - `get_rl_position_model(use_rl, model_path)`：工厂入口。
- **AIFundManager.get_position_scale(state)**：结合择时与 RL 仓位模型对总仓位做缩放。

---

## 五、QMT 实盘接入骨架

- **`backend/broker/qmt.py`**
  - `QMTBroker`：完整 `BrokerBase` 实现（connect / send_order / buy / sell / cancel_order / query_position / get_balance）。
  - 配置驱动：`qmt_path`、`account_id`、`timeout`；可从环境变量或 YAML 读取。
  - `create_qmt_broker(config)`：从配置创建实例。
- **`config/broker.example.yaml`**：券商配置示例（sim / qmt，active: sim）。

实盘接入时：实现 QMT 客户端调用（如 miniquant、xtquant），在 `send_order` / `cancel_order` / `query_position` / `get_balance` 中替换 TODO 逻辑。

---

## 六、使用与扩展建议

1. **仓位**：组合层可优先使用 `PortfolioOptimizer.kelly_weights()` 或 `kelly_weights_from_returns()`，再用 `vol_target_scale` 做总仓位约束。
2. **风控**：所有下单路径经 `RiskEngine.check()`；需 VaR/熔断时调用 `check_var`、`trip_circuit`。
3. **择时**：训练好 LSTM/Transformer 后，实现 `load_lstm_timing` / `load_transformer_timing`，在 `get_timing_model("lstm", path)` 中使用。
4. **RL 仓位**：与 `rl_trading` 或 SB3 策略对接后，实现 `load_rl_position_model`，并在 AI 基金经理或执行层调用 `get_rl_position_model(use_rl=True, path)` 与 `get_position_scale(state)`。
5. **QMT**：复制 `config/broker.example.yaml` 为 `config/broker.yaml`，填写 QMT 参数，将 `active` 设为 `qmt`，并在创建 Broker 时使用 `create_qmt_broker(config)`。

---

## 七、Cursor / OpenClaw 任务（可选）

若需自动化「私募级」扩展，可在任务列表中增加：

- 任务14：Kelly 仓位 + 波动率约束接入组合层。
- 任务15：私募级风控（VaR、集中度、熔断）接入 RiskEngine 与交易循环。
- 任务16：AI 择时模型接口与 LSTM/Transformer 占位实现。
- 任务17：RL 仓位模型接口与 rl_trading 对接。
- 任务18：QMT 配置与 Broker 工厂（config + create_qmt_broker）。

上述模块已按当前设计实现，可按需启用或替换为实际训练/实盘代码。
