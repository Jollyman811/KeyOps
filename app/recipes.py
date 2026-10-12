import json
from typing import Any, Dict, List
from .db import get_session
from .models import Recipe, JobLog, Task, Lead
from .llm import draft_email_reply
from .connectors.google import gmail_send

def evaluate_condition(expr: str, context: Dict[str, Any]) -> bool:
    try:
        return bool(eval(expr, {}, context))
    except Exception:
        return False

def run_actions(org_id: int, actions: List[Dict[str, Any]], ctx: Dict[str, Any]):
    for act in actions:
        t = act.get("type")
        if t == "create_task":
            title = act.get("title","Follow up")
            with get_session() as s:
                s.add(Task(org_id=org_id, title=title)); s.commit()
        elif t == "ai_email":
            template = act.get("template","")
            provider = act.get("provider","openai")
            rendered = template.format(**{k:v for k,v in ctx.items()})
            body = draft_email_reply(rendered, provider=provider)
            to_email = getattr(ctx.get('lead'), 'email', None) if ctx.get('lead') else None
            if to_email:
                gmail_send(org_id, None, to_email, "Regarding your inquiry", body)
            with get_session() as s:
                s.add(JobLog(org_id=org_id, event="ai_email", details=body)); s.commit()
        else:
            with get_session() as s:
                s.add(JobLog(org_id=org_id, event="unknown_action", details=json.dumps(act))); s.commit()

def on_lead_created(lead: Lead):
    org_id = lead.org_id
    with get_session() as s:
        recipes = s.query(Recipe).filter(Recipe.org_id==org_id, Recipe.enabled==True, Recipe.trigger_model=="lead").all()
    for r in recipes:
        ctx = {"lead": lead}
        if evaluate_condition(r.condition or "False", ctx):
            actions = json.loads(r.actions_json or "[]")
            run_actions(org_id, actions, ctx)
            with get_session() as s:
                s.add(JobLog(org_id=org_id, recipe_id=r.id, event="lead_trigger", status="ok", details=f"Lead #{lead.id}")); s.commit()
