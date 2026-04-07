"""Basic Python AST parser for decision points and identifiers (LFL-7)."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .ast_utils import attribute_chain

__all__ = [
    "DecisionPoint",
    "FunctionLogic",
    "ModuleLogicParseResult",
    "parse_module_logic",
]


@dataclass(frozen=True)
class DecisionPoint:
    """Single ``if`` decision site inside a function."""

    line: int
    condition_source: str
    identifiers: tuple[str, ...]
    has_else: bool
    nesting_level: int


@dataclass(frozen=True)
class FunctionLogic:
    """Extracted logic details for one function."""

    name: str
    line: int
    is_decorated_logic_lock: bool
    decision_points: tuple[DecisionPoint, ...]


@dataclass(frozen=True)
class ModuleLogicParseResult:
    """AST parse output for a module file."""

    module_path: str
    functions: tuple[FunctionLogic, ...]


class _IfCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self._depth = 0
        self.items: list[DecisionPoint] = []

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        cond = _safe_unparse(node.test)
        ids = _extract_identifiers(node.test)
        self.items.append(
            DecisionPoint(
                line=getattr(node, "lineno", 0),
                condition_source=cond,
                identifiers=ids,
                has_else=bool(node.orelse),
                nesting_level=self._depth,
            ),
        )
        self._depth += 1
        for stmt in node.body:
            self.visit(stmt)
        self._depth -= 1
        if not node.orelse:
            return
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            # ``elif`` is a nested If in orelse — same chain level, not deeper.
            self.visit(node.orelse[0])
        else:
            self._depth += 1
            for stmt in node.orelse:
                self.visit(stmt)
            self._depth -= 1


def parse_module_logic(
    module_path: str | Path,
    *,
    decorated_only: bool = True,
) -> ModuleLogicParseResult:
    """
    Parse module and return ``if`` decision points per function.

    - ``decorated_only=True``: only functions decorated with ``logic_lock``.
    - ``decorated_only=False``: parse all top-level and nested functions.
    """
    p = Path(module_path)
    source = p.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(p))
    funcs: list[FunctionLogic] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        is_logic = _has_logic_lock_decorator(node)
        if decorated_only and not is_logic:
            continue
        collector = _IfCollector()
        for stmt in node.body:
            collector.visit(stmt)
        funcs.append(
            FunctionLogic(
                name=node.name,
                line=getattr(node, "lineno", 0),
                is_decorated_logic_lock=is_logic,
                decision_points=tuple(collector.items),
            ),
        )
    funcs.sort(key=lambda f: (f.line, f.name))
    return ModuleLogicParseResult(module_path=str(p), functions=tuple(funcs))


def _has_logic_lock_decorator(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name) and target.id == "logic_lock":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "logic_lock":
            return True
    return False


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover
        return "<unparse-failed>"


def _extract_identifiers(expr: ast.AST) -> tuple[str, ...]:
    names: set[str] = set()
    attrs: set[str] = set()
    for n in ast.walk(expr):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            full = attribute_chain(n)
            if full is not None:
                attrs.add(full)
    return tuple(sorted(names | attrs))
