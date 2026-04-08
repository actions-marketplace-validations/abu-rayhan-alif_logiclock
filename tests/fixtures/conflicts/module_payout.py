from logiclock.decorators import logic_lock


@logic_lock(
    "decision_route",
    result="block_payout",
    conditions=["user.is_verified", "daily_limit_exceeded"],
)
def payout_route(user, daily_limit_exceeded):
    if user.is_verified and daily_limit_exceeded:
        return "block_payout"
    return "allow_payout"
