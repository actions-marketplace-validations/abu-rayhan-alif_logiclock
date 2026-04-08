"""Typer CLI for logiclock."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import ast
from pathlib import Path

import typer

from logiclock.core import (
    DEFAULT_EXCLUDES,
    ImplementationSpec,
    Severity,
    ValidationPolicy,
    detect_declared_result_conflicts,
    detect_overlapping_predicate_conflicts,
    export_dot,
    export_mermaid,
    findings_include_severity,
    format_declared_result_conflict,
    format_overlapping_predicate_conflict,
    load_logiclock_config,
    load_rule_flexible,
    load_rule_from_json_file,
    parse_module_logic,
    scan_repository,
    validate_implementation_vs_schema,
    clear_rule_usage_sites,
    autotest_function,
    generate_pytest_from_rule,
    iter_rule_usage_sites,
)
from logiclock.reporting import exit_code_for_report, format_report_plain
from logiclock.reporting.demo import build_sample_report
from logiclock.reporting.terminal import format_report_terminal

_KNOWN_PARSE_ERRORS = (
    OSError,
    UnicodeDecodeError,
    ValueError,
)


def _default_workers() -> int:
    return max(1, min(4, os.cpu_count() or 1))


def _dist_version() -> str:
    try:
        return importlib.metadata.version("pylogiclock")
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
def scan(
    ctx: typer.Context,
    root: str = typer.Argument(
        ".",
        help="Root directory to scan.",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Disable scan cache and re-parse all files.",
    ),
    workers: int = typer.Option(
        _default_workers(),
        "--workers",
        min=1,
        help="Parallel parser workers (processes).",
    ),
    exclude: list[str] = typer.Option(
        [],
        "--exclude",
        help="Extra directory name to exclude (can be repeated).",
    ),
    format: str | None = typer.Option(
        None,
        "--format",
        help="Scan output format: text, json, or sarif.",
    ),
    rules_path: str | None = typer.Option(
        None,
        "--rules",
        help="Directory containing rule JSON files for scan matching.",
    ),
) -> None:
    """Scan repository Python files and print summary."""
    _ = ctx
    cfg = load_logiclock_config(root)
    excludes = tuple(
        dict.fromkeys((*DEFAULT_EXCLUDES, *cfg.excludes, *exclude))
    )
    resolved_workers = workers if workers > 0 else (_default_workers())
    if workers == _default_workers() and cfg.workers is not None:
        resolved_workers = cfg.workers
    use_cache = not no_cache
    if not no_cache and cfg.no_cache:
        use_cache = False
    summary = scan_repository(
        root=root,
        excludes=excludes,
        use_cache=use_cache,
        workers=resolved_workers,
    )
    rule_stats = _scan_rule_stats(
        root=Path(summary.root),
        excludes=excludes,
        rules_path=rules_path or cfg.rules_path,
    )
    out_fmt = (
        format.strip().lower()
        if format is not None
        else cfg.scan_format.strip().lower()
    )
    if out_fmt == "json":
        payload = {
            "root": summary.root,
            "files": summary.total_py_files,
            "parsed": summary.parsed_files,
            "cached": summary.cached_files,
            "parse_errors": summary.parse_errors,
            "functions": summary.total_functions,
            "decision_points": summary.total_decision_points,
            "workers": summary.workers,
            "cache_enabled": summary.cache_enabled,
            "elapsed_seconds": round(summary.elapsed_seconds, 6),
            "detected_rules": sorted(rule_stats["detected_rules"]),
            "missing_rule_metadata_paths": sorted(
                rule_stats["missing_rule_metadata_paths"]
            ),
            "unmatched_rule_ids": sorted(rule_stats["unmatched_rule_ids"]),
        }
        typer.echo(json.dumps(payload, indent=2))
        if (
            ctx.obj
            and ctx.obj.get("strict")
            and _has_scan_findings(rule_stats)
        ):
            raise typer.Exit(code=1)
        return
    if out_fmt == "sarif":
        typer.echo(json.dumps(_scan_sarif(summary.root, rule_stats), indent=2))
        if (
            ctx.obj
            and ctx.obj.get("strict")
            and _has_scan_findings(rule_stats)
        ):
            raise typer.Exit(code=1)
        return
    if out_fmt != "text":
        raise typer.BadParameter("format must be one of: text, json, sarif")
    typer.echo(
        "\n".join(
            [
                "scan: completed",
                f"  root: {summary.root}",
                f"  files: {summary.total_py_files}",
                f"  parsed: {summary.parsed_files}",
                f"  cached: {summary.cached_files}",
                f"  parse_errors: {summary.parse_errors}",
                f"  functions: {summary.total_functions}",
                f"  decision_points: {summary.total_decision_points}",
                f"  workers: {summary.workers}",
                f"  cache: {'on' if summary.cache_enabled else 'off'}",
                f"  elapsed_s: {summary.elapsed_seconds:.3f}",
                f"  detected_rules: {len(rule_stats['detected_rules'])}",
                f"  missing_rule_metadata: "
                f"{len(rule_stats['missing_rule_metadata_paths'])}",
                "  unmatched_rule_ids: "
                f"{len(rule_stats['unmatched_rule_ids'])}",
            ]
        )
    )
    if rule_stats["missing_rule_metadata_paths"]:
        typer.echo("  How to fix: add @logic_lock('rule_id', ...).")
    if rule_stats["unmatched_rule_ids"]:
        typer.echo("  How to fix: add matching rule JSON or fix rule id.")
    if ctx.obj and ctx.obj.get("strict") and _has_scan_findings(rule_stats):
        raise typer.Exit(code=1)


@app.command()
def validate(
    ctx: typer.Context,
    rules_path: str = typer.Option(
        "examples",
        "--rules",
        help="Directory containing rule JSON files.",
    ),
    module: list[str] = typer.Option(
        [],
        "--module",
        help="Python module file path to import for decorator metadata.",
    ),
    trusted_code: bool = typer.Option(
        False,
        "--trusted-code",
        help="Confirm that importing target modules is trusted/safe.",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Validate output format: text, json, or sarif.",
    ),
) -> None:
    """Validate declared decorator metadata against rule JSON schemas."""
    _ = ctx
    cfg = load_logiclock_config(".")
    resolved_rules = rules_path
    if rules_path == "examples" and cfg.rules_path is not None:
        resolved_rules = cfg.rules_path
    json_files = sorted(Path(resolved_rules).rglob("*.json"))
    if not json_files:
        raise typer.BadParameter(
            f"no rule JSON files found under: {resolved_rules}",
            param_hint="--rules. How to fix: pass a valid rules directory.",
        )
    rules = {}
    for p in json_files:
        try:
            rule = load_rule_from_json_file(p)
        except Exception:
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict) or "rule_id" not in raw:
                continue
            raw2 = dict(raw)
            raw2["id"] = raw2.pop("rule_id")
            try:
                from logiclock.core import load_rule_from_dict

                rule = load_rule_from_dict(raw2)
            except Exception:
                continue
        rules[rule.id] = rule

    clear_rule_usage_sites()
    if module and not trusted_code:
        raise typer.BadParameter(
            "validate imports and executes module top-level code.",
            param_hint=(
                "pass --trusted-code if you trust the target module(s)"
            ),
        )
    for idx, module_path in enumerate(module):
        path = Path(module_path)
        if not path.exists():
            raise typer.BadParameter(
                f"module path does not exist: {path}",
                param_hint=(
                    "--module. How to fix: pass an existing .py module."
                ),
            )
        name = f"logiclock_validate_target_{idx}"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise typer.BadParameter(
                f"failed loading module: {path}",
                param_hint=(
                    "--module. How to fix: ensure valid importable module."
                ),
            )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    findings_text: list[str] = []
    findings_payload: list[dict[str, str]] = []
    all_findings = []
    used_rule_ids: set[str] = set()
    for site in iter_rule_usage_sites():
        used_rule_ids.add(site.rule_id)
        rule = rules.get(site.rule_id)
        if rule is None:
            findings_text.append(
                f"ERROR RULE_NOT_FOUND {site.rule_id}: "
                f"{site.file}:{site.line} ({site.qualname})\n"
                "How to fix: add rule JSON with matching id."
            )
            findings_payload.append(
                {
                    "severity": "error",
                    "code": "RULE_NOT_FOUND",
                    "rule_id": site.rule_id,
                    "message": "Rule JSON not found for decorated function.",
                    "path": site.file,
                    "line": str(site.line),
                }
            )
            continue
        impl = ImplementationSpec(
            rule_id=site.rule_id,
            result_declared=site.result_declared,
            conditions_declared=list(site.conditions_declared),
        )
        findings = validate_implementation_vs_schema(
            rule,
            impl,
            policy=ValidationPolicy(),
        )
        all_findings.extend(findings)
        for f in findings:
            findings_text.append(
                f"{f.severity.value.upper()} {f.code} {f.rule_id}: "
                f"{f.message}\nHow to fix: update decorator metadata "
                "or rule JSON."
            )
            findings_payload.append(
                {
                    "severity": f.severity.value,
                    "code": f.code,
                    "rule_id": f.rule_id,
                    "message": f.message,
                    "path": site.file,
                    "line": str(site.line),
                }
            )
    for rule_id in sorted(set(rules) - used_rule_ids):
        findings_text.append(
            f"INFO RULE_UNUSED {rule_id}: no decorated usage found"
        )
        findings_payload.append(
            {
                "severity": "info",
                "code": "RULE_UNUSED",
                "rule_id": rule_id,
                "message": "Rule has no decorated usage.",
                "path": str(Path(resolved_rules)),
                "line": "1",
            }
        )

    out_fmt = format.strip().lower()
    has_error = findings_include_severity(all_findings, Severity.ERROR) or any(
        line.startswith("ERROR RULE_NOT_FOUND") for line in findings_text
    )
    if not findings_text:
        if out_fmt == "json":
            typer.echo(json.dumps({"findings": []}, indent=2))
        elif out_fmt == "sarif":
            typer.echo(json.dumps(_validate_sarif(findings_payload), indent=2))
        else:
            typer.echo("validate: OK (no findings)")
        return
    if out_fmt == "json":
        typer.echo(json.dumps({"findings": findings_payload}, indent=2))
    elif out_fmt == "sarif":
        typer.echo(json.dumps(_validate_sarif(findings_payload), indent=2))
    elif out_fmt == "text":
        typer.echo("\n".join(findings_text))
    else:
        raise typer.BadParameter("format must be one of: text, json, sarif")
    if has_error:
        raise typer.Exit(code=1)


@app.command()
def conflicts(
    advanced: bool = typer.Option(
        False,
        "--advanced",
        help="Also detect overlapping predicate conflicts.",
    ),
    max_pair_checks: int = typer.Option(
        20000,
        "--max-pair-checks",
        min=1,
        help="Pairwise comparison guardrail for advanced conflicts.",
    ),
) -> None:
    """Print detected rule conflicts from current registered usage sites."""
    declared = detect_declared_result_conflicts()
    advanced_items = (
        detect_overlapping_predicate_conflicts(
            max_pair_checks=max_pair_checks,
        )
        if advanced
        else []
    )
    if not declared and not advanced_items:
        typer.echo("conflicts: none detected")
        return
    for item in declared:
        typer.echo(format_declared_result_conflict(item))
        typer.echo("")
    for item in advanced_items:
        typer.echo(format_overlapping_predicate_conflict(item))
        typer.echo("")
    raise typer.Exit(code=1)


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


@app.command()
def graph(
    module_path: str = typer.Argument(
        ...,
        help="Python module path to parse.",
    ),
    format: str = typer.Option(
        "mermaid",
        "--format",
        "-f",
        help="Output format: mermaid or dot.",
    ),
    function: str | None = typer.Option(
        None,
        "--function",
        help="Export a single function by name (default: whole module).",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to file instead of stdout.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow overwriting an existing output file.",
    ),
) -> None:
    """Export visual logic flow as Mermaid (.mmd) or Graphviz (.dot)."""
    module = Path(module_path)
    if not module.exists():
        raise typer.BadParameter(
            f"module path does not exist: {module}",
            param_hint="module_path",
        )
    if module.suffix.lower() != ".py":
        raise typer.BadParameter(
            "module_path must point to a .py file",
            param_hint="module_path",
        )

    try:
        parsed = parse_module_logic(module, decorated_only=False)
    except SyntaxError as exc:
        raise typer.BadParameter(
            f"failed to parse Python module: {exc.msg} (line {exc.lineno})",
            param_hint="module_path",
        ) from exc
    except _KNOWN_PARSE_ERRORS as exc:
        raise typer.BadParameter(
            f"failed to parse module: {exc}",
            param_hint="module_path",
        ) from exc

    fmt = format.strip().lower()
    if fmt not in {"mermaid", "dot"}:
        raise typer.BadParameter("format must be one of: mermaid, dot")
    try:
        if fmt == "mermaid":
            text = export_mermaid(parsed, function_name=function)
        else:
            text = export_dot(parsed, function_name=function)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--function") from exc

    if output:
        out_path = Path(output)
        parent = out_path.parent
        if not parent.exists():
            raise typer.BadParameter(
                f"output directory does not exist: {parent}",
                param_hint="--output",
            )
        if out_path.exists() and not force:
            raise typer.BadParameter(
                "output file exists; use --force to overwrite",
                param_hint="--output",
            )

        try:
            out_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise typer.BadParameter(
                f"failed writing output file: {exc}",
                param_hint="--output",
            ) from exc
        typer.echo(f"wrote {fmt} graph to {out_path}")
    else:
        typer.echo(text.rstrip("\n"))


@app.command()
def autotest(
    rule: str = typer.Option(
        ...,
        "--rule",
        help="Rule JSON path.",
    ),
    module: str = typer.Option(
        ...,
        "--module",
        help="Target Python module file.",
    ),
    function: str = typer.Option(
        ...,
        "--function",
        help="Target function name inside module.",
    ),
    generate_pytest: str | None = typer.Option(
        None,
        "--generate-pytest",
        help="Opt-in pytest output path instead of direct execution.",
    ),
    allow_unsafe: bool = typer.Option(
        False,
        "--allow-unsafe",
        help="Allow execution even if function appears ORM/network-bound.",
    ),
    trusted_code: bool = typer.Option(
        False,
        "--trusted-code",
        help="Confirm that importing/executing target module code is trusted.",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Autotest output format: text or json.",
    ),
) -> None:
    """Run generated scenarios and report PASS/FAIL counts."""
    rule_obj = load_rule_flexible(rule)
    if not trusted_code:
        raise typer.BadParameter(
            "autotest imports and executes target function code.",
            param_hint=(
                "pass --trusted-code if you trust the target module"
            ),
        )
    if generate_pytest is not None:
        out = generate_pytest_from_rule(
            module_path=module,
            function_name=function,
            rule=rule_obj,
            output_path=generate_pytest,
        )
        typer.echo(f"generated pytest scenarios: {out}")
        return
    report = autotest_function(
        module_path=module,
        function_name=function,
        rule=rule_obj,
        allow_unsafe=allow_unsafe,
    )
    out_fmt = format.strip().lower()
    if out_fmt == "json":
        payload = {
            "rule": report.rule_id,
            "total": report.total,
            "pass": report.passed,
            "fail": report.failed,
            "truncated": report.truncated,
            "results": [
                {
                    "scenario": r.scenario,
                    "output": None if r.output is None else str(r.output),
                    "passed": r.passed,
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
    elif out_fmt == "text":
        typer.echo(
            "\n".join(
                [
                    "autotest: completed",
                    f"  rule: {report.rule_id}",
                    f"  total: {report.total}",
                    f"  pass: {report.passed}",
                    f"  fail: {report.failed}",
                    f"  truncated: {'yes' if report.truncated else 'no'}",
                ]
            )
        )
    else:
        raise typer.BadParameter("format must be one of: text, json")
    if report.failed > 0:
        raise typer.Exit(code=1)


def _has_scan_findings(stats: dict[str, set[str]]) -> bool:
    return bool(
        stats["missing_rule_metadata_paths"] or stats["unmatched_rule_ids"]
    )


def _scan_rule_stats(
    *,
    root: Path,
    excludes: tuple[str, ...],
    rules_path: str | None,
) -> dict[str, set[str]]:
    detected_rules: set[str] = set()
    missing_rule_metadata_paths: set[str] = set()
    exclude_set = set(excludes)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_set]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = Path(dirpath) / name
            try:
                src = path.read_text(encoding="utf-8")
                if "logic_lock" not in src:
                    continue
                tree = ast.parse(src, filename=str(path))
            except Exception:
                continue
            for node in ast.walk(tree):
                if not isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    continue
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "logic_lock"
                    ):
                        rid = _extract_rule_id(dec)
                        if rid is None:
                            missing_rule_metadata_paths.add(str(path))
                        else:
                            detected_rules.add(rid)
                    elif (
                        isinstance(target, ast.Attribute)
                        and target.attr == "logic_lock"
                    ):
                        rid = _extract_rule_id(dec)
                        if rid is None:
                            missing_rule_metadata_paths.add(str(path))
                        else:
                            detected_rules.add(rid)

    declared_rules: set[str] = set()
    if rules_path is not None:
        for p in sorted(Path(rules_path).rglob("*.json")):
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(raw, dict):
                rid = raw.get("id") or raw.get("rule_id")
                if isinstance(rid, str) and rid:
                    declared_rules.add(rid)
    unmatched_rule_ids = (
        detected_rules - declared_rules
        if declared_rules
        else set()
    )
    return {
        "detected_rules": detected_rules,
        "missing_rule_metadata_paths": missing_rule_metadata_paths,
        "unmatched_rule_ids": unmatched_rule_ids,
    }


def _extract_rule_id(dec: ast.AST) -> str | None:
    if isinstance(dec, ast.Call):
        if dec.args and isinstance(dec.args[0], ast.Constant):
            v = dec.args[0].value
            if isinstance(v, str) and v.strip():
                return v
        for kw in dec.keywords:
            if kw.arg in {"rule", "rule_id"} and isinstance(
                kw.value, ast.Constant
            ):
                v = kw.value.value
                if isinstance(v, str) and v.strip():
                    return v
    return None


def _scan_sarif(root: str, stats: dict[str, set[str]]) -> dict[str, object]:
    rules = [
        {
            "id": "MISSING_RULE_METADATA",
            "shortDescription": {"text": "Missing logic_lock rule id"},
            "fullDescription": {
                "text": (
                    "Decorated function has missing or invalid "
                    "rule metadata."
                )
            },
            "help": {
                "text": (
                    "How to fix: use @logic_lock('rule_id', ...) "
                    "on the function."
                )
            },
        },
        {
            "id": "UNMATCHED_RULE_ID",
            "shortDescription": {"text": "Rule id has no rule file"},
            "fullDescription": {
                "text": (
                    "Detected decorator rule id does not exist "
                    "in rule JSON files."
                )
            },
            "help": {
                "text": (
                    "How to fix: add rule JSON with matching id "
                    "or fix decorator rule id."
                )
            },
        },
    ]
    results: list[dict[str, object]] = []
    for p in sorted(stats["missing_rule_metadata_paths"]):
        results.append(
            {
                "ruleId": "MISSING_RULE_METADATA",
                "level": "error",
                "message": {
                    "text": "Decorated function has missing rule metadata."
                },
                "properties": {
                    "rule_id": "",
                    "severity": "error",
                    "source": "scan",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": p},
                        }
                    }
                ],
            }
        )
    for rid in sorted(stats["unmatched_rule_ids"]):
        results.append(
            {
                "ruleId": "UNMATCHED_RULE_ID",
                "level": "warning",
                "message": {
                    "text": f"Rule id '{rid}' has no matching rule file."
                },
                "properties": {
                    "rule_id": rid,
                    "severity": "warning",
                    "source": "scan",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": root},
                        }
                    }
                ],
            }
        )
    return {
        "version": "2.1.0",
        "$schema": (
            "https://json.schemastore.org/sarif-2.1.0.json"
        ),
        "runs": [
            {
                "tool": {"driver": {"name": "logiclock-scan", "rules": rules}},
                "results": results,
            }
        ],
    }


def _validate_sarif(findings: list[dict[str, str]]) -> dict[str, object]:
    rule_meta: dict[str, dict[str, object]] = {}
    results: list[dict[str, object]] = []
    for f in findings:
        code = f["code"]
        sev = f["severity"]
        if sev == "error":
            level = "error"
        elif sev == "warning":
            level = "warning"
        else:
            level = "note"
        if code not in rule_meta:
            rule_meta[code] = {
                "id": code,
                "shortDescription": {"text": code.replace("_", " ").title()},
                "fullDescription": {"text": f["message"]},
                "help": {
                    "text": (
                        "How to fix: align rule JSON and "
                        "decorator metadata."
                    )
                },
            }
        results.append(
            {
                "ruleId": code,
                "level": level,
                "message": {"text": f["message"].split("\n")[0]},
                "properties": {
                    "rule_id": f["rule_id"],
                    "severity": sev,
                    "source": "validate",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f["path"]},
                        }
                    }
                ],
            }
        )
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "logiclock-validate",
                        "rules": [rule_meta[k] for k in sorted(rule_meta)],
                    }
                },
                "results": results,
            }
        ],
    }


if __name__ == "__main__":
    app()
