from .base import register
from ..models import Task, JobLog
from ..db import get_session
from ..security import current_org_id
from ..connectors.google import calendar_create_event
# Tip: Import your Request type if you want strict type hinting
# from fastapi import Request # Or whatever web framework you use

@register("add_task")
def add_task(payload: dict, request = None):
    # 1. Guard against a missing request upfront if it's strictly required
    if request is None:
        return {"ok": False, "error": "Request context is required"}
        
    org_id = current_org_id(request)
    
    # 2. Guard against a missing org_id if current_org_id can return None
    if org_id is None:
        return {"ok": False, "error": "Could not determine organization ID"}

    with get_session() as s:
        t = Task(org_id=org_id, title=(payload.get("title") or "Untitled"), due=payload.get("due"))
        s.add(t); s.commit(); s.refresh(t)
        
        if t.due:
            try:
                from datetime import timedelta
                start_iso = t.due.isoformat()
                end_iso = (t.due + timedelta(minutes=60)).isoformat()
                
                # 3. Safely get the user ID now that Pylance knows request is not None
                uid = request.session.get('uid')
                if uid is None:
                    raise ValueError("User session ID is missing")
                
                # All types are now strictly guaranteed (int, unknown, str, str, str)
                calendar_create_event(org_id, uid, f"Task: {t.title}", start_iso, end_iso)
                
            except Exception as e:
                s.add(JobLog(org_id=org_id, event="calendar_hold_task", status="fail", details=str(e))); s.commit()
                
    return {"ok": True, "created_id": t.id, "model":"task"}

@register("show_tasks")
def show_tasks(_payload, request=None):
    return {"ok": True}
