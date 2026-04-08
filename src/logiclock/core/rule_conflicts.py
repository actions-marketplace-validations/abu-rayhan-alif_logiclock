"""Detect conflicting declarations for the same rule id (basic, metadata)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from logiclock.core.rule_usage import RuleUsageSite, iter_rule_usage_sites

__all__ = [
    "DeclaredResultConflict",
    "OverlappingPredicateConflict",
    "detect_declared_result_conflicts",
    "detect_overlapping_predicate_conflicts",
    "format_declared_result_conflict",
    "format_overlapping_predicate_conflict",
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


@dataclass(frozen=True)
class OverlappingPredicateConflict:
    """
    Same rule id with overlapping declared conditions but different outcomes.

    Overlap is approximated by normalized condition expression intersection.
    """

    rule_id: str
    left: RuleUsageSite
    right: RuleUsageSite
    overlapping_conditions: tuple[str, ...]

    @property
    def message(self) -> str:
        return format_overlapping_predicate_conflict(self)


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


def detect_overlapping_predicate_conflicts(
    sites: Iterable[RuleUsageSite] | None = None,
    *,
    max_pair_checks: int = 20000,
) -> list[OverlappingPredicateConflict]:
    """
    Detect contradictory branches across files/modules for the same rule id.

    Performance guardrail:
    - ``max_pair_checks`` limits pairwise comparisons and fails fast.
    """
    all_sites = tuple(iter_rule_usage_sites() if sites is None else sites)
    by_rule: dict[str, list[RuleUsageSite]] = defaultdict(list)
    for site in all_sites:
        by_rule[site.rule_id].append(site)

    conflicts: list[OverlappingPredicateConflict] = []
    pair_checks = 0
    for rule_id, rule_sites in sorted(by_rule.items()):
        n = len(rule_sites)
        if n < 2:
            continue
        for i in range(n):
            left = rule_sites[i]
            if left.result_declared is None:
                continue
            left_set = _normalized_conditions(left)
            if not left_set:
                continue
            for j in range(i + 1, n):
                pair_checks += 1
                if pair_checks > max_pair_checks:
                    raise RuntimeError(
                        "pair comparison limit exceeded while detecting "
                        "overlapping predicate conflicts"
                    )
                right = rule_sites[j]
                if right.result_declared is None:
                    continue
                if left.result_declared == right.result_declared:
                    continue
                right_set = _normalized_conditions(right)
                if not right_set:
                    continue
                overlap = tuple(sorted(left_set & right_set))
                if not overlap:
                    continue
                conflicts.append(
                    OverlappingPredicateConflict(
                        rule_id=rule_id,
                        left=left,
                        right=right,
                        overlapping_conditions=overlap,
                    ),
                )
    return conflicts


def format_overlapping_predicate_conflict(
    conflict: OverlappingPredicateConflict,
) -> str:
    """Human-readable conflict text with both paths/symbols cited."""
    shared = ", ".join(repr(c) for c in conflict.overlapping_conditions)
    left_res = conflict.left.result_declared
    right_res = conflict.right.result_declared
    return (
        f"Rule {conflict.rule_id!r} has overlapping predicates with different "
        f"results ({left_res!r} vs {right_res!r}).\n"
        f"Shared conditions: {shared}\n"
        f"Left:  {conflict.left.file}:{conflict.left.line} "
        f"({conflict.left.qualname})\n"
        f"Right: {conflict.right.file}:{conflict.right.line} "
        f"({conflict.right.qualname})"
    )


def _normalized_conditions(site: RuleUsageSite) -> set[str]:
    return {c.strip().lower() for c in site.conditions_declared if c.strip()}
