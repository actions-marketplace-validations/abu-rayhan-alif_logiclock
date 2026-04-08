"""Config loader for logiclock CLI defaults."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

__all__ = ["LogiclockConfig", "load_logiclock_config"]


@dataclass(frozen=True)
class LogiclockConfig:
    excludes: tuple[str, ...] = ()
    workers: int | None = None
    no_cache: bool = False
    scan_format: str = "text"
    rules_path: str | None = None


def load_logiclock_config(root: str | Path = ".") -> LogiclockConfig:
    """Load `.logiclock.toml` from root if present."""
    p = Path(root) / ".logiclock.toml"
    if not p.exists():
        return LogiclockConfig()
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return LogiclockConfig()
    section = data.get("logiclock")
    if not isinstance(section, dict):
        return LogiclockConfig()
    excludes_raw = section.get("exclude", [])
    excludes: tuple[str, ...]
    if isinstance(excludes_raw, list):
        excludes = tuple(str(x) for x in excludes_raw)
    else:
        excludes = ()
    workers_raw = section.get("workers")
    workers = (
        workers_raw
        if isinstance(workers_raw, int) and workers_raw > 0
        else None
    )
    no_cache = bool(section.get("no_cache", False))
    scan_format_raw = section.get("scan_format", "text")
    scan_format = str(scan_format_raw).lower()
    rules_path_raw = section.get("rules_path")
    rules_path = (
        str(rules_path_raw)
        if isinstance(rules_path_raw, str)
        else None
    )
    return LogiclockConfig(
        excludes=excludes,
        workers=workers,
        no_cache=no_cache,
        scan_format=scan_format,
        rules_path=rules_path,
    )
