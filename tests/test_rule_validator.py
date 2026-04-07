"""Tests for metadata-level rule vs implementation validation (LFL-4)."""

import pytest

from logiclock.core import (
    ImplementationSpec,
    Rule,
    Severity,
    ValidationPolicy,
    findings_include_severity,
    implementation_spec_from_metadata,
    validate_implementation_vs_schema,
)
from logiclock.decorators import get_rule_metadata, logic_lock


def _schema_discount() -> Rule:
    return Rule(
        id="premium_discount",
        conditions=["user.is_premium", "cart.total > 100"],
        result="discount=10",
        version=1,
    )


def test_result_mismatch_emits_error_by_default() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        result_declared="discount=5",
        conditions_declared=["user.is_premium", "cart.total > 100"],
    )
    findings = validate_implementation_vs_schema(rule, impl)
    assert findings_include_severity(findings, Severity.ERROR)
    assert any(f.code == "RESULT_MISMATCH" for f in findings)
    assert "discount=5" in findings[0].message


def test_result_mismatch_can_be_warning_via_policy() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        result_declared="discount=5",
        conditions_declared=["user.is_premium", "cart.total > 100"],
    )
    policy = ValidationPolicy(result_mismatch=Severity.WARNING)
    findings = validate_implementation_vs_schema(rule, impl, policy)
    assert findings_include_severity(findings, Severity.WARNING)
    assert not findings_include_severity(findings, Severity.ERROR)
    assert findings[0].code == "RESULT_MISMATCH"


def test_empty_conditions_lists_all_schema_conditions_as_missing() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(rule_id=rule.id, conditions_declared=[])
    findings = validate_implementation_vs_schema(rule, impl)
    missing = [f for f in findings if f.code == "MISSING_SCHEMA_CONDITION"]
    assert len(missing) == len(rule.conditions)


def test_missing_schema_condition_emits_warning_by_default() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        result_declared="discount=10",
        conditions_declared=["cart.total > 100"],
    )
    findings = validate_implementation_vs_schema(rule, impl)
    assert findings_include_severity(findings, Severity.WARNING)
    assert any(
        f.code == "MISSING_SCHEMA_CONDITION" and "user.is_premium" in f.message
        for f in findings
    )


def test_missing_condition_with_suggestion_message() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        conditions_declared=["user.is_basic", "cart.total > 100"],
    )
    findings = validate_implementation_vs_schema(rule, impl)
    missing = [f for f in findings if f.code == "MISSING_SCHEMA_CONDITION"]
    assert len(missing) == 1
    assert "Closest implementation condition" in missing[0].message
    assert "user.is_basic" in missing[0].message


def test_missing_condition_can_be_error_via_policy() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        conditions_declared=["cart.total > 100"],
    )
    policy = ValidationPolicy(missing_schema_condition=Severity.ERROR)
    findings = validate_implementation_vs_schema(rule, impl, policy)
    assert findings_include_severity(findings, Severity.ERROR)


def test_conditions_not_provided_skips_subset_check() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        result_declared="discount=10",
        conditions_declared=None,
    )
    assert validate_implementation_vs_schema(rule, impl) == []


def test_rule_id_mismatch() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(rule_id="other", conditions_declared=[])
    findings = validate_implementation_vs_schema(rule, impl)
    assert any(f.code == "RULE_ID_MISMATCH" for f in findings)


def test_aligned_spec_no_findings() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        result_declared=rule.result,
        conditions_declared=list(rule.conditions),
    )
    assert validate_implementation_vs_schema(rule, impl) == []


def test_aligned_spec_with_normalized_conditions_no_findings() -> None:
    rule = _schema_discount()
    impl = ImplementationSpec(
        rule_id=rule.id,
        result_declared=rule.result,
        conditions_declared=["user.is_premium", "100 < cart.total"],
    )
    assert validate_implementation_vs_schema(rule, impl) == []


def test_implementation_spec_from_decorator_metadata() -> None:
    @logic_lock(
        "premium_discount",
        result="discount=5",
        conditions=["user.is_premium"],
    )
    def apply_discount() -> None:
        return None

    spec = implementation_spec_from_metadata(get_rule_metadata(apply_discount))
    assert spec.rule_id == "premium_discount"
    assert spec.result_declared == "discount=5"
    assert spec.conditions_declared == ["user.is_premium"]


def test_implementation_spec_conditions_key_must_be_list() -> None:
    with pytest.raises(TypeError, match="conditions"):
        implementation_spec_from_metadata(
            {"rule_id": "x", "conditions": "not-a-list"},
        )
