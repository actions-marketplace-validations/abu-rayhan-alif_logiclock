"""Graph export tests for visual logic flow (LFL-11)."""

from pathlib import Path

import pytest

from logiclock.core import (
    DecisionPoint,
    FunctionLogic,
    ModuleLogicParseResult,
    export_dot,
    export_mermaid,
    graphviz_is_available,
    parse_module_logic,
    render_dot_with_graphviz,
)

_FIXTURE_MODULE = (
    Path(__file__).resolve().parent / "fixtures" / "sample_module.py"
)
_SNAP_MERMAID = (
    Path(__file__).resolve().parent / "snapshots" / "graph_fixture_module.mmd"
)
_SNAP_DOT = (
    Path(__file__).resolve().parent / "snapshots" / "graph_fixture_module.dot"
)


def test_mermaid_export_matches_snapshot() -> None:
    parsed = parse_module_logic(_FIXTURE_MODULE, decorated_only=False)
    expected = _SNAP_MERMAID.read_text(encoding="utf-8")
    assert export_mermaid(parsed) == expected


def test_mermaid_output_has_renderable_shape() -> None:
    parsed = parse_module_logic(_FIXTURE_MODULE, decorated_only=False)
    text = export_mermaid(parsed)
    assert text.startswith("flowchart TD")
    assert '{"' in text
    assert "-->" in text


def test_dot_export_matches_snapshot() -> None:
    parsed = parse_module_logic(_FIXTURE_MODULE, decorated_only=False)
    expected = _SNAP_DOT.read_text(encoding="utf-8")
    assert export_dot(parsed) == expected


def test_function_filter_only_exports_one_function() -> None:
    parsed = parse_module_logic(_FIXTURE_MODULE, decorated_only=False)
    out = export_mermaid(parsed, function_name="plain_check")
    assert "plain_check()" in out
    assert "apply_discount()" not in out


def test_duplicate_function_names_use_distinct_node_ids() -> None:
    parsed = ModuleLogicParseResult(
        module_path="x.py",
        functions=(
            FunctionLogic(
                name="save",
                line=10,
                is_decorated_logic_lock=False,
                decision_points=(),
            ),
            FunctionLogic(
                name="save",
                line=42,
                is_decorated_logic_lock=False,
                decision_points=(),
            ),
        ),
    )
    mermaid = export_mermaid(parsed)
    dot = export_dot(parsed)
    assert 'fn_save_10["save()"]' in mermaid
    assert 'fn_save_42["save()"]' in mermaid
    assert 'fn_save_10 [shape=box, label="save()"];' in dot
    assert 'fn_save_42 [shape=box, label="save()"];' in dot


def test_graphviz_render_is_optional_when_installed(tmp_path: Path) -> None:
    if not graphviz_is_available():
        pytest.skip("Graphviz not installed in this environment")
    parsed = parse_module_logic(_FIXTURE_MODULE, decorated_only=False)
    dot_text = export_dot(parsed)
    out = tmp_path / "graph.svg"
    render_dot_with_graphviz(dot_text, output_path=out, output_format="svg")
    assert out.exists()


def test_mermaid_and_dot_labels_use_format_specific_escaping() -> None:
    parsed = ModuleLogicParseResult(
        module_path="x.py",
        functions=(
            FunctionLogic(
                name="f",
                line=1,
                is_decorated_logic_lock=False,
                decision_points=(
                    DecisionPoint(
                        line=2,
                        condition_source='user.role == "admin"\nactive',
                        identifiers=(),
                        has_else=False,
                        nesting_level=0,
                    ),
                ),
            ),
        ),
    )
    mermaid = export_mermaid(parsed)
    dot = export_dot(parsed)
    assert "&quot;admin&quot;" in mermaid
    assert "<br/>active" in mermaid
    assert '\\"admin\\"' in dot
    assert "\\nactive" in dot


def test_duplicate_function_names_get_unique_node_ids() -> None:
    parsed = ModuleLogicParseResult(
        module_path="x.py",
        functions=(
            FunctionLogic(
                name="save",
                line=10,
                is_decorated_logic_lock=False,
                decision_points=(),
            ),
            FunctionLogic(
                name="save",
                line=40,
                is_decorated_logic_lock=False,
                decision_points=(),
            ),
        ),
    )
    mermaid = export_mermaid(parsed)
    dot = export_dot(parsed)
    assert 'fn_save_10["save()"]' in mermaid
    assert 'fn_save_40["save()"]' in mermaid
    assert 'fn_save_10 [shape=box, label="save()"];' in dot
    assert 'fn_save_40 [shape=box, label="save()"];' in dot
