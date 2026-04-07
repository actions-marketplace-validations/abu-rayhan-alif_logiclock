"""Process-wide list of ``logic_lock`` registration sites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "RuleUsageSite",
    "clear_rule_usage_sites",
    "iter_rule_usage_sites",
    "record_rule_usage_from_callable",
]

_rule_usage_sites: list[RuleUsageSite] = []


@dataclass(frozen=True)
class RuleUsageSite:
    """One decorated callable’s declared hints and definition location."""

    rule_id: str
    result_declared: str | None
    file: str
    line: int
    qualname: str


def clear_rule_usage_sites() -> None:
    """Clear the process-wide usage list (mainly for tests)."""
    _rule_usage_sites.clear()


def iter_rule_usage_sites() -> tuple[RuleUsageSite, ...]:
    """Snapshot of all recorded sites, in registration order."""
    return tuple(_rule_usage_sites)


def record_rule_usage_from_callable(
    fn: Any,
    rule_id: str,
    result: str | None,
) -> None:
    """Record definition location and declared ``result`` (if any)."""
    code = getattr(fn, "__code__", None)
    if code is None:
        file = "<unknown>"
        line = 0
    else:
        file = str(code.co_filename)
        line = int(code.co_firstlineno)
    qualname = getattr(fn, "__qualname__", repr(fn))
    _rule_usage_sites.append(
        RuleUsageSite(
            rule_id=rule_id,
            result_declared=result,
            file=file,
            line=line,
            qualname=qualname,
        ),
    )
