from reel_gen.llm.cost import RATES, cost_for_llm_usage, cost_for_units


def test_cost_for_llm_usage_with_known_model():
    cost = cost_for_llm_usage(
        model="anthropic/claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_input_tokens=0,
    )
    expected = RATES["anthropic/claude-sonnet-4-6"]["input_per_mtok"]
    assert abs(cost - expected) < 1e-6


def test_cost_for_llm_usage_unknown_model_returns_none():
    assert cost_for_llm_usage(model="some/unknown", input_tokens=1000, output_tokens=0) is None


def test_cost_for_units_image():
    c = cost_for_units(provider="replicate", unit_label="images", units=2)
    assert abs(c - 0.006) < 1e-6
