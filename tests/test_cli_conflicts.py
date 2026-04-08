"""CLI tests for conflict reporting command."""

from typer.testing import CliRunner

from logiclock.cli import app
from logiclock.core import clear_rule_usage_sites
from logiclock.decorators import logic_lock


def test_conflicts_command_reports_none_when_empty() -> None:
    clear_rule_usage_sites()
    runner = CliRunner()
    result = runner.invoke(app, ["conflicts"])
    assert result.exit_code == 0, result.output
    assert "none detected" in result.stdout


def test_conflicts_command_reports_declared_result_conflict() -> None:
    clear_rule_usage_sites()

    @logic_lock("r_checkout", result="allow")
    def a() -> None:
        return None

    @logic_lock("r_checkout", result="block")
    def b() -> None:
        return None

    _ = (a, b)
    runner = CliRunner()
    result = runner.invoke(app, ["conflicts"])
    assert result.exit_code == 1, result.output
    assert "conflicting declared results" in result.stdout
    assert "allow" in result.stdout
    assert "block" in result.stdout


def test_conflicts_command_reports_advanced_overlap_conflict() -> None:
    clear_rule_usage_sites()

    @logic_lock(
        "r_route",
        result="allow_checkout",
        conditions=["user.is_verified", "risk_score < 50"],
    )
    def checkout() -> None:
        return None

    @logic_lock(
        "r_route",
        result="block_payout",
        conditions=["user.is_verified", "daily_limit_exceeded"],
    )
    def payout() -> None:
        return None

    _ = (checkout, payout)
    runner = CliRunner()
    result = runner.invoke(app, ["conflicts", "--advanced"])
    assert result.exit_code == 1, result.output
    assert "overlapping predicates" in result.stdout
    assert "user.is_verified" in result.stdout
    assert "allow_checkout" in result.stdout
    assert "block_payout" in result.stdout
