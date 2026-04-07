"""Match schema conditions against code conditions with normalization."""

from __future__ import annotations

import ast
from difflib import SequenceMatcher
from dataclasses import dataclass

from .ast_utils import attribute_chain

__all__ = [
    "ConditionMatchResult",
    "MissingCondition",
    "match_conditions",
    "normalize_condition_expression",
]


@dataclass(frozen=True)
class MissingCondition:
    """Schema condition not found in implementation conditions."""

    schema_condition: str
    suggested_code_condition: str | None


@dataclass(frozen=True)
class ConditionMatchResult:
    """Result of condition matching after normalization."""

    matched_schema_conditions: tuple[str, ...]
    missing_schema_conditions: tuple[MissingCondition, ...]

    @property
    def complete_match(self) -> bool:
        return not self.missing_schema_conditions


def match_conditions(
    schema_conditions: list[str],
    code_conditions: list[str],
) -> ConditionMatchResult:
    normalized_code = {
        normalize_condition_expression(c): c for c in code_conditions
    }
    matched: list[str] = []
    missing: list[MissingCondition] = []
    unmatched_code = set(code_conditions)

    for schema in schema_conditions:
        ns = normalize_condition_expression(schema)
        if ns in normalized_code:
            matched.append(schema)
            unmatched_code.discard(normalized_code[ns])
            continue
        suggestion = _best_suggestion(schema, list(unmatched_code))
        missing.append(
            MissingCondition(
                schema_condition=schema,
                suggested_code_condition=suggestion,
            ),
        )
    return ConditionMatchResult(
        matched_schema_conditions=tuple(matched),
        missing_schema_conditions=tuple(missing),
    )


def normalize_condition_expression(expr: str) -> str:
    """
    Best-effort normalization for condition strings.

    Example: ``100 < user.balance`` and ``user.balance > 100`` normalize
    to the same canonical representation.
    """
    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        return " ".join(expr.split())
    normalized = _NormalizeTransformer().visit(node)
    ast.fix_missing_locations(normalized)
    try:
        return ast.unparse(normalized.body)  # type: ignore[attr-defined]
    except Exception:
        return " ".join(expr.split())


class _NormalizeTransformer(ast.NodeTransformer):
    _INVERT_OPS: dict[type[ast.cmpop], type[ast.cmpop]] = {
        ast.Lt: ast.Gt,
        ast.Gt: ast.Lt,
        ast.LtE: ast.GtE,
        ast.GtE: ast.LtE,
    }

    def visit_Compare(self, node: ast.Compare) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)  # type: ignore[assignment]
        if len(node.ops) != 1 or len(node.comparators) != 1:
            return node
        op = node.ops[0]
        left = node.left
        right = node.comparators[0]
        is_invertible = type(op) in self._INVERT_OPS
        if is_invertible and _is_constant(left) and not _is_constant(right):
            inv = self._INVERT_OPS[type(op)]()
            return ast.Compare(left=right, ops=[inv], comparators=[left])
        if isinstance(op, (ast.Eq, ast.NotEq)):
            lu = ast.unparse(left)
            ru = ast.unparse(right)
            if lu > ru:
                return ast.Compare(left=right, ops=[op], comparators=[left])
        return node


def _is_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant)


def _best_suggestion(schema: str, code_conditions: list[str]) -> str | None:
    if not code_conditions:
        return None
    schema_tokens = _identifier_tokens(schema)
    best: tuple[int, str] | None = None
    for c in code_conditions:
        score = len(schema_tokens & _identifier_tokens(c))
        cand = (score, c)
        if best is None or cand > best:
            best = cand
    if best is not None and best[0] > 0:
        return best[1]
    return max(
        code_conditions,
        key=lambda c: SequenceMatcher(a=schema, b=c).ratio(),
    )


def _identifier_tokens(expr: str) -> set[str]:
    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        return set()
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            chain = attribute_chain(n)
            if chain is not None:
                out.add(chain)
    return out
