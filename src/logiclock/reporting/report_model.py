"""Unified report model aggregating validator and conflict results."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from logiclock.core.rule_conflicts import DeclaredResultConflict
from logiclock.core.rule_validator import Finding, Severity

__all__ = [
    "Report",
    "ReportItem",
    "exit_code_for_report",
]


@dataclass(frozen=True)
class ReportItem:
    """One row in a logiclock report (stable sorting / grouping)."""

    severity: Severity
    rule_id: str
    code: str
    message: str


@dataclass
class Report:
    """
    Aggregation of :class:`ReportItem` rows for formatting and exit status.
    """

    items: tuple[ReportItem, ...] = field(default_factory=tuple)

    def with_items(self, *extra: ReportItem) -> Report:
        return Report(items=tuple([*self.items, *extra]))

    @classmethod
    def empty(cls) -> Report:
        return Report(items=())

    @classmethod
    def from_findings(cls, findings: Iterable[Finding]) -> Report:
        items = [
            ReportItem(
                severity=f.severity,
                rule_id=f.rule_id,
                code=f.code,
                message=f.message,
            )
            for f in findings
        ]
        return Report(items=tuple(_sorted_items(items)))

    @classmethod
    def from_conflicts(
        cls,
        conflicts: Iterable[DeclaredResultConflict],
    ) -> Report:
        items: list[ReportItem] = []
        for c in conflicts:
            items.append(
                ReportItem(
                    severity=Severity.ERROR,
                    rule_id=c.rule_id,
                    code="DECLARED_RESULT_CONFLICT",
                    message=c.message,
                ),
            )
        return Report(items=tuple(_sorted_items(items)))

    def merge(self, other: Report) -> Report:
        return Report(items=tuple(_sorted_items([*self.items, *other.items])))

    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.items)


def exit_code_for_report(report: Report, *, fail_on_error: bool = True) -> int:
    """
    Return 0 if there are no ERROR-level items (or ``fail_on_error`` is False).

    Suitable for ``typer.Exit(code=...)``.
    """
    if not fail_on_error:
        return 0
    return 1 if report.has_errors() else 0


_SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


def _sorted_items(items: list[ReportItem]) -> list[ReportItem]:
    return sorted(
        items,
        key=lambda i: (
            _SEVERITY_RANK[i.severity],
            i.rule_id,
            i.code,
            i.message,
        ),
    )
