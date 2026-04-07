"""Format ``Report`` for terminals: plain text, ANSI, or Rich."""

from __future__ import annotations

from typing import NamedTuple

from logiclock.core.rule_validator import Severity
from logiclock.reporting.report_model import Report, ReportItem

__all__ = [
    "format_report_plain",
    "format_report_terminal",
]

_HEADER = "logiclock report"


class _RuleGroup(NamedTuple):
    rule_id: str
    items: tuple[ReportItem, ...]


class _SevBlock(NamedTuple):
    severity: Severity
    rule_groups: tuple[_RuleGroup, ...]


def _severity_blocks(report: Report) -> tuple[_SevBlock, ...]:
    """Group by severity (ERROR/WARNING/INFO), rule id; stable item order."""
    by_sev: dict[Severity, dict[str, list[ReportItem]]] = {}
    for item in report.items:
        by_rule = by_sev.setdefault(item.severity, {})
        by_rule.setdefault(item.rule_id, []).append(item)
    order = (Severity.ERROR, Severity.WARNING, Severity.INFO)
    blocks: list[_SevBlock] = []
    for sev in order:
        groups = by_sev.get(sev)
        if not groups:
            continue
        rule_groups: list[_RuleGroup] = []
        for rule_id in sorted(groups.keys()):
            items = tuple(
                sorted(groups[rule_id], key=lambda i: (i.code, i.message)),
            )
            rule_groups.append(_RuleGroup(rule_id, items))
        blocks.append(_SevBlock(sev, tuple(rule_groups)))
    return tuple(blocks)


def format_report_plain(report: Report, *, color: bool = False) -> str:
    """
    Stable, CI-friendly text (no ANSI unless ``color`` is True).

    Grouped by severity, then rule id. Ends with a single newline.
    """
    if color:
        return _format_ansi(report)
    return _format_plain_no_ansi(report)


def format_report_terminal(
    report: Report,
    *,
    color: bool = True,
    prefer_rich: bool = True,
) -> str:
    """
    Terminal output: Rich when available and ``prefer_rich``; else ANSI if
    ``color``; else plain.
    """
    if color and prefer_rich:
        try:
            return _format_rich(report)
        except ImportError:
            pass
    return format_report_plain(report, color=color)


def _grouped_lines(report: Report) -> str:
    """Plain body: stable blank lines between severity blocks."""
    parts: list[str] = [_HEADER, ""]
    blocks: list[str] = []
    for blk in _severity_blocks(report):
        buf: list[str] = [f"== {blk.severity.value.upper()} =="]
        for rg in blk.rule_groups:
            buf.append(f"-- rule_id: {rg.rule_id} --")
            for it in rg.items:
                msg = it.message.replace("\n", "\n  ")
                buf.append(f"[{it.code}] {msg}")
            buf.append("")
        while buf and buf[-1] == "":
            buf.pop()
        blocks.append("\n".join(buf))
    if not blocks:
        blocks.append("(no findings)")
    parts.append("\n\n".join(blocks))
    parts.append("")
    return "\n".join(parts)


def _format_plain_no_ansi(report: Report) -> str:
    return _grouped_lines(report)


_SEV_STYLE = {
    Severity.ERROR: ("31", "91"),
    Severity.WARNING: ("33", "93"),
    Severity.INFO: ("36", "96"),
}


def _format_ansi(report: Report) -> str:
    parts: list[str] = [_HEADER, ""]
    blocks: list[str] = []
    for blk in _severity_blocks(report):
        dim, bright = _SEV_STYLE[blk.severity]
        buf: list[str] = [
            f"\033[1m\033[{bright}m== {blk.severity.value.upper()} ==\033[0m",
        ]
        for rg in blk.rule_groups:
            buf.append(f"\033[{dim}m-- rule_id: {rg.rule_id} --\033[0m")
            for it in rg.items:
                msg = it.message.replace("\n", "\n  ")
                buf.append(f"[{it.code}] {msg}")
            buf.append("")
        while buf and buf[-1] == "":
            buf.pop()
        blocks.append("\n".join(buf))
    if not blocks:
        blocks.append("(no findings)")
    parts.append("\n\n".join(blocks))
    parts.append("")
    out = "\n".join(parts)
    if not out.endswith("\n"):
        out += "\n"
    return out


def _format_rich(report: Report) -> str:
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    con = Console(
        file=buf,
        width=120,
        force_terminal=True,
        color_system="standard",
    )
    con.print(_HEADER, style="bold")
    con.print()
    style_map = {
        Severity.ERROR: "bold red",
        Severity.WARNING: "bold yellow",
        Severity.INFO: "bold cyan",
    }
    sev_blocks = _severity_blocks(report)
    block_text: list[str] = []
    for blk in sev_blocks:
        sio = StringIO()
        c2 = Console(
            file=sio,
            width=120,
            force_terminal=True,
            color_system="standard",
        )
        c2.print(
            f"== {blk.severity.value.upper()} ==",
            style=style_map[blk.severity],
        )
        for rg in blk.rule_groups:
            c2.print(f"-- rule_id: {rg.rule_id} --", style="dim")
            for it in rg.items:
                c2.print(f"  [{it.code}] {it.message}")
            c2.print()
        block_text.append(sio.getvalue().rstrip("\n"))
    if not block_text:
        con.print("(no findings)")
        con.print()
    else:
        con.print("\n\n".join(block_text))
        con.print()
    return buf.getvalue()
