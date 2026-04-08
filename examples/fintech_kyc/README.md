# Fintech Example (KYC Transfer Limit)

This example models KYC-based transfer limit checks that are common in fintech
approval flows.

## Files

- `rules/kyc_transfer_limit.json` - declared rule metadata
- `payments/services/kyc.py` - DRF/Django-compatible service logic

## Quick run

```bash
pip install pylogiclock
logiclock graph examples/fintech_kyc/payments/services/kyc.py --format dot --output kyc_flow.dot
```
