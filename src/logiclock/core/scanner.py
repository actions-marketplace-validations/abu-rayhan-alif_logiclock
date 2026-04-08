"""Repository scanner with incremental cache support (LFL-16)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from logiclock.core.ast_parser import parse_module_logic

DEFAULT_EXCLUDES = (
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "migrations",
    "dist",
    "build",
)
DEFAULT_CACHE_FILE = ".logiclock_scan_cache.json"


@dataclass(frozen=True)
class ScanSummary:
    root: str
    total_py_files: int
    parsed_files: int
    cached_files: int
    parse_errors: int
    total_functions: int
    total_decision_points: int
    elapsed_seconds: float
    cache_enabled: bool
    workers: int


def scan_repository(
    root: str | Path = ".",
    *,
    excludes: tuple[str, ...] = DEFAULT_EXCLUDES,
    use_cache: bool = True,
    cache_file: str = DEFAULT_CACHE_FILE,
    workers: int = 1,
) -> ScanSummary:
    """Scan Python files and return aggregate logic summary."""
    started = time.perf_counter()
    root_path = Path(root).resolve()
    files = tuple(_iter_python_files(root_path, excludes=excludes))
    cache_path = root_path / cache_file
    cache = _load_cache(cache_path) if use_cache else {}

    to_parse: list[tuple[Path, str]] = []
    cached_files = 0
    total_functions = 0
    total_decisions = 0
    for path in files:
        digest = _sha256(path)
        rel = str(path.relative_to(root_path)).replace("\\", "/")
        row = cache.get(rel)
        if row and row.get("hash") == digest:
            cached_files += 1
            total_functions += int(row.get("functions", 0))
            total_decisions += int(row.get("decision_points", 0))
            continue
        to_parse.append((path, digest))

    parse_errors = 0
    if workers > 1 and to_parse:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            parse_inputs = [str(p) for p, _ in to_parse]
            results = ex.map(_parse_file_summary, parse_inputs)
            parsed_rows = list(results)
    else:
        parsed_rows = [_parse_file_summary(str(p)) for p, _ in to_parse]

    for (path, digest), row in zip(to_parse, parsed_rows):
        rel = str(path.relative_to(root_path)).replace("\\", "/")
        if row["error"] is not None:
            parse_errors += 1
            cache[rel] = {
                "hash": digest,
                "functions": 0,
                "decision_points": 0,
                "error": row["error"],
            }
            continue
        fn_count = int(row["functions"])
        dp_count = int(row["decision_points"])
        total_functions += fn_count
        total_decisions += dp_count
        cache[rel] = {
            "hash": digest,
            "functions": fn_count,
            "decision_points": dp_count,
            "error": None,
        }

    if use_cache:
        _save_cache(cache_path, cache)

    elapsed = time.perf_counter() - started
    return ScanSummary(
        root=str(root_path),
        total_py_files=len(files),
        parsed_files=len(to_parse),
        cached_files=cached_files,
        parse_errors=parse_errors,
        total_functions=total_functions,
        total_decision_points=total_decisions,
        elapsed_seconds=elapsed,
        cache_enabled=use_cache,
        workers=max(1, int(workers)),
    )


def _iter_python_files(
    root: Path,
    *,
    excludes: tuple[str, ...],
) -> list[Path]:
    out: list[Path] = []
    exclude_set = set(excludes)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_set]
        for name in filenames:
            if name.endswith(".py"):
                out.append(Path(dirpath) / name)
    out.sort()
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_file_summary(path: str) -> dict[str, int | str | None]:
    try:
        parsed = parse_module_logic(path, decorated_only=False)
    except Exception as exc:
        return {"functions": 0, "decision_points": 0, "error": str(exc)}
    functions = parsed.functions
    decision_points = sum(len(f.decision_points) for f in functions)
    return {
        "functions": len(functions),
        "decision_points": decision_points,
        "error": None,
    }


def _load_cache(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(k): v
        for k, v in data.items()
        if isinstance(k, str) and isinstance(v, dict)
    }


def _save_cache(path: Path, cache: dict[str, dict[str, object]]) -> None:
    payload = json.dumps(cache, indent=2, sort_keys=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload + "\n", encoding="utf-8")
    tmp.replace(path)
