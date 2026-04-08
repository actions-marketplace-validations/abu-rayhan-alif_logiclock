"""Zero-code scenario execution for pure functions (LFL-13)."""

from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from logiclock.core.edge_case_generator import (
    generate_scenarios_from_conditions,
)
from logiclock.core.rule_schema import (
    Rule,
    load_rule_from_dict,
    load_rule_from_json_file,
)

__all__ = [
    "AutoTestReport",
    "ScenarioResult",
    "autotest_function",
    "generate_pytest_from_rule",
    "is_likely_unsafe_for_execution",
    "load_rule_flexible",
]


@dataclass(frozen=True)
class ScenarioResult:
    scenario: dict[str, object]
    output: object | None
    passed: bool
    error: str | None


@dataclass(frozen=True)
class AutoTestReport:
    rule_id: str
    total: int
    passed: int
    failed: int
    truncated: bool
    results: tuple[ScenarioResult, ...]


def load_rule_flexible(path: str | Path) -> Rule:
    """Load rule JSON accepting either `id` or `rule_id` keys."""
    p = Path(path)
    try:
        return load_rule_from_json_file(p)
    except Exception:
        import json

        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise
        if "rule_id" in raw and "id" not in raw:
            raw = dict(raw)
            raw["id"] = raw.pop("rule_id")
        return load_rule_from_dict(raw)


def is_likely_unsafe_for_execution(fn: Any) -> bool:
    """Heuristic check for ORM/network-heavy code paths."""
    try:
        src = inspect.getsource(fn).lower()
    except Exception:
        return True
    danger_markers = (
        "django",
        ".objects.",
        "session",
        "requests.",
        "httpx.",
        "sqlalchemy",
        "database",
    )
    return any(m in src for m in danger_markers)


def autotest_function(
    *,
    module_path: str | Path,
    function_name: str,
    rule: Rule,
    allow_unsafe: bool = False,
) -> AutoTestReport:
    """Execute generated scenarios against a target function."""
    fn = _load_function(module_path, function_name)
    if is_likely_unsafe_for_execution(fn) and not allow_unsafe:
        raise RuntimeError(
            "Function looks ORM/network-bound; "
            "use --generate-pytest or --allow-unsafe."
        )
    generated = generate_scenarios_from_conditions(rule.conditions)
    rows: list[ScenarioResult] = []
    for scenario in generated.scenarios:
        args = _build_call_args(fn, scenario)
        try:
            output = fn(**args)
            passed = str(output) == str(rule.result)
            rows.append(
                ScenarioResult(
                    scenario=scenario,
                    output=output,
                    passed=passed,
                    error=None,
                )
            )
        except Exception as exc:
            rows.append(
                ScenarioResult(
                    scenario=scenario,
                    output=None,
                    passed=False,
                    error=str(exc),
                )
            )
    passed_count = sum(1 for r in rows if r.passed)
    total = len(rows)
    return AutoTestReport(
        rule_id=rule.id,
        total=total,
        passed=passed_count,
        failed=total - passed_count,
        truncated=generated.truncated,
        results=tuple(rows),
    )


def generate_pytest_from_rule(
    *,
    module_path: str | Path,
    function_name: str,
    rule: Rule,
    output_path: str | Path,
) -> Path:
    """Generate opt-in pytest file for manual/sandboxed execution."""
    generated = generate_scenarios_from_conditions(rule.conditions)
    out = Path(output_path)
    scenarios_literal = repr(list(generated.scenarios))
    code = (
        "import importlib.util\n"
        "from pathlib import Path\n\n"
        f"MODULE_PATH = {str(Path(module_path))!r}\n"
        f"FUNCTION_NAME = {function_name!r}\n"
        f"EXPECTED_RESULT = {str(rule.result)!r}\n"
        f"SCENARIOS = {scenarios_literal}\n\n"
        "def _load_target():\n"
        "    spec = importlib.util.spec_from_file_location(\n"
        "        'logiclock_autotest_target', MODULE_PATH\n"
        "    )\n"
        "    assert spec and spec.loader\n"
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(mod)\n"
        "    return getattr(mod, FUNCTION_NAME)\n\n"
        "def test_generated_scenarios():\n"
        "    fn = _load_target()\n"
        "    for scenario in SCENARIOS:\n"
        "        out = fn(**scenario)\n"
        "        assert str(out) == EXPECTED_RESULT\n"
    )
    out.write_text(code, encoding="utf-8")
    return out


def _load_function(module_path: str | Path, function_name: str) -> Any:
    p = Path(module_path)
    spec = importlib.util.spec_from_file_location(
        "logiclock_autotest_target",
        p,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed loading module: {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, function_name):
        raise RuntimeError(f"function not found in module: {function_name}")
    return getattr(mod, function_name)


def _build_call_args(
    fn: Any,
    scenario: dict[str, object],
) -> dict[str, object]:
    sig = inspect.signature(fn)
    args: dict[str, object] = {}
    nested: dict[str, dict[str, object]] = {}
    for key, value in scenario.items():
        if "." in key:
            root, rest = key.split(".", 1)
            nested.setdefault(root, {})[rest] = value
        else:
            args[key] = value
    for root, attrs in nested.items():
        if root in sig.parameters:
            args[root] = _namespace_from_dotted(attrs)
    return {k: v for k, v in args.items() if k in sig.parameters}


def _namespace_from_dotted(attrs: dict[str, object]) -> object:
    root: dict[str, object] = {}
    for dotted, value in attrs.items():
        parts = dotted.split(".")
        cur = root
        for part in parts[:-1]:
            if part not in cur or not isinstance(cur[part], dict):
                cur[part] = {}
            cur = cur[part]  # type: ignore[assignment]
        cur[parts[-1]] = value
    return _dict_to_ns(root)


def _dict_to_ns(d: dict[str, object]) -> object:
    out: dict[str, object] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _dict_to_ns(v)
        else:
            out[k] = v
    return SimpleNamespace(**out)
