"""Compare implementation hints (metadata-level) to authoritative rule schema.

MVP (LFL-4): string / metadata validation only. AST-based checks are deferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from logiclock.core.condition_matcher import match_conditions
from logiclock.core.rule_schema import Rule

__all__ = [
    "Finding",
    "ImplementationSpec",
    "Severity",
    "ValidationPolicy",
    "findings_include_severity",
    "implementation_spec_from_metadata",
    "validate_implementation_vs_schema",
]


class Severity(str, Enum):
    """Finding severity for validator output and policy knobs."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationPolicy:
    """Per-check severity (MVP defaults match story acceptance)."""

    result_mismatch: Severity = Severity.ERROR
    missing_schema_condition: Severity = Severity.WARNING
    rule_id_mismatch: Severity = Severity.ERROR


@dataclass(frozen=True)
class Finding:
    """Single validation finding."""

    severity: Severity
    code: str
    message: str
    rule_id: str


@dataclass(frozen=True)
class ImplementationSpec:
    """
    Declared hints for one callable or collector row (metadata-level).

    * ``result_declared``: optional concrete ``result`` string (e.g.
      ``discount=10``) when the implementation documents it.
    * ``conditions_declared``: if present (including ``[]``), each schema
      condition must appear in this list (exact string). If ``None``, condition
      subset checks are skipped (collector did not expose conditions).
    """

    rule_id: str
    result_declared: str | None = None
    conditions_declared: list[str] | None = None


def implementation_spec_from_metadata(
    meta: dict[str, Any],
) -> ImplementationSpec:
    """
    Build :class:`ImplementationSpec` from decorator/collector metadata.

    Compatible with :func:`~logiclock.decorators.get_rule_metadata` output.
    """
    rule_id = str(meta["rule_id"])
    result_declared = meta.get("result")
    if result_declared is not None:
        result_declared = str(result_declared)
    conditions_raw = meta.get("conditions", None)
    conditions_declared: list[str] | None
    if conditions_raw is None:
        conditions_declared = None
    elif isinstance(conditions_raw, list):
        conditions_declared = [str(x) for x in conditions_raw]
    else:
        raise TypeError(
            f"logic_lock metadata 'conditions' must be a list or omitted, "
            f"got {type(conditions_raw).__name__}",
        )
    return ImplementationSpec(
        rule_id=rule_id,
        result_declared=result_declared,
        conditions_declared=conditions_declared,
    )


def validate_implementation_vs_schema(
    rule: Rule,
    impl: ImplementationSpec,
    policy: ValidationPolicy | None = None,
) -> list[Finding]:
    """
    Compare declared implementation hints to ``rule`` (schema).

    Returns findings sorted by severity (errors first), then code, message.
    """
    pol = policy or ValidationPolicy()
    findings: list[Finding] = []
    rid = rule.id

    if impl.rule_id != rule.id:
        findings.append(
            Finding(
                severity=pol.rule_id_mismatch,
                code="RULE_ID_MISMATCH",
                message=(
                    f"Implementation rule_id {impl.rule_id!r} does not match "
                    f"schema id {rule.id!r}"
                ),
                rule_id=rid,
            ),
        )

    if (
        impl.result_declared is not None
        and impl.result_declared != rule.result
    ):
        findings.append(
            Finding(
                severity=pol.result_mismatch,
                code="RESULT_MISMATCH",
                message=(
                    f"Declared result {impl.result_declared!r} does not match "
                    f"schema result {rule.result!r}"
                ),
                rule_id=rid,
            ),
        )

    if impl.conditions_declared is not None:
        cond_match = match_conditions(
            rule.conditions,
            impl.conditions_declared,
        )
        for miss in cond_match.missing_schema_conditions:
            hint = ""
            if miss.suggested_code_condition is not None:
                hint = (
                    " Closest implementation condition: "
                    f"{miss.suggested_code_condition!r}."
                )
            findings.append(
                Finding(
                    severity=pol.missing_schema_condition,
                    code="MISSING_SCHEMA_CONDITION",
                    message=(
                        f"Schema condition {miss.schema_condition!r} is not "
                        f"matched in implementation conditions.{hint}"
                    ),
                    rule_id=rid,
                ),
            )

    order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    findings.sort(key=lambda f: (order[f.severity], f.code, f.message))
    return findings


def findings_include_severity(
    findings: list[Finding],
    severity: Severity,
) -> bool:
    """Return True if any finding matches ``severity``."""
    return any(f.severity == severity for f in findings)
