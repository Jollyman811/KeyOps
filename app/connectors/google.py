from __future__ import annotations
import base64, requests
from typing import Optional
from datetime import datetime, timedelta
from ..db import get_session
from ..models import OAuthAccount, JobLog
from ..config import settings

GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
CAL_EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

def _refresh_google(rec):
    if not rec.refresh_token: return None
    data = {
        "grant_type": "refresh_token",
        "refresh_token": rec.refresh_token,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
    if r.status_code >= 400:
        try:
            with get_session() as s:
                s.add(JobLog(org_id=rec.org_id, event="oauth_refresh_google", status="fail", details=str(r.text)))
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
        s.add(dbrec); s.add(JobLog(org_id=dbrec.org_id, event="oauth_refresh_google", status="ok", details=f"expires_in={expires_in}")); s.commit()
    return new_token

def _get_google_token(org_id: int, user_id: Optional[int] = None) -> Optional[str]:
    with get_session() as s:
        q = s.query(OAuthAccount).filter(OAuthAccount.org_id==org_id, OAuthAccount.provider=="google").order_by(OAuthAccount.created_at.desc())
        if user_id: q = q.filter(OAuthAccount.user_id==user_id)
        rec = q.first()
    if not rec: return None
    if not rec.expires_at or rec.expires_at <= datetime.utcnow() + timedelta(minutes=2):
        tok = _refresh_google(rec)
        return tok or rec.access_token
    return rec.access_token

def gmail_send(org_id: int, user_id: Optional[int], to_email: str, subject: str, body: str) -> dict:
    token = _get_google_token(org_id, user_id)
    if not token:
        return {"ok": False, "error": "No Google OAuth token for this org/user"}
    mime = f"To: {to_email}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
    raw = base64.urlsafe_b64encode(mime.encode("utf-8")).decode("ascii")
    r = requests.post(GMAIL_SEND, headers={"Authorization": f"Bearer {token}"}, json={"raw": raw}, timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}

def calendar_create_event(org_id: int, user_id: Optional[int], summary: str, start_iso: str, end_iso: str, timezone: str="America/Chicago") -> dict:
    token = _get_google_token(org_id, user_id)
    if not token:
        return {"ok": False, "error": "No Google OAuth token for this org/user"}
    body = {"summary": summary, "start": {"dateTime": start_iso, "timeZone": timezone}, "end": {"dateTime": end_iso, "timeZone": timezone}}
    r = requests.post(CAL_EVENTS, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body, timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    return {"ok": True, "data": r.json()}
