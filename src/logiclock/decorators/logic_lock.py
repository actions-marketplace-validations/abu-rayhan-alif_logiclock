"""Attach logic-lock rule metadata to callables."""

from __future__ import annotations

import functools
import weakref
from collections.abc import Callable
from typing import Any, TypeVar

from logiclock.core.rule_usage import record_rule_usage_from_callable

__all__ = [
    "LOGICLOCK_META_ATTR",
    "get_rule_id",
    "get_rule_metadata",
    "logic_lock",
    "registry_view",
]

LOGICLOCK_META_ATTR = "__logiclock_meta__"

F = TypeVar("F", bound=Callable[..., Any])

# Optional introspection: weak keys so decorators do not leak callables.
_registry: weakref.WeakKeyDictionary[Callable[..., Any], dict[str, Any]] = (
    weakref.WeakKeyDictionary()
)


def _merge_meta(
    rule_id: str,
    version: int | None,
    result: str | None,
    conditions: list[str] | None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {"rule_id": rule_id}
    if version is not None:
        meta["version"] = version
    if result is not None:
        meta["result"] = result
    if conditions is not None:
        meta["conditions"] = list(conditions)
    return meta


def logic_lock(
    arg: str | None = None,
    *,
    rule: str | None = None,
    version: int | None = None,
    result: str | None = None,
    conditions: list[str] | None = None,
) -> Callable[[F], F]:
    """
    Decorator: attach rule id (and optional ``version``) for tooling / runtime.

    Usage::

        @logic_lock("premium_discount")
        def apply_discount(): ...

        @logic_lock(rule="premium_discount", version=1)
        def apply_discount(): ...

        @logic_lock(
            "price_rule",
            result="discount=10",
            conditions=["user.is_premium"],
        )
        def f(): ...
    """
    if arg is not None and rule is not None:
        raise TypeError(
            "logic_lock: pass the rule id either positionally or as "
            "'rule=', not both",
        )
    rule_id = rule if rule is not None else arg
    if not rule_id or not isinstance(rule_id, str):
        raise TypeError(
            "logic_lock requires a non-empty rule id string "
            "(e.g. @logic_lock('my_rule') or @logic_lock(rule='my_rule')).",
        )

    meta = _merge_meta(rule_id, version, result, conditions)

    def decorator(fn: F) -> F:
        record_rule_usage_from_callable(fn, rule_id, result)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        setattr(wrapper, LOGICLOCK_META_ATTR, meta)
        _registry[wrapper] = dict(meta)
        return wrapper  # type: ignore[return-value]

    return decorator


def get_rule_metadata(obj: Any) -> dict[str, Any]:
    """
    Return metadata dict from ``obj`` or any callable in its ``__wrapped__``
    chain. Raises ``LookupError`` if none is found.
    """
    current: Any = obj
    seen: set[int] = set()
    while callable(current):
        cid = id(current)
        if cid in seen:
            break
        seen.add(cid)
        raw = getattr(current, LOGICLOCK_META_ATTR, None)
        if isinstance(raw, dict) and "rule_id" in raw:
            return dict(raw)
        reg = _registry.get(current)
        if reg is not None:
            return dict(reg)
        current = getattr(current, "__wrapped__", None)
    raise LookupError(f"No logic_lock metadata on {obj!r}")


def get_rule_id(obj: Any) -> str:
    """Return the rule id string attached by :func:`logic_lock`."""
    return str(get_rule_metadata(obj)["rule_id"])


def registry_view() -> dict[str, Any]:
    """
    Snapshot of registered wrappers for tests / introspection.

    Keys are ``repr()`` of callables because functions are not dict keys
    in a plain dict copy.
    """
    return {repr(fn): dict(meta) for fn, meta in _registry.items()}
