"""Tests for zero-code autotest command (LFL-13)."""

from pathlib import Path
import re

from typer.testing import CliRunner

from logiclock.cli import app

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text).lower()


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "autotest"


def test_autotest_reports_pass_fail_counts() -> None:
    fx = _fixture_dir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "autotest",
            "--rule",
            str(fx / "demo_rule.json"),
            "--module",
            str(fx / "demo_target.py"),
            "--function",
            "apply_discount",
            "--trusted-code",
        ],
    )
    assert result.exit_code == 1, result.output
    out = result.stdout.lower()
    assert "autotest: completed" in out
    assert "pass:" in out
    assert "fail:" in out


def test_autotest_generate_pytest_file() -> None:
    fx = _fixture_dir()
    runner = CliRunner()
    with runner.isolated_filesystem():
        out = Path("generated_autotest.py")
        result = runner.invoke(
            app,
            [
                "autotest",
                "--rule",
                str(fx / "demo_rule.json"),
                "--module",
                str(fx / "demo_target.py"),
                "--function",
                "apply_discount",
                "--trusted-code",
                "--generate-pytest",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "def test_generated_scenarios" in text


def test_autotest_json_output_shape() -> None:
    fx = _fixture_dir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "autotest",
            "--rule",
            str(fx / "demo_rule.json"),
            "--module",
            str(fx / "demo_target.py"),
            "--function",
            "apply_discount",
            "--trusted-code",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 1, result.output
    import json

    payload = json.loads(result.stdout)
    assert payload["rule"] == "autotest_discount"
    assert "pass" in payload and "fail" in payload


def test_autotest_requires_trusted_code_flag() -> None:
    fx = _fixture_dir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "autotest",
            "--rule",
            str(fx / "demo_rule.json"),
            "--module",
            str(fx / "demo_target.py"),
            "--function",
            "apply_discount",
        ],
    )
    assert result.exit_code != 0
    out = _plain(result.output)
    assert "trusted" in out
