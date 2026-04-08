"""Flask checkout eligibility service example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "checkout_eligibility",
    result="eligible",
    conditions=["user.is_active", "cart.total > 0"],
)
def can_checkout(user, cart) -> bool:
    if not user.is_active:
        return False
    if cart.total > 0:
        return True
    return False
