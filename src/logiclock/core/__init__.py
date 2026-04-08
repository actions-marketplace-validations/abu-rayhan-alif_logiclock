"""Core scanning and validation engine."""

from logiclock.core.rule_conflicts import (
    DeclaredResultConflict,
    OverlappingPredicateConflict,
    detect_overlapping_predicate_conflicts,
    detect_declared_result_conflicts,
    format_overlapping_predicate_conflict,
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
from logiclock.core.auto_test import (
    AutoTestReport,
    ScenarioResult,
    autotest_function,
    generate_pytest_from_rule,
    is_likely_unsafe_for_execution,
    load_rule_flexible,
)
from logiclock.core.config import LogiclockConfig, load_logiclock_config
from logiclock.core.edge_case_generator import (
    ScenarioGenerationConfig,
    ScenarioGenerationResult,
    generate_scenarios_from_conditions,
)
from logiclock.core.graph_export import (
    export_dot,
    export_mermaid,
    graphviz_is_available,
    render_dot_with_graphviz,
)
from logiclock.core.rule_schema import (
    Rule,
    RuleSchemaError,
    load_rule_from_dict,
    load_rule_from_json_file,
)
from logiclock.core.scanner import (
    DEFAULT_CACHE_FILE,
    DEFAULT_EXCLUDES,
    ScanSummary,
    scan_repository,
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
    "AutoTestReport",
    "DeclaredResultConflict",
    "LogiclockConfig",
    "OverlappingPredicateConflict",
    "Finding",
    "FunctionLogic",
    "ImplementationSpec",
    "MissingCondition",
    "ModuleLogicParseResult",
    "Rule",
    "RuleSchemaError",
    "RuleUsageSite",
    "ScenarioResult",
    "ScanSummary",
    "Severity",
    "DEFAULT_CACHE_FILE",
    "DEFAULT_EXCLUDES",
    "ScenarioGenerationConfig",
    "ScenarioGenerationResult",
    "ValidationPolicy",
    "clear_rule_usage_sites",
    "autotest_function",
    "load_logiclock_config",
    "detect_declared_result_conflicts",
    "detect_overlapping_predicate_conflicts",
    "export_dot",
    "export_mermaid",
    "findings_include_severity",
    "format_declared_result_conflict",
    "format_overlapping_predicate_conflict",
    "graphviz_is_available",
    "generate_pytest_from_rule",
    "implementation_spec_from_metadata",
    "iter_rule_usage_sites",
    "load_rule_from_dict",
    "load_rule_flexible",
    "load_rule_from_json_file",
    "match_conditions",
    "normalize_condition_expression",
    "parse_module_logic",
    "generate_scenarios_from_conditions",
    "is_likely_unsafe_for_execution",
    "record_rule_usage_from_callable",
    "render_dot_with_graphviz",
    "scan_repository",
    "validate_implementation_vs_schema",
]
