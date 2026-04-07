"""Generate boundary/value scenarios from rule condition expressions."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from itertools import product
from typing import Protocol

from .ast_utils import attribute_chain

__all__ = [
    "ScenarioGenerationConfig",
    "ScenarioGenerationResult",
    "generate_scenarios_from_conditions",
]


class ConditionScenarioGenerator(Protocol):
    """Pluggable condition-to-candidate generator."""

    def generate(self, expr: str) -> tuple[str, list[object]] | None:
        """Return target field and candidate values, or None if unsupported."""


@dataclass(frozen=True)
class ScenarioGenerationConfig:
    """Controls scenario volume to avoid Cartesian explosion."""

    max_combinations: int = 50


@dataclass(frozen=True)
class ScenarioGenerationResult:
    """Generated scenarios and metadata for reporting."""

    scenarios: tuple[dict[str, object], ...]
    total_possible_combinations: int
    truncated: bool


class ComparisonBoundaryGenerator:
    """Generate n-1, n, n+1 around numeric comparison boundary."""

    def generate(self, expr: str) -> tuple[str, list[object]] | None:
        try:
            node = ast.parse(expr, mode="eval").body
        except SyntaxError:
            return None
        if not isinstance(node, ast.Compare):
            return None
        if len(node.ops) != 1 or len(node.comparators) != 1:
            return None
        left = node.left
        right = node.comparators[0]
        if isinstance(left, (ast.Name, ast.Attribute)) and _num_const(right):
            field = _name_or_attr_field(left)
            if field is None:
                return None
            n = _num_value(right)
            return (field, _boundary_values(n))
        if isinstance(right, (ast.Name, ast.Attribute)) and _num_const(left):
            field = _name_or_attr_field(right)
            if field is None:
                return None
            n = _num_value(left)
            return (field, _boundary_values(n))
        return None


class BooleanFlagGenerator:
    """Generate True/False for boolean-like name/attribute conditions."""

    def generate(self, expr: str) -> tuple[str, list[object]] | None:
        try:
            body = ast.parse(expr, mode="eval").body
        except SyntaxError:
            return None
        if isinstance(body, ast.Name):
            return (body.id, [True, False])
        if isinstance(body, ast.Attribute):
            field = _name_or_attr_field(body)
            if field is None:
                return None
            return (field, [True, False])
        if isinstance(body, ast.UnaryOp) and isinstance(body.op, ast.Not):
            inner = body.operand
            if isinstance(inner, ast.Name):
                return (inner.id, [True, False])
            if isinstance(inner, ast.Attribute):
                field = _name_or_attr_field(inner)
                if field is None:
                    return None
                return (field, [True, False])
        return None


_DEFAULT_GENERATORS: tuple[ConditionScenarioGenerator, ...] = (
    ComparisonBoundaryGenerator(),
    BooleanFlagGenerator(),
)


def generate_scenarios_from_conditions(
    conditions: list[str],
    *,
    config: ScenarioGenerationConfig | None = None,
    generators: tuple[ConditionScenarioGenerator, ...] = _DEFAULT_GENERATORS,
) -> ScenarioGenerationResult:
    """
    Build scenario dicts from conditions with a max Cartesian combination cap.

    Unsupported conditions are skipped in this basic version.
    """
    cfg = config or ScenarioGenerationConfig()
    axes: list[tuple[str, list[object]]] = []
    for cond in conditions:
        axis: tuple[str, list[object]] | None = None
        for gen in generators:
            axis = gen.generate(cond)
            if axis is not None:
                break
        if axis is not None:
            axes.append(axis)

    if not axes:
        return ScenarioGenerationResult(
            scenarios=tuple(),
            total_possible_combinations=0,
            truncated=False,
        )

    fields = [f for f, _ in axes]
    value_sets = [vals for _, vals in axes]
    total = 1
    for vals in value_sets:
        total *= len(vals)

    rows: list[dict[str, object]] = []
    for values in product(*value_sets):
        row = dict(zip(fields, values, strict=False))
        rows.append(row)
        if len(rows) >= cfg.max_combinations:
            break
    return ScenarioGenerationResult(
        scenarios=tuple(rows),
        total_possible_combinations=total,
        truncated=total > len(rows),
    )


def _boundary_values(n: float | int) -> list[object]:
    if isinstance(n, int):
        return [n - 1, n, n + 1]
    eps = 0.01
    return [round(n - eps, 6), n, round(n + eps, 6)]


def _num_const(node: ast.AST) -> bool:
    if not isinstance(node, ast.Constant):
        return False
    v = node.value
    # bool is a subclass of int; exclude it from numeric boundaries.
    if isinstance(v, bool):
        return False
    return isinstance(v, (int, float))


def _num_value(node: ast.AST) -> float | int:
    assert isinstance(node, ast.Constant)
    v = node.value
    assert not isinstance(v, bool) and isinstance(v, (int, float))
    return v


def _name_or_attr_field(node: ast.Name | ast.Attribute) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return attribute_chain(node)
