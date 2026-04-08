"""Tests for repository scanner cache/incremental behavior."""

from pathlib import Path

from logiclock.core.scanner import scan_repository


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_repository_second_run_uses_cache(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.py",
        "def a(x):\n    if x:\n        return 1\n    return 0\n",
    )
    _write(
        tmp_path / "b.py",
        "def b(y):\n    if y > 3:\n        return 9\n    return 2\n",
    )
    first = scan_repository(tmp_path, use_cache=True, workers=1)
    second = scan_repository(tmp_path, use_cache=True, workers=1)
    assert first.total_py_files == 2
    assert first.parsed_files == 2
    assert second.total_py_files == 2
    assert second.parsed_files == 0
    assert second.cached_files == 2


def test_scan_repository_incremental_reparse_only_changed_file(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "a.py", "def a():\n    return 1\n")
    _write(tmp_path / "b.py", "def b():\n    return 2\n")
    _ = scan_repository(tmp_path, use_cache=True, workers=1)
    _write(tmp_path / "b.py", "def b():\n    if True:\n        return 3\n")
    third = scan_repository(tmp_path, use_cache=True, workers=1)
    assert third.total_py_files == 2
    assert third.parsed_files == 1
    assert third.cached_files == 1


def test_scan_repository_excludes_common_dirs(tmp_path: Path) -> None:
    _write(tmp_path / "app" / "ok.py", "def f():\n    return 1\n")
    _write(tmp_path / "venv" / "ignored.py", "def ignored():\n    return 1\n")
    _write(
        tmp_path / "migrations" / "0001_initial.py",
        "def migration():\n    return 1\n",
    )
    summary = scan_repository(tmp_path, use_cache=False, workers=1)
    assert summary.total_py_files == 1
