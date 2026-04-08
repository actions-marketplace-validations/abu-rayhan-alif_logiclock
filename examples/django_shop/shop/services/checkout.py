"""Django-style checkout service example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "checkout_discount",
    result="discount_applied",
    conditions=["user.is_premium", "cart.total >= 100"],
)
def calculate_discount(user, cart) -> int:
    if user.is_premium:
        if cart.total >= 100:
            return 15
        return 5
    return 0
