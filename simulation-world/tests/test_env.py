from simulation_world import MarketSimEnv, make_env

def test_env_reset_step():
    env = MarketSimEnv(max_steps=5)
    obs, info = env.reset(seed=42)
    assert obs.shape == (6,)
    obs, reward, term, trunc, info = env.step(1)
    assert not term or env._step >= 5
