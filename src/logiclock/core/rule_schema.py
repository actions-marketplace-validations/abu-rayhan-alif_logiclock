"""Load and validate rule definitions from JSON files or dicts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

__all__ = [
    "Rule",
    "RuleSchemaError",
    "load_rule_from_dict",
    "load_rule_from_json_file",
]


class RuleSchemaError(ValueError):
    """Raised when a rule dict or JSON document does not match the schema."""

    def __init__(self, message: str, *, rule_id: str | None = None) -> None:
        super().__init__(message)
        self.rule_id = rule_id


def _format_validation_errors(errors: list[Any], rule_id: str) -> str:
    parts: list[str] = []
    for err in errors:
        loc = err.get("loc") or ()
        path = ".".join(str(x) for x in loc) if loc else "(root)"
        msg = err.get("msg", "invalid")
        parts.append(f"{path}: {msg}")
    detail = "; ".join(parts)
    return f"Invalid rule schema (rule id: {rule_id}): {detail}"


class Rule(BaseModel):
    """Authoritative rule schema: conditions, result, optional version."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this rule.",
    )
    conditions: list[str] = Field(
        ...,
        description=(
            "Non-empty list of condition expressions evaluated by the engine."
        ),
    )
    result: str = Field(
        ...,
        min_length=1,
        description="Outcome or action when all conditions hold.",
    )
    version: int | None = Field(
        default=None,
        ge=1,
        description="Optional schema version for migration.",
    )

    @field_validator("conditions")
    @classmethod
    def conditions_not_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("conditions must not be empty")
        return value


def load_rule_from_dict(data: dict[str, Any]) -> Rule:
    """
    Validate and return a :class:`Rule` from an in-memory mapping.

    Raises:
        RuleSchemaError: On missing keys, wrong types, empty ``conditions``,
        or extra keys.
    """
    rule_id = data.get("id")
    if isinstance(rule_id, str) and rule_id:
        rule_id_str = rule_id
    else:
        rule_id_str = "<missing or invalid id>"

    try:
        return Rule.model_validate(data)
    except ValidationError as exc:
        known = rule_id_str != "<missing or invalid id>"
        raise RuleSchemaError(
            _format_validation_errors(exc.errors(), rule_id_str),
            rule_id=rule_id_str if known else None,
        ) from exc


def load_rule_from_json_file(path: Path | str) -> Rule:
    """Load a rule from a ``.json`` file (UTF-8)."""
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuleSchemaError(
            "Invalid rule schema (rule id: unknown): "
            f"invalid JSON in {p}: {exc.msg}",
            rule_id=None,
        ) from exc

    if not isinstance(data, dict):
        raise RuleSchemaError(
            "Invalid rule schema (rule id: unknown): "
            f"expected JSON object in {p}, got {type(data).__name__}",
            rule_id=None,
        )

    return load_rule_from_dict(data)
