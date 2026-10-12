from .base import register
from ..models import Invoice, JobLog
from ..db import get_session
from ..security import current_org_id
from ..connectors import stripe_conn, quickbooks

@register("create_invoice")
def create_invoice(payload, request=None):
    org_id = current_org_id(request)
    with get_session() as s:
        inv = Invoice(org_id=org_id, to_name=payload.get("to_name",""), description=payload.get("description",""),
                      amount=float(payload.get("amount",0.0)))
        s.add(inv); s.commit(); s.refresh(inv)
        try:
            stripe_res = stripe_conn.create_invoice(org_id, request.session.get('uid'), inv.to_name, float(inv.amount), inv.description)
            s.add(JobLog(org_id=org_id, event='stripe_invoice', status='ok' if stripe_res.get('ok') else 'fail', details=str(stripe_res)))
            link_res = stripe_conn.create_payment_link(org_id, request.session.get('uid'), inv.to_name, float(inv.amount), inv.description)
            s.add(JobLog(org_id=org_id, event='stripe_payment_link', status='ok' if link_res.get('ok') else 'fail', details=str(link_res)))
            try:
                session = (link_res.get('data') or {})
                inv.stripe_checkout_url = session.get('url')
                inv.stripe_checkout_id = session.get('id')
                inv.stripe_checkout_status = session.get('status')
                inv.stripe_payment_status = session.get('payment_status')
                s.add(inv)
            except Exception:
                pass
        except Exception as e:
            s.add(JobLog(org_id=org_id, event='stripe_error', status='fail', details=str(e)))
        try:
            qb_customer = quickbooks.create_customer(org_id, request.session.get('uid'), inv.to_name)
            if qb_customer.get('ok'):
                cid = qb_customer['data']['Customer']['Id']
                qb_inv = quickbooks.create_invoice(org_id, request.session.get('uid'), cid, float(inv.amount), inv.description, item_name=inv.description)
                s.add(JobLog(org_id=org_id, event='qb_invoice', status='ok' if qb_inv.get('ok') else 'fail', details=str(qb_inv)))
            else:
                s.add(JobLog(org_id=org_id, event='qb_customer', status='fail', details=str(qb_customer)))
            s.commit()
        except Exception as e:
            s.add(JobLog(org_id=org_id, event='qb_error', status='fail', details=str(e))); s.commit()
        return {"ok": True, "created_id": inv.id, "model":"invoice"}

@register("show_invoices")
def show_invoices(_payload, request=None):
    return {"ok": True}
