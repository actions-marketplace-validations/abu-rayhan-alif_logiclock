"""Celery routing helper example."""

from logiclock.decorators import logic_lock


@logic_lock(
    "fraud_queue_gate",
    result="send_review_queue",
    conditions=["transaction.amount > 5000", "transaction.risk_score >= 80"],
)
def route_transaction(transaction) -> str:
    if transaction.amount > 5000:
        if transaction.risk_score >= 80:
            return "review_queue"
    return "normal_queue"
