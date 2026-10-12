from __future__ import annotations
import requests, json, base64
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
from ..db import get_session
from ..models import OAuthAccount, JobLog
from ..config import settings

BASE = "https://quickbooks.api.intuit.com/v3/company"

def _refresh_intuit(rec):
    if not rec.refresh_token: return None
    b64 = base64.b64encode(f"{settings.INTUIT_CLIENT_ID}:{settings.INTUIT_CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {b64}", "Content-Type":"application/x-www-form-urlencoded"}
    data = {"grant_type":"refresh_token","refresh_token":rec.refresh_token}
    r = requests.post("https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer", headers=headers, data=data, timeout=30)
    if r.status_code >= 400:
        try:
            with get_session() as s:
                s.add(JobLog(org_id=rec.org_id, event="oauth_refresh_intuit", status="fail", details=str(r.text)))
                s.commit()
        except Exception:
            pass
        return None
    info = r.json()
    new_token = info.get("access_token")
    expires_in = int(info.get("expires_in", 3600))
    with get_session() as s:
        dbrec = s.get(OAuthAccount, rec.id)
        dbrec.access_token = new_token or dbrec.access_token
        dbrec.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        s.add(dbrec); s.add(JobLog(org_id=dbrec.org_id, event="oauth_refresh_intuit", status="ok", details=f"expires_in={expires_in}")); s.commit()
    return new_token

def _get_intuit(org_id: int, user_id: int) -> Tuple[Optional[str], Optional[str]]:
    with get_session() as s:
        rec = s.query(OAuthAccount).filter(OAuthAccount.org_id==org_id, OAuthAccount.user_id==user_id, OAuthAccount.provider=="intuit").order_by(OAuthAccount.created_at.desc()).first()
    if not rec: return None, None
    token = rec.access_token
    if not rec.expires_at or rec.expires_at <= datetime.utcnow() + timedelta(minutes=2):
        tok = _refresh_intuit(rec)
        token = tok or token
    realm_id = rec.scope  # we store realmId in scope
    return token, realm_id

def _headers(token: str):
    return {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

def _query(token: str, realm: str, q: str):
    url = f"{BASE}/{realm}/query"
    params = {"query": q}
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/text"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}

def find_income_account(token: str, realm: str) -> Optional[str]:
    res = _query(token, realm, "select * from Account where AccountType = 'Income' maxresults 1")
    if not res.get("ok"): return None
    accs = res["data"].get("QueryResponse", {}).get("Account", [])
    if not accs: return None
    return accs[0].get("Id")

def find_item_by_name(token: str, realm: str, name: str) -> Optional[Dict]:
    name_q = name.replace('"', '\"')
    res = _query(token, realm, f'select * from Item where Name = "{name_q}"')
    if not res.get("ok"): return None
    items = res["data"].get("QueryResponse", {}).get("Item", [])
    return items[0] if items else None

def ensure_item(org_id: int, user_id: int, name: str, price: float) -> Optional[str]:
    token, realm = _get_intuit(org_id, user_id)
    if not token or not realm: return None
    existing = find_item_by_name(token, realm, name)
    if existing: return existing.get("Id")
    acc = find_income_account(token, realm)
    if not acc: return None
    url = f"{BASE}/{realm}/item"
    body = {"Name": name[:100], "Type": "Service", "IncomeAccountRef": {"value": acc}, "UnitPrice": price}
    r = requests.post(url, headers=_headers(token), data=json.dumps(body), timeout=30)
    if r.status_code >= 400: return None
    return r.json().get("Item", {}).get("Id")

def create_customer(org_id: int, user_id: int, display_name: str):
    token, realm = _get_intuit(org_id, user_id)
    if not token or not realm:
        return {"ok": False, "error": "No Intuit token/realmId"}
    url = f"{BASE}/{realm}/customer"
    body = {"DisplayName": display_name}
    r = requests.post(url, headers=_headers(token), data=json.dumps(body), timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}

def create_invoice(org_id: int, user_id: int, customer_id: str, amount: float, description: str, item_name: str = None):
    token, realm = _get_intuit(org_id, user_id)
    if not token or not realm:
        return {"ok": False, "error": "No Intuit token/realmId"}
    url = f"{BASE}/{realm}/invoice"
    item_id = ensure_item(org_id, user_id, item_name or description[:80], amount) or '1'
    body = {
        "CustomerRef": {"value": customer_id},
        "Line": [{
            "Amount": amount,
            "DetailType": "SalesItemLineDetail",
            "Description": description,
            "SalesItemLineDetail": {"ItemRef": {"value": item_id}}
        }]
    }
    r = requests.post(url, headers=_headers(token), data=json.dumps(body), timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}
