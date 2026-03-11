# meta-fund-manager

AI 基金经理大脑：选择策略、分配资金、监控表现、关闭差策略。

- select_strategies: 按 Alpha 分选策略上线
- allocate_capital: equal / alpha_weighted
- should_disable: 回撤或亏损超限则关闭
- monitor_performance: 批量检查并返回应关闭的 strategy_id 列表
