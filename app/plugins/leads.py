from .base import register
from ..models import Lead
from ..db import get_session

@register("new_lead")
def new_lead(payload):
    with get_session() as s:
        lead = Lead(
            name=payload.get("name", ""),
            company=payload.get("company"),
            email=payload.get("email"),
            phone=payload.get("phone"),
            budget=payload.get("budget"),
        )
        s.add(lead)
        s.commit()
        s.refresh(lead)
        return {"ok": True, "created_id": lead.id, "model": "lead"}

@register("show_leads")
def show_leads(_payload):
    return {"ok": True}
