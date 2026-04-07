"""Tests for AST-based logic parser (LFL-7)."""

from pathlib import Path

from logiclock.core import parse_module_logic


def _fixture_module() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "sample_module.py"


def test_detects_if_else_for_decorated_function() -> None:
    result = parse_module_logic(_fixture_module(), decorated_only=True)
    assert len(result.functions) == 1
    fn = result.functions[0]
    assert fn.name == "apply_discount"
    assert fn.is_decorated_logic_lock is True
    assert len(fn.decision_points) == 2

    top = fn.decision_points[0]
    assert top.condition_source == "user.is_premium"
    assert top.has_else is True
    assert top.nesting_level == 0
    assert "user.is_premium" in top.identifiers
    assert "user" in top.identifiers


def test_nested_if_and_identifiers_match_expected_set() -> None:
    result = parse_module_logic(_fixture_module(), decorated_only=True)
    fn = result.functions[0]
    inner = fn.decision_points[1]
    assert inner.condition_source == "cart.total > 100"
    assert inner.has_else is False
    assert inner.nesting_level == 1
    assert set(inner.identifiers) == {"cart", "cart.total"}


def test_module_mode_includes_non_decorated_functions() -> None:
    result = parse_module_logic(_fixture_module(), decorated_only=False)
    names = {f.name for f in result.functions}
    assert "apply_discount" in names
    assert "plain_check" in names
    plain = next(f for f in result.functions if f.name == "plain_check")
    assert len(plain.decision_points) == 1
    assert plain.decision_points[0].condition_source == "user.is_staff"


def test_elif_chain_reports_flat_nesting_levels(tmp_path) -> None:
    """``elif`` is one If per orelse; depth must not climb along the chain."""
    src = '''
from logiclock.decorators import logic_lock

@logic_lock("chain")
def classify(u):
    if u.a:
        return 1
    elif u.b:
        return 2
    elif u.c:
        return 3
    return 0
'''
    path = tmp_path / "elif_chain.py"
    path.write_text(src, encoding="utf-8")
    result = parse_module_logic(path, decorated_only=True)
    assert len(result.functions) == 1
    dps = result.functions[0].decision_points
    assert len(dps) == 3
    assert [dp.nesting_level for dp in dps] == [0, 0, 0]
    assert [dp.condition_source for dp in dps] == ["u.a", "u.b", "u.c"]
