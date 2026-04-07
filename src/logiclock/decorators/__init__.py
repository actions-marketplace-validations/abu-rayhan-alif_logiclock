"""Decorators for marking and enforcement."""

from logiclock.decorators.logic_lock import (
    LOGICLOCK_META_ATTR,
    get_rule_id,
    get_rule_metadata,
    logic_lock,
    registry_view,
)

__all__ = [
    "LOGICLOCK_META_ATTR",
    "get_rule_id",
    "get_rule_metadata",
    "logic_lock",
    "registry_view",
]
