"""Typer CLI for logiclock."""

from __future__ import annotations

import importlib.metadata

import typer

from logiclock.reporting import exit_code_for_report, format_report_plain
from logiclock.reporting.demo import build_sample_report
from logiclock.reporting.terminal import format_report_terminal


def _dist_version() -> str:
    try:
        return importlib.metadata.version("logic-lock")
    except importlib.metadata.PackageNotFoundError:
        from logiclock import __version__

        return str(__version__)


def _configure(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        is_eager=True,
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output (plain text, stable for CI logs).",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Exit with code 1 when a report contains ERROR (default: on).",
    ),
) -> None:
    if version:
        typer.echo(_dist_version())
        raise typer.Exit()
    ctx.obj = {"no_color": no_color, "strict": strict}


app = typer.Typer(
    name="logiclock",
    help="Scan and validate code with configurable logic-lock rules.",
    add_completion=False,
    invoke_without_command=True,
    callback=_configure,
)


@app.command()
def scan(ctx: typer.Context) -> None:
    """Scan the project for rule violations (stub)."""
    _ = ctx
    typer.echo(
        "scan: stub — no violations\n"
        "  Full scan is not wired yet; use the library API or tests. "
        "See README “Quick start”.",
    )


@app.command()
def validate(ctx: typer.Context) -> None:
    """Validate configuration or inputs (stub)."""
    _ = ctx
    typer.echo(
        "validate: stub — OK\n"
        "  Use logiclock.core APIs from Python for metadata validation; "
        "see README.",
    )


@app.command("report-sample")
def report_sample(ctx: typer.Context) -> None:
    """Print a sample report (grouped by severity and rule id)."""
    assert ctx.obj is not None
    no_color: bool = ctx.obj["no_color"]
    strict: bool = ctx.obj["strict"]
    report = build_sample_report()
    if no_color:
        text = format_report_plain(report, color=False)
    else:
        text = format_report_terminal(report, color=True, prefer_rich=True)
    typer.echo(text.rstrip("\n"))
    code = exit_code_for_report(report, fail_on_error=strict)
    raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
