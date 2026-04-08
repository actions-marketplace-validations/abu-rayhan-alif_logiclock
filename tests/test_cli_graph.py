"""CLI tests for `logiclock graph` command."""

from pathlib import Path

from typer.testing import CliRunner

from logiclock.cli import app

_FIXTURE_MODULE = (
    Path(__file__).resolve().parent / "fixtures" / "sample_module.py"
)
_SNAP_MERMAID = (
    Path(__file__).resolve().parent / "snapshots" / "graph_fixture_module.mmd"
)


def test_graph_command_mermaid_matches_snapshot() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["graph", str(_FIXTURE_MODULE)])
    assert result.exit_code == 0, result.output
    expected = _SNAP_MERMAID.read_text(encoding="utf-8").rstrip("\n")
    assert result.stdout.rstrip("\n") == expected


def test_graph_command_dot_with_function_filter() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "graph",
            str(_FIXTURE_MODULE),
            "--format",
            "dot",
            "--function",
            "plain_check",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "digraph LogicFlow" in result.stdout
    assert "plain_check()" in result.stdout
    assert "apply_discount()" not in result.stdout


def test_graph_command_rejects_non_python_input() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["graph", "README.md"])
    assert result.exit_code != 0
    assert "must point to a .py file" in result.output


def test_graph_command_rejects_missing_module_path() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["graph", "missing_module.py"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_graph_command_rejects_unknown_function() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "graph",
            str(_FIXTURE_MODULE),
            "--function",
            "no_such_fn",
        ],
    )
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_graph_command_output_requires_force_when_file_exists(
    tmp_path: Path,
) -> None:
    out = tmp_path / "graph.mmd"
    out.write_text("existing", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "graph",
            str(_FIXTURE_MODULE),
            "--output",
            str(out),
        ],
    )
    assert result.exit_code != 0
    assert "--force" in result.output


def test_graph_command_rejects_missing_output_directory() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "graph",
            str(_FIXTURE_MODULE),
            "--output",
            str(Path("missing_dir") / "graph.mmd"),
        ],
    )
    assert result.exit_code != 0
    assert "output directory does not exist" in result.output


def test_graph_command_output_writes_with_force(tmp_path: Path) -> None:
    out = tmp_path / "graph.mmd"
    out.write_text("existing", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "graph",
            str(_FIXTURE_MODULE),
            "--output",
            str(out),
            "--force",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "flowchart TD" in out.read_text(encoding="utf-8")
