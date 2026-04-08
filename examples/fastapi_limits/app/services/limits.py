"""FastAPI transfer limit service example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "transfer_limit",
    result="allowed",
    conditions=["account.is_active", "amount <= account.transfer_limit"],
)
def check_transfer_limit(account, amount: float) -> str:
    if not account.is_active:
        return "blocked_inactive"
    if amount <= account.transfer_limit:
        return "allowed"
    return "blocked_limit"
