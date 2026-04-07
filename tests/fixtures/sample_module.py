from logiclock.decorators import logic_lock


@logic_lock("premium_discount")
def apply_discount(user, cart):
    "fixture function"
    if user.is_premium:
        if cart.total > 100:
            return "discount=10"
        return "discount=5"
    else:
        return "discount=0"


def plain_check(user):
    if user.is_staff:
        return True
    return False
