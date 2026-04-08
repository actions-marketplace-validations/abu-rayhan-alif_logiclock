# Django Shop Example (Checkout Discount)

This example shows how to annotate checkout pricing logic with `@logic_lock`
metadata so rule files and implementation stay aligned.

## Files

- `rules/checkout_discount.json` - rule source of truth
- `shop/services/checkout.py` - Django-style service function

## Quick run

```bash
pip install pylogiclock
logiclock graph examples/django_shop/shop/services/checkout.py --output checkout_flow.mmd
```

The generated Mermaid flow can be rendered in Mermaid Live Editor or in an IDE
with Mermaid support.
