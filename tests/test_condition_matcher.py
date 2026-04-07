"""Tests for condition matching and normalization (LFL-8)."""

from pathlib import Path

from logiclock.core import match_conditions, normalize_condition_expression


_GOLDEN_PATH = (
    Path(__file__).resolve().parent
    / "snapshots"
    / "condition_normalization_golden.txt"
)


def test_normalization_golden() -> None:
    lines = _GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
    for line in lines:
        raw, expected = line.split(" => ", maxsplit=1)
        assert normalize_condition_expression(raw) == expected


def test_missing_condition_has_suggestion() -> None:
    schema = ["user.is_premium", "user.balance > 100"]
    code = ["user.is_premium", "cart.total > 100"]
    result = match_conditions(schema, code)
    assert result.complete_match is False
    assert len(result.missing_schema_conditions) == 1
    miss = result.missing_schema_conditions[0]
    assert miss.schema_condition == "user.balance > 100"
    assert miss.suggested_code_condition == "cart.total > 100"


def test_partial_overlap_not_complete_match() -> None:
    schema = ["user.is_premium", "cart.total > 100", "country == 'US'"]
    code = ["user.is_premium", "100 < cart.total"]
    result = match_conditions(schema, code)
    assert result.complete_match is False
    assert set(result.matched_schema_conditions) == {
        "user.is_premium",
        "cart.total > 100",
    }
    assert [m.schema_condition for m in result.missing_schema_conditions] == [
        "country == 'US'",
    ]


def test_normalized_equivalent_comparison_matches() -> None:
    schema = ["user.balance > 100"]
    code = ["100 < user.balance"]
    result = match_conditions(schema, code)
    assert result.complete_match is True
