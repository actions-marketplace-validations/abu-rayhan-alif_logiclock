"""Plain Python feature gate example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "feature_gate",
    result="enabled",
    conditions=["tenant.is_paid", "feature_name in tenant.enabled_features"],
)
def is_feature_enabled(tenant, feature_name: str) -> bool:
    if not tenant.is_paid:
        return False
    if feature_name in tenant.enabled_features:
        return True
    return False
