# DRF Example (Order Risk Gate)

This example shows a DRF-style service function that can be called from a
`APIView`/`ViewSet` before order placement.

## Files

- `rules/order_risk_gate.json`
- `orders/services/risk.py`

## Quick run

```bash
logiclock graph examples/drf_orders/orders/services/risk.py --output drf_risk_flow.mmd
```
