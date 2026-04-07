"""Detect conflicting declarations for the same rule id (basic, metadata)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from logiclock.core.rule_usage import RuleUsageSite, iter_rule_usage_sites

__all__ = [
    "DeclaredResultConflict",
    "detect_declared_result_conflicts",
    "format_declared_result_conflict",
]


@dataclass(frozen=True)
class DeclaredResultConflict:
    """
    Same ``rule_id`` with two or more different declared ``result`` strings.
    """

    rule_id: str
    distinct_results: tuple[str, ...]
    sites: tuple[RuleUsageSite, ...]

    @property
    def message(self) -> str:
        return format_declared_result_conflict(self)


def format_declared_result_conflict(conflict: DeclaredResultConflict) -> str:
    """Human-readable message listing locations (file:line / qualname)."""
    lines: list[str] = [
        f"Rule {conflict.rule_id!r} has conflicting declared results: "
        f"{', '.join(repr(r) for r in conflict.distinct_results)}.",
        "Locations:",
    ]
    for site in conflict.sites:
        if site.result_declared is not None:
            res = site.result_declared
        else:
            res = "<not declared>"
        lines.append(
            f"  - {site.file}:{site.line} ({site.qualname}) result={res!r}",
        )
    return "\n".join(lines)


def detect_declared_result_conflicts(
    sites: Iterable[RuleUsageSite] | None = None,
) -> list[DeclaredResultConflict]:
    """
    Find rule ids where declared ``result`` strings disagree across sites.

    Only **non-None** ``result_declared`` values take part in comparison.
    If at most one distinct declared value appears (or none), there is no
    conflict.
    """
    all_sites = tuple(iter_rule_usage_sites() if sites is None else sites)
    by_rule: dict[str, list[RuleUsageSite]] = defaultdict(list)
    for site in all_sites:
        by_rule[site.rule_id].append(site)

    conflicts: list[DeclaredResultConflict] = []
    for rule_id, rule_sites in sorted(by_rule.items()):
        declared = [
            s.result_declared
            for s in rule_sites
            if s.result_declared is not None
        ]
        distinct = tuple(sorted(set(declared)))
        if len(distinct) <= 1:
            continue
        conflicts.append(
            DeclaredResultConflict(
                rule_id=rule_id,
                distinct_results=distinct,
                sites=tuple(rule_sites),
            ),
        )
    return conflicts
