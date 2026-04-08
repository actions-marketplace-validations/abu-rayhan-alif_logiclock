"""Fintech KYC transfer approval example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "kyc_transfer_limit",
    result="approved",
    conditions=[
        "user.kyc_level in ['basic', 'full']",
        "amount <= user.daily_limit",
    ],
)
def approve_transfer(user, amount: float) -> str:
    if user.kyc_level not in {"basic", "full"}:
        return "manual_review"
    if amount <= user.daily_limit:
        return "approved"
    return "blocked_limit_exceeded"
