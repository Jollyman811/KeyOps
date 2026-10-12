from __future__ import annotations
import requests
from typing import Optional
from ..db import get_session
from ..models import OAuthAccount

STRIPE_API = "https://api.stripe.com/v1"

def _get_stripe_token(org_id: int, user_id: int) -> Optional[str]:
    with get_session() as s:
        rec = s.query(OAuthAccount).filter(OAuthAccount.org_id==org_id, OAuthAccount.user_id==user_id, OAuthAccount.provider=="stripe").order_by(OAuthAccount.created_at.desc()).first()
        return rec.access_token if rec else None

def _post(path: str, token: str, data: dict):
    r = requests.post(f"{STRIPE_API}{path}", headers={"Authorization": f"Bearer {token}"}, data=data, timeout=30)
    r.raise_for_status()
    return r.json()

def create_invoice(org_id: int, user_id: int, to_name: str, amount_usd: float, description: str, currency: str="usd"):
    token = _get_stripe_token(org_id, user_id)
    if not token:
        return {"ok": False, "error": "No Stripe OAuth token"}
    cust = _post("/customers", token, {"name": to_name})
    cents = int(round(amount_usd * 100))
    _post("/invoiceitems", token, {"customer": cust["id"], "amount": cents, "currency": currency, "description": description})
    inv = _post("/invoices", token, {"customer": cust["id"], "auto_advance": "true"})
    inv_final = _post(f"/invoices/{inv['id']}/finalize", token, {})
    return {"ok": True, "data": inv_final}

def create_payment_link(org_id: int, user_id: int, name: str, amount_usd: float, description: str, currency: str="usd", success_url: str="http://127.0.0.1:8009/success", cancel_url: str="http://127.0.0.1:8009/cancel"):
    token = _get_stripe_token(org_id, user_id)
    if not token:
        return {"ok": False, "error": "No Stripe OAuth token"}
    cents = int(round(amount_usd * 100))
    body = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price_data][currency]": currency,
        "line_items[0][price_data][unit_amount]": str(cents),
        "line_items[0][price_data][product_data][name]": name,
        "line_items[0][price_data][product_data][description]": description,
        "line_items[0][quantity]": "1"
    }
    r = requests.post(f"{STRIPE_API}/checkout/sessions", headers={"Authorization": f"Bearer {token}"}, data=body, timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}

def get_checkout_session(org_id: int, user_id: int, session_id: str):
    token = _get_stripe_token(org_id, user_id)
    if not token:
        return {"ok": False, "error": "No Stripe OAuth token"}
    r = requests.get(f"{STRIPE_API}/checkout/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}
