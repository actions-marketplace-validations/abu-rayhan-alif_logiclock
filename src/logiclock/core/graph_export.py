"""Graph exporters for AST-derived logic flow (LFL-11)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from logiclock.core.ast_parser import (
    FunctionLogic,
    ModuleLogicParseResult,
)

__all__ = [
    "export_dot",
    "export_mermaid",
    "graphviz_is_available",
    "render_dot_with_graphviz",
]


def export_mermaid(
    parsed: ModuleLogicParseResult,
    *,
    function_name: str | None = None,
) -> str:
    """Export function/module logic as Mermaid flowchart text."""
    functions = _select_functions(parsed, function_name=function_name)
    lines = ["flowchart TD"]

    for fn in functions:
        root_id = _function_node_id(fn)
        lines.append(f'  {root_id}["{_escape_mermaid_label(fn.name)}()"]')
        for i, dp in enumerate(fn.decision_points, start=1):
            dp_id = f"{root_id}_if_{i}"
            condition = _escape_mermaid_label(dp.condition_source)
            lines.append(f'  {dp_id}{{"{condition}"}}')
            if i == 1:
                lines.append(f"  {root_id} --> {dp_id}")
            else:
                prev_id = f"{root_id}_if_{i - 1}"
                lines.append(f"  {prev_id} -->|next| {dp_id}")
            lines.append(
                f"  {dp_id} -->|depth={dp.nesting_level}| {root_id}"
            )

    return "\n".join(lines) + "\n"


def export_dot(
    parsed: ModuleLogicParseResult,
    *,
    function_name: str | None = None,
) -> str:
    """Export function/module logic as Graphviz DOT text."""
    functions = _select_functions(parsed, function_name=function_name)
    lines = [
        "digraph LogicFlow {",
        "  rankdir=TB;",
        '  node [fontname="Arial"];',
    ]
    for fn in functions:
        root_id = _function_node_id(fn)
        fn_label = _escape_dot_label(fn.name)
        lines.append(f'  {root_id} [shape=box, label="{fn_label}()"];')
        for i, dp in enumerate(fn.decision_points, start=1):
            dp_id = f"{root_id}_if_{i}"
            condition = _escape_dot_label(dp.condition_source)
            lines.append(
                f'  {dp_id} [shape=diamond, label="{condition}"];'
            )
            if i == 1:
                lines.append(f"  {root_id} -> {dp_id};")
            else:
                prev_id = f"{root_id}_if_{i - 1}"
                lines.append(f'  {prev_id} -> {dp_id} [label="next"];')
            lines.append(
                f'  {dp_id} -> {root_id} [label="depth={dp.nesting_level}"];'
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def graphviz_is_available() -> bool:
    """Return whether Graphviz 'dot' binary is installed."""
    return shutil.which("dot") is not None


def render_dot_with_graphviz(
    dot_text: str,
    *,
    output_path: str | Path,
    output_format: str = "svg",
    timeout_seconds: float = 10.0,
) -> Path:
    """Render DOT text to a file via Graphviz if available."""
    if not graphviz_is_available():
        raise RuntimeError("Graphviz is not installed (missing 'dot' binary).")
    out = Path(output_path)
    try:
        proc = subprocess.run(
            ["dot", f"-T{output_format}", "-o", str(out)],
            input=dot_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Graphviz rendering timed out after {timeout_seconds} seconds."
        ) from exc
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Graphviz rendering failed.")
    return out


def _select_functions(
    parsed: ModuleLogicParseResult,
    *,
    function_name: str | None,
) -> tuple[FunctionLogic, ...]:
    if function_name is None:
        return parsed.functions
    selected = tuple(f for f in parsed.functions if f.name == function_name)
    if not selected:
        raise ValueError(
            f"Function '{function_name}' not found in parsed module."
        )
    return selected


def _escape_dot_label(label: str) -> str:
    escaped = label.replace("\\", "\\\\")
    escaped = escaped.replace("\n", "\\n").replace("\r", "")
    return escaped.replace('"', '\\"')


def _escape_mermaid_label(label: str) -> str:
    escaped = label.replace("&", "&amp;")
    escaped = escaped.replace('"', "&quot;")
    escaped = escaped.replace("\r", "")
    return escaped.replace("\n", "<br/>")


def _function_node_id(fn: FunctionLogic) -> str:
    """Return stable node id, unique even for duplicate function names."""
    return f"fn_{fn.name}_{fn.line}"
