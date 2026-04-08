"""Tests for declared-result conflict detection (LFL-5)."""

from logiclock.core import (
    DeclaredResultConflict,
    OverlappingPredicateConflict,
    clear_rule_usage_sites,
    detect_declared_result_conflicts,
    detect_overlapping_predicate_conflicts,
    format_declared_result_conflict,
    format_overlapping_predicate_conflict,
)
from logiclock.decorators import logic_lock


def test_two_sites_same_rule_different_results_yields_conflict() -> None:
    clear_rule_usage_sites()

    @logic_lock("premium_discount", result="discount=10")
    def apply_a() -> None:
        return None

    @logic_lock("premium_discount", result="discount=5")
    def apply_b() -> None:
        return None

    conflicts = detect_declared_result_conflicts()
    assert len(conflicts) == 1
    c = conflicts[0]
    assert isinstance(c, DeclaredResultConflict)
    assert c.rule_id == "premium_discount"
    assert set(c.distinct_results) == {"discount=10", "discount=5"}
    msg = format_declared_result_conflict(c)
    assert "premium_discount" in msg
    assert "discount=10" in msg
    assert "discount=5" in msg
    assert "apply_a" in msg
    assert "apply_b" in msg
    norm_msg = msg.replace("\\", "/")
    norm_this = __file__.replace("\\", "/")
    assert ".py" in msg or norm_this in norm_msg


def test_identical_declared_results_no_conflict() -> None:
    clear_rule_usage_sites()

    @logic_lock("premium_discount", result="discount=10")
    def apply_a() -> None:
        return None

    @logic_lock("premium_discount", result="discount=10")
    def apply_b() -> None:
        return None

    assert detect_declared_result_conflicts() == []


def test_mixed_declared_and_omitted_no_conflict_single_value() -> None:
    clear_rule_usage_sites()

    @logic_lock("premium_discount", result="discount=10")
    def apply_a() -> None:
        return None

    @logic_lock("premium_discount")
    def apply_b() -> None:
        return None

    assert detect_declared_result_conflicts() == []


def test_both_omit_result_no_conflict() -> None:
    clear_rule_usage_sites()

    @logic_lock("premium_discount")
    def apply_a() -> None:
        return None

    @logic_lock("premium_discount")
    def apply_b() -> None:
        return None

    assert detect_declared_result_conflicts() == []


def test_detect_with_explicit_sites_independent_of_global() -> None:
    from logiclock.core.rule_usage import RuleUsageSite

    sites = (
        RuleUsageSite(
            rule_id="r",
            result_declared="5%",
            file="a.py",
            line=1,
            qualname="f",
        ),
        RuleUsageSite(
            rule_id="r",
            result_declared="10%",
            file="b.py",
            line=2,
            qualname="g",
        ),
    )
    conflicts = detect_declared_result_conflicts(sites)
    assert len(conflicts) == 1
    assert conflicts[0].distinct_results == ("10%", "5%")


def test_multi_file_overlapping_conditions_conflict_cites_both_paths() -> None:
    from pathlib import Path

    from logiclock.core.rule_usage import RuleUsageSite

    root = Path(__file__).resolve().parent / "fixtures" / "conflicts"
    left_file = str(root / "module_checkout.py")
    right_file = str(root / "module_payout.py")
    sites = (
        RuleUsageSite(
            rule_id="decision_route",
            result_declared="allow_checkout",
            file=left_file,
            line=4,
            qualname="checkout_route",
            conditions_declared=("user.is_verified", "risk_score < 50"),
        ),
        RuleUsageSite(
            rule_id="decision_route",
            result_declared="block_payout",
            file=right_file,
            line=4,
            qualname="payout_route",
            conditions_declared=("user.is_verified", "daily_limit_exceeded"),
        ),
    )
    conflicts = detect_overlapping_predicate_conflicts(sites)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert isinstance(conflict, OverlappingPredicateConflict)
    assert conflict.rule_id == "decision_route"
    assert conflict.overlapping_conditions == ("user.is_verified",)
    message = format_overlapping_predicate_conflict(conflict)
    assert "allow_checkout" in message
    assert "block_payout" in message
    assert left_file.replace("\\", "/") in message.replace("\\", "/")
    assert right_file.replace("\\", "/") in message.replace("\\", "/")


def test_overlapping_conflict_detector_guardrail() -> None:
    from logiclock.core.rule_usage import RuleUsageSite

    sites = tuple(
        RuleUsageSite(
            rule_id="r",
            result_declared="a" if i % 2 == 0 else "b",
            file=f"f{i}.py",
            line=i + 1,
            qualname=f"fn{i}",
            conditions_declared=("same_condition",),
        )
        for i in range(20)
    )
    try:
        detect_overlapping_predicate_conflicts(sites, max_pair_checks=10)
    except RuntimeError as exc:
        assert "pair comparison limit exceeded" in str(exc)
    else:
        raise AssertionError(
            "guardrail should raise when pair checks exceed limit"
        )
