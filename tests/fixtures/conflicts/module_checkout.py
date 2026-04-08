from logiclock.decorators import logic_lock


@logic_lock(
    "decision_route",
    result="allow_checkout",
    conditions=["user.is_verified", "risk_score < 50"],
)
def checkout_route(user, risk_score):
    if user.is_verified and risk_score < 50:
        return "allow_checkout"
    return "manual_review"
