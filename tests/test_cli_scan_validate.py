"""CLI tests for scan json output and validate flow."""

import json
from pathlib import Path
import re

from typer.testing import CliRunner

from logiclock.cli import app
from logiclock.core import clear_rule_usage_sites

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text).lower()


def test_scan_json_output_shape(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        "def f():\n    return 1\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--workers", "1"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["files"] == 1
    assert payload["parsed"] >= 0
    assert "elapsed_seconds" in payload


def test_scan_uses_config_default_format_when_flag_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.py").write_text(
        "def f():\n    return 1\n",
        encoding="utf-8",
    )
    (tmp_path / ".logiclock.toml").write_text(
        "[logiclock]\nscan_format = 'json'\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--workers", "1"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["files"] == 1


def test_scan_sarif_output_contains_results(tmp_path: Path) -> None:
    mod = tmp_path / "mod.py"
    mod.write_text(
        "\n".join(
            [
                "from logiclock.decorators import logic_lock",
                "",
                "@logic_lock(123)",
                "def f():",
                "    return 1",
            ]
        ),
        encoding="utf-8",
    )
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "a.json").write_text(
        json.dumps({"id": "known_rule", "conditions": ["x"], "result": "ok"}),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "sarif",
            "--rules",
            str(rules),
            "--workers",
            "1",
        ],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["version"] == "2.1.0"
    assert "runs" in payload
    run = payload["runs"][0]
    assert run["tool"]["driver"]["rules"]
    first = run["results"][0]
    assert "ruleId" in first
    assert first["level"] in {"error", "warning", "note"}
    assert first["properties"]["source"] == "scan"


def test_validate_reports_ok_for_matching_rule(tmp_path: Path) -> None:
    clear_rule_usage_sites()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "r.json").write_text(
        json.dumps(
            {
                "id": "checkout_discount",
                "conditions": ["user.is_premium"],
                "result": "discount=10",
            }
        ),
        encoding="utf-8",
    )
    mod = tmp_path / "mod.py"
    mod.write_text(
        "\n".join(
            [
                "from logiclock.decorators import logic_lock",
                "",
                '@logic_lock("checkout_discount", result="discount=10", '
                'conditions=["user.is_premium"])',
                "def f(user):",
                "    return 'discount=10'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate",
            "--rules",
            str(rules_dir),
            "--module",
            str(mod),
            "--trusted-code",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "validate: OK" in result.stdout


def test_validate_json_output_shape(tmp_path: Path) -> None:
    clear_rule_usage_sites()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "r.json").write_text(
        json.dumps(
            {
                "id": "checkout_discount",
                "conditions": ["user.is_premium"],
                "result": "discount=10",
            }
        ),
        encoding="utf-8",
    )
    mod = tmp_path / "mod.py"
    mod.write_text(
        "from logiclock.decorators import logic_lock\n"
        "@logic_lock('checkout_discount', result='discount=10', "
        "conditions=['user.is_premium'])\n"
        "def f(user):\n    return 'discount=10'\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate",
            "--rules",
            str(rules_dir),
            "--module",
            str(mod),
            "--trusted-code",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert "findings" in payload
    assert payload["findings"] == []


def test_validate_sarif_has_rules_and_properties(tmp_path: Path) -> None:
    clear_rule_usage_sites()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "r.json").write_text(
        json.dumps(
            {"id": "checkout_discount", "conditions": ["x"], "result": "ok"}
        ),
        encoding="utf-8",
    )
    mod = tmp_path / "mod.py"
    mod.write_text(
        "from logiclock.decorators import logic_lock\n"
        "@logic_lock('checkout_discount', result='bad', conditions=['x'])\n"
        "def f(x):\n    return 'bad'\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate",
            "--rules",
            str(rules_dir),
            "--module",
            str(mod),
            "--trusted-code",
            "--format",
            "sarif",
        ],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    run = payload["runs"][0]
    assert run["tool"]["driver"]["rules"]
    first = run["results"][0]
    assert first["ruleId"]
    assert first["level"] in {"error", "warning", "note"}
    assert first["properties"]["source"] == "validate"


def test_validate_requires_trusted_code_flag(tmp_path: Path) -> None:
    clear_rule_usage_sites()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "r.json").write_text(
        json.dumps(
            {"id": "r", "conditions": ["x"], "result": "ok"}
        ),
        encoding="utf-8",
    )
    mod = tmp_path / "mod.py"
    mod.write_text("def f():\n    return 'ok'\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["validate", "--rules", str(rules_dir), "--module", str(mod)],
    )
    assert result.exit_code != 0
    out = _plain(result.output)
    assert "trusted" in out
