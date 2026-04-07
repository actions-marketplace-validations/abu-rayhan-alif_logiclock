"""Tests for @logic_lock decorator."""

import functools

import pytest

from logiclock.decorators import (
    LOGICLOCK_META_ATTR,
    get_rule_id,
    get_rule_metadata,
    logic_lock,
    registry_view,
)


def test_decorated_function_behavior_unchanged() -> None:
    @logic_lock("premium_discount")
    def apply_discount(x: int, y: int = 1) -> int:
        return x * 10 + y

    assert apply_discount(3) == 31
    assert apply_discount(3, y=2) == 32


def test_get_rule_id_positional_form() -> None:
    @logic_lock("premium_discount")
    def apply_discount() -> None:
        return None

    assert get_rule_id(apply_discount) == "premium_discount"


def test_get_rule_id_keyword_form() -> None:
    @logic_lock(rule="premium_discount")
    def apply_discount() -> None:
        return None

    assert get_rule_id(apply_discount) == "premium_discount"


def test_metadata_on_wrapper_and_wrapped_chain() -> None:
    @logic_lock("premium_discount", version=2)
    def apply_discount() -> str:
        return "ok"

    meta = getattr(apply_discount, LOGICLOCK_META_ATTR)
    assert meta["rule_id"] == "premium_discount"
    assert meta["version"] == 2
    assert get_rule_metadata(apply_discount) == meta
    inner = apply_discount.__wrapped__
    assert getattr(inner, LOGICLOCK_META_ATTR, None) is None


def test_get_rule_id_walks_outer_decorator() -> None:
    def outer_decorator(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapped

    @outer_decorator
    @logic_lock("premium_discount")
    def apply_discount() -> int:
        return 1

    assert get_rule_id(apply_discount) == "premium_discount"


def test_logic_lock_rejects_both_positional_and_rule() -> None:
    with pytest.raises(TypeError, match="not both"):
        logic_lock("a", rule="b")  # type: ignore[call-overload]


def test_logic_lock_requires_rule() -> None:
    with pytest.raises(TypeError, match="non-empty rule id"):
        logic_lock(rule=None)  # type: ignore[call-overload]

    with pytest.raises(TypeError, match="non-empty rule id"):
        logic_lock("")  # type: ignore[arg-type]


def test_registry_snapshot() -> None:
    @logic_lock(rule="premium_discount")
    def f() -> None:
        return None

    snap = registry_view()
    assert len(snap) >= 1
    assert any(
        m.get("rule_id") == "premium_discount" for m in snap.values()
    )


def test_get_rule_metadata_missing_raises() -> None:
    def plain() -> None:
        return None

    with pytest.raises(LookupError):
        get_rule_metadata(plain)
