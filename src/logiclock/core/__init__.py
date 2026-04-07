"""Core scanning and validation engine."""

from logiclock.core.rule_conflicts import (
    DeclaredResultConflict,
    detect_declared_result_conflicts,
    format_declared_result_conflict,
)
from logiclock.core.ast_parser import (
    DecisionPoint,
    FunctionLogic,
    ModuleLogicParseResult,
    parse_module_logic,
)
from logiclock.core.condition_matcher import (
    ConditionMatchResult,
    MissingCondition,
    match_conditions,
    normalize_condition_expression,
)
from logiclock.core.edge_case_generator import (
    ScenarioGenerationConfig,
    ScenarioGenerationResult,
    generate_scenarios_from_conditions,
)
from logiclock.core.rule_schema import (
    Rule,
    RuleSchemaError,
    load_rule_from_dict,
    load_rule_from_json_file,
)
from logiclock.core.rule_usage import (
    RuleUsageSite,
    clear_rule_usage_sites,
    iter_rule_usage_sites,
    record_rule_usage_from_callable,
)
from logiclock.core.rule_validator import (
    Finding,
    ImplementationSpec,
    Severity,
    ValidationPolicy,
    findings_include_severity,
    implementation_spec_from_metadata,
    validate_implementation_vs_schema,
)

__all__ = [
    "DecisionPoint",
    "ConditionMatchResult",
    "DeclaredResultConflict",
    "Finding",
    "FunctionLogic",
    "ImplementationSpec",
    "MissingCondition",
    "ModuleLogicParseResult",
    "Rule",
    "RuleSchemaError",
    "RuleUsageSite",
    "Severity",
    "ScenarioGenerationConfig",
    "ScenarioGenerationResult",
    "ValidationPolicy",
    "clear_rule_usage_sites",
    "detect_declared_result_conflicts",
    "findings_include_severity",
    "format_declared_result_conflict",
    "implementation_spec_from_metadata",
    "iter_rule_usage_sites",
    "load_rule_from_dict",
    "load_rule_from_json_file",
    "match_conditions",
    "normalize_condition_expression",
    "parse_module_logic",
    "generate_scenarios_from_conditions",
    "record_rule_usage_from_callable",
    "validate_implementation_vs_schema",
]
