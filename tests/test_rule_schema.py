"""Tests for rule schema loading and validation."""

import json
from pathlib import Path

import pytest

from logiclock.core import (
    Rule,
    RuleSchemaError,
    load_rule_from_dict,
    load_rule_from_json_file,
)

# Example from product spec style: premium eligibility / discount rule.
PREMIUM_DISCOUNT_SPEC: dict = {
    "id": "premium_discount",
    "conditions": [
        "account.tier == 'premium'",
        "order.subtotal >= 100",
    ],
    "result": "eligible_for_loyalty_discount",
    "version": 1,
}


def test_valid_rule_loads_typed() -> None:
    rule = load_rule_from_dict(PREMIUM_DISCOUNT_SPEC.copy())
    assert isinstance(rule, Rule)
    assert rule.id == "premium_discount"
    assert rule.conditions == PREMIUM_DISCOUNT_SPEC["conditions"]
    assert rule.result == PREMIUM_DISCOUNT_SPEC["result"]
    assert rule.version == 1


def test_premium_discount_round_trip_dict() -> None:
    rule = load_rule_from_dict(PREMIUM_DISCOUNT_SPEC.copy())
    dumped = rule.model_dump(mode="python")
    assert dumped == PREMIUM_DISCOUNT_SPEC


def test_premium_discount_round_trip_json_file(tmp_path: Path) -> None:
    path = tmp_path / "premium_discount.json"
    path.write_text(json.dumps(PREMIUM_DISCOUNT_SPEC), encoding="utf-8")
    rule = load_rule_from_json_file(path)
    assert rule.id == "premium_discount"
    again = load_rule_from_dict(json.loads(path.read_text(encoding="utf-8")))
    assert again.model_dump(mode="python") == PREMIUM_DISCOUNT_SPEC


def test_version_optional_omitted() -> None:
    data = {
        "id": "no_version",
        "conditions": ["x"],
        "result": "y",
    }
    rule = load_rule_from_dict(data)
    assert rule.version is None


@pytest.mark.parametrize(
    "payload,matcher",
    [
        (
            {"conditions": ["a"], "result": "b"},
            lambda m: "id" in m.lower() and "premium" not in m,
        ),
        (
            {"id": "x", "result": "b"},
            lambda m: "conditions" in m.lower(),
        ),
        (
            {"id": "x", "conditions": ["a"]},
            lambda m: "result" in m.lower(),
        ),
        (
            {"id": "x", "conditions": [], "result": "r"},
            lambda m: "conditions" in m.lower()
            and ("empty" in m.lower() or "not be empty" in m.lower()),
        ),
        (
            {"id": "x", "conditions": ["a"], "result": "r", "version": 0},
            lambda m: "version" in m.lower(),
        ),
        (
            {"id": "x", "conditions": ["a"], "result": "r", "extra": 1},
            lambda m: "extra" in m.lower(),
        ),
    ],
)
def test_invalid_schema_raises_with_rule_id_when_present(
    payload: dict,
    matcher,
) -> None:
    with pytest.raises(RuleSchemaError) as excinfo:
        load_rule_from_dict(payload)
    msg = str(excinfo.value)
    assert "rule id:" in msg.lower()
    if "id" in payload and isinstance(payload["id"], str):
        assert payload["id"] in msg
    assert matcher(msg)


def test_invalid_schema_missing_id_message() -> None:
    with pytest.raises(RuleSchemaError) as excinfo:
        load_rule_from_dict({"conditions": ["a"], "result": "b"})
    msg = str(excinfo.value)
    assert "rule id:" in msg.lower()
    assert "missing" in msg.lower() or "id" in msg.lower()


def test_json_file_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuleSchemaError) as excinfo:
        load_rule_from_json_file(path)
    assert "invalid json" in str(excinfo.value).lower()


def test_json_file_not_object(tmp_path: Path) -> None:
    path = tmp_path / "arr.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(RuleSchemaError) as excinfo:
        load_rule_from_json_file(path)
    msg = str(excinfo.value).lower()
    assert "expected json object" in msg or "object" in msg
