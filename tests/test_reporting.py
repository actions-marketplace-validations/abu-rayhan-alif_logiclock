"""Reports and terminal formatting (LFL-6)."""

import importlib.util
from pathlib import Path

import pytest

from logiclock.core.rule_conflicts import DeclaredResultConflict
from logiclock.core.rule_usage import RuleUsageSite
from logiclock.core.rule_validator import Finding, Severity
from logiclock.reporting import (
    Report,
    exit_code_for_report,
    format_report_plain,
    format_report_terminal,
)
from logiclock.reporting.demo import build_sample_report
from logiclock.reporting.report_model import ReportItem

_SNAPSHOT = (
    Path(__file__).resolve().parent / "snapshots" / "report_sample_plain.txt"
)


def test_plain_report_snapshot_matches_file() -> None:
    expected = _SNAPSHOT.read_text(encoding="utf-8")
    report = build_sample_report()
    assert format_report_plain(report, color=False) == expected


def test_grouped_by_severity_then_rule_id() -> None:
    report = build_sample_report()
    text = format_report_plain(report, color=False)
    err = text.index("== ERROR ==")
    warn = text.index("== WARNING ==")
    info = text.index("== INFO ==")
    assert err < warn < info
    assert text.find("premium_discount", err, warn) != -1


def test_exit_code_strict_and_relaxed() -> None:
    report = build_sample_report()
    assert exit_code_for_report(report, fail_on_error=True) == 1
    assert exit_code_for_report(report, fail_on_error=False) == 0
    assert exit_code_for_report(Report.empty(), fail_on_error=True) == 0


def test_report_from_findings_roundtrip_shape() -> None:
    findings = [
        Finding(
            severity=Severity.WARNING,
            code="X",
            message="m",
            rule_id="r1",
        ),
    ]
    report = Report.from_findings(findings)
    assert len(report.items) == 1
    assert report.items[0].code == "X"


def test_report_from_conflicts() -> None:
    c = DeclaredResultConflict(
        rule_id="dup",
        distinct_results=("a", "b"),
        sites=(
            RuleUsageSite("dup", "a", "f.py", 1, "x"),
            RuleUsageSite("dup", "b", "f.py", 2, "y"),
        ),
    )
    report = Report.from_conflicts([c])
    assert len(report.items) == 1
    assert report.items[0].severity == Severity.ERROR
    assert report.items[0].code == "DECLARED_RESULT_CONFLICT"


def test_merge_reports() -> None:
    a = Report(items=(ReportItem(Severity.INFO, "r", "A", "one"),))
    b = Report(items=(ReportItem(Severity.ERROR, "r", "B", "two"),))
    m = a.merge(b)
    assert m.items[0].severity == Severity.ERROR
    assert m.items[1].severity == Severity.INFO


@pytest.mark.skipif(
    importlib.util.find_spec("rich") is None,
    reason="rich optional",
)
def test_format_report_terminal_rich_includes_sections() -> None:
    out = format_report_terminal(
        build_sample_report(),
        color=True,
        prefer_rich=True,
    )
    assert "logiclock report" in out
    assert "ERROR" in out
    assert "WARNING" in out


def test_ansi_mode_uses_escape_codes() -> None:
    out = format_report_plain(build_sample_report(), color=True)
    assert "\033[" in out
    assert "== ERROR ==" in out
