from .base import register
from ..models import Lead, JobLog
from ..db import get_session
from ..security import current_org_id
from ..recipes import on_lead_created
from ..connectors.google import calendar_create_event

@register("new_lead")
def new_lead(payload, request=None):
    org_id = current_org_id(request)
    with get_session() as s:
        lead = Lead(org_id=org_id, name=payload.get("name",""), company=payload.get("company"),
                    email=payload.get("email"), phone=payload.get("phone"), budget=payload.get("budget"))
        s.add(lead); s.commit(); s.refresh(lead)
        try:
            from datetime import datetime, timedelta
            now = datetime.utcnow(); start_iso = now.isoformat(); end_iso = (now + timedelta(minutes=30)).isoformat()
            calendar_create_event(org_id, request.session.get('uid'), f"Lead: {lead.name}", start_iso, end_iso)
        except Exception as e:
            s.add(JobLog(org_id=org_id, event="calendar_hold_lead", status="fail", details=str(e))); s.commit()
    on_lead_created(lead)
    return {"ok": True, "created_id": lead.id, "model":"lead"}

@register("show_leads")
def show_leads(_payload, request=None):
    return {"ok": True}
