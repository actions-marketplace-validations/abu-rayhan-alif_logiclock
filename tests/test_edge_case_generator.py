"""Tests for boundary/value scenario generation (LFL-9)."""

from logiclock.core import (
    ScenarioGenerationConfig,
    generate_scenarios_from_conditions,
)


def test_fixture_rule_generates_scenario_dicts() -> None:
    conditions = ["user.is_premium", "user.balance > 100"]
    out = generate_scenarios_from_conditions(conditions)
    assert out.total_possible_combinations == 6
    assert out.truncated is False
    assert len(out.scenarios) == 6
    first = out.scenarios[0]
    assert "user.is_premium" in first
    assert "user.balance" in first
    balances = {row["user.balance"] for row in out.scenarios}
    assert balances == {99, 100, 101}
    flags = {row["user.is_premium"] for row in out.scenarios}
    assert flags == {True, False}


def test_cartesian_limit_is_enforced_and_reported() -> None:
    conditions = [
        "a > 10",
        "b > 20",
        "c > 30",
        "d > 40",
    ]  # 3^4=81 possible
    out = generate_scenarios_from_conditions(
        conditions,
        config=ScenarioGenerationConfig(max_combinations=20),
    )
    assert out.total_possible_combinations == 81
    assert len(out.scenarios) == 20
    assert out.truncated is True


def test_unsupported_condition_is_skipped_in_basic_generator() -> None:
    conditions = ["x in allowed_values", "user.is_premium"]
    out = generate_scenarios_from_conditions(conditions)
    assert out.total_possible_combinations == 2
    assert len(out.scenarios) == 2
    assert all("user.is_premium" in row for row in out.scenarios)
    assert all("x" not in row for row in out.scenarios)


def test_boolean_constant_is_not_numeric_boundary() -> None:
    """``True``/``False`` are ``int`` subclasses; do not use n±1 boundaries."""
    for expr in ("balance > True", "False < balance", "x == False"):
        out = generate_scenarios_from_conditions([expr])
        assert out.scenarios == ()
        assert out.total_possible_combinations == 0
