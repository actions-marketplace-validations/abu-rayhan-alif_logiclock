# Celery Example (Fraud Queue Gate)

Use `@logic_lock` in task-routing helpers used by Celery workers.

## Files

- `rules/fraud_queue_gate.json`
- `worker/services/routing.py`

## Quick run

```bash
logiclock graph examples/celery_fraud/worker/services/routing.py --output celery_fraud_flow.mmd
```
