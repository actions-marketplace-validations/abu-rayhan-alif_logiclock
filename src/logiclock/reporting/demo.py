"""Fixed demo data for docs, CLI sample runs, and snapshot tests."""

from __future__ import annotations

from logiclock.core.rule_validator import Severity
from logiclock.reporting.report_model import Report, ReportItem

__all__ = ["build_sample_report"]


def build_sample_report() -> Report:
    """Deterministic report used by ``logiclock report-sample`` and tests."""
    return Report(
        items=(
            ReportItem(
                severity=Severity.ERROR,
                rule_id="premium_discount",
                code="RESULT_MISMATCH",
                message=(
                    "Declared result 'discount=5' does not match "
                    "schema result 'discount=10'"
                ),
            ),
            ReportItem(
                severity=Severity.WARNING,
                rule_id="premium_discount",
                code="MISSING_SCHEMA_CONDITION",
                message=(
                    "Schema condition 'user.is_premium' is not listed in "
                    "implementation metadata conditions"
                ),
            ),
            ReportItem(
                severity=Severity.INFO,
                rule_id="checkout",
                code="SCAN_NOTE",
                message="Stub scan completed (no files examined).",
            ),
        ),
    )
