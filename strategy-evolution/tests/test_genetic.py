from strategy_evolution import select_elite, crossover, mutate, evolve_population


def test_select_elite():
    scored = [({"id": i}, 0.1 * i) for i in range(20)]
    elite = select_elite(scored, elite_size=5)
    assert len(elite) == 5


def test_crossover():
    a = {"strategy_type": "trend_following", "params": {"fast_period": 10}, "indicators": ["rsi"]}
    b = {"strategy_type": "mean_reversion", "params": {"rsi_period": 14}, "indicators": ["macd"]}
    c = crossover(a, b)
    assert "strategy_type" in c and "params" in c


def test_evolve_population():
    scored = [
        (
            {
                "strategy_type": "trend_following",
                "params": {"fast_period": 10},
                "indicators": ["rsi"],
                "timeframe": "1h",
            },
            0.5 + i * 0.01,
        )
        for i in range(50)
    ]
    new_pop = evolve_population(scored, population_size=100, elite_size=10, mutation_rate=0.2)
    assert len(new_pop) == 100
