"""Smoke tests for the logiclock CLI (installed entry point)."""

import re
import shutil
import subprocess
from pathlib import Path

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _cli_help_text(proc: subprocess.CompletedProcess[str]) -> str:
    """Normalize CLI help: merge streams, strip ANSI (Typer/Rich)."""
    combined = (proc.stdout + proc.stderr).lower()
    plain = _ANSI_ESCAPE.sub("", combined)
    # Rare: non-ASCII hyphen in formatted help (e.g. unicode minus).
    return plain.replace("\u2011", "-").replace("\u2212", "-")


def _logiclock_exe() -> str:
    exe = shutil.which("logiclock")
    assert exe, "logiclock console script must be on PATH (pip install -e .)"
    return exe


def test_cli_version_exits_zero() -> None:
    proc = subprocess.run(
        [_logiclock_exe(), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout + proc.stderr).strip()
    assert out
    assert out[0].isdigit() or out.startswith("0.")


def test_cli_help_shows_app_and_commands() -> None:
    proc = subprocess.run(
        [_logiclock_exe(), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert proc.returncode == 0, proc.stderr
    out = _cli_help_text(proc)
    assert "logiclock" in out
    assert "scan" in out
    assert "autotest" in out
    assert "conflicts" in out
    assert "validate" in out
    assert "report-sample" in out
    assert "no-color" in out.replace("_", "-")
    assert "--version" in out or "-V" in out
    assert "scan and validate" in out or "validate" in out


def test_scan_runs_without_traceback() -> None:
    proc = subprocess.run(
        [_logiclock_exe(), "scan"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert proc.returncode == 0
    assert "traceback" not in proc.stderr.lower()
    assert "scan: completed" in proc.stdout.lower()


def test_report_sample_no_color_matches_snapshot_file() -> None:
    snap = (
        Path(__file__).resolve().parent
        / "snapshots"
        / "report_sample_plain.txt"
    )
    expected = snap.read_text(encoding="utf-8").rstrip("\n")
    proc = subprocess.run(
        [
            _logiclock_exe(),
            "--no-color",
            "--no-strict",
            "report-sample",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.rstrip("\n") == expected


def test_report_sample_strict_exits_nonzero() -> None:
    proc = subprocess.run(
        [_logiclock_exe(), "--no-color", "report-sample"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 1


def test_validate_runs_without_traceback() -> None:
    proc = subprocess.run(
        [_logiclock_exe(), "validate"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "traceback" not in proc.stderr.lower()
