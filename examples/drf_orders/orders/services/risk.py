"""DRF order risk service example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "order_risk_gate",
    result="approved",
    conditions=["user.is_verified", "risk_score < 70"],
)
def approve_order(user, risk_score: int) -> str:
    if not user.is_verified:
        return "manual_review"
    if risk_score < 70:
        return "approved"
    return "blocked_risk"
