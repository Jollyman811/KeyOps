from .base import register
from ..models import Invoice
from ..db import get_session

@register("create_invoice")
def create_invoice(payload):
    with get_session() as s:
        inv = Invoice(
            to_name=payload.get("to_name", ""),
            description=payload.get("description", ""),
            amount=float(payload.get("amount", 0.0)),
        )
        s.add(inv)
        s.commit()
        s.refresh(inv)
        return {"ok": True, "created_id": inv.id, "model": "invoice"}

@register("show_invoices")
def show_invoices(_payload):
    return {"ok": True}
