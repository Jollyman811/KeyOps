from .base import register
from ..models import Task
from ..db import get_session
from datetime import datetime

@register("add_task")
def add_task(payload):
    title = payload.get("title", "Untitled").strip()
    due = payload.get("due")
    with get_session() as s:
        t = Task(title=title, due=due if due else None)
        s.add(t)
        s.commit()
        s.refresh(t)
        return {"ok": True, "created_id": t.id, "model": "task"}

@register("show_tasks")
def show_tasks(_payload):
    # no-op; handled in route to render template
    return {"ok": True}
