# simulation-world

市场模拟环境，用于 RL 训练（PPO、SAC）。

- reset(): 重置环境，返回 (obs, info)
- step(action): action -1/0/1 → (obs, reward, terminated, truncated, info)
- reward_type: returns | pnl
