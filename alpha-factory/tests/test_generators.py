from alpha_factory import generate_random_combination, generate_population

def test_generate_random_combination():
    c = generate_random_combination()
    assert "strategy_type" in c
    assert "params" in c
    assert c["strategy_type"] in ("trend_following", "mean_reversion", "breakout")

def test_generate_population():
    pop = generate_population(10)
    assert len(pop) == 10
