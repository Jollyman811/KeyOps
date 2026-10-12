from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from .db import init_db, get_session
from .models import Task, Lead, Invoice, User, Organization, UserOrg, APIKey, OAuthAccount, Recipe
from .security import add_session_middleware, hash_password, verify_password, current_user, require_login, current_org_id, set_org, require_role, user_role_in_org, generate_csrf, verify_csrf
from .intents import parse_intent
from .plugins import todos, leads, invoices
from .plugins.base import REGISTRY as ACTIONS
from .config import settings
from .llm import draft_email_reply, draft_proposal, run_chain
from .connectors.oauth import get_oauth

app = FastAPI(title="KeyOps-Plus", version="0.5.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
add_session_middleware(app)
scheduler = BackgroundScheduler(); scheduler.start()

@app.on_event("startup")
def on_startup(): init_db()

# -------- Auth --------
@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": current_user(request), "csrf_token": generate_csrf(request)})

@app.post("/register", response_class=HTMLResponse)
def register(request: Request, email: str = Form(...), password: str = Form(...), org_name: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    with get_session() as s:
        if s.query(User).filter(User.email==email).first():
            return templates.TemplateResponse("register.html", {"request": request, "user": None, "error":"Email already in use", "csrf_token": generate_csrf(request)})
        u = User(email=email, password_hash=hash_password(password)); s.add(u); s.commit(); s.refresh(u)
        o = Organization(name=org_name); s.add(o); s.commit(); s.refresh(o)
        s.add(UserOrg(user_id=u.id, org_id=o.id, role="owner")); s.commit()
        request.session["uid"] = u.id; set_org(request, o.id)
    return RedirectResponse("/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": current_user(request), "csrf_token": generate_csrf(request)})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    with get_session() as s:
        u = s.query(User).filter(User.email==email).first()
        if not u or not verify_password(password, u.password_hash):
            return templates.TemplateResponse("login.html", {"request": request, "user": None, "error":"Invalid credentials", "csrf_token": generate_csrf(request)})
        request.session["uid"] = u.id
        uo = s.query(UserOrg).filter(UserOrg.user_id==u.id).first()
        if uo: set_org(request, uo.org_id)
    return RedirectResponse("/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear(); return RedirectResponse("/login", status_code=303)

# -------- Dashboard --------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    u = require_login(request); org_id = current_org_id(request)
    with get_session() as s:
        tasks = s.query(Task).filter(Task.org_id==org_id).order_by(Task.created_at.desc()).limit(6).all()
        leads = s.query(Lead).filter(Lead.org_id==org_id).order_by(Lead.created_at.desc()).limit(6).all()
        invoices = s.query(Invoice).filter(Invoice.org_id==org_id).order_by(Invoice.created_at.desc()).limit(6).all()
        org = s.get(Organization, org_id)
    return templates.TemplateResponse("index.html", {"request": request, "user": u, "org_name": org.name if org else None, "tasks": tasks, "leads": leads, "invoices": invoices, "csrf_token": generate_csrf(request)})

@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(request: Request):
    require_login(request); org_id = current_org_id(request)
    with get_session() as s: tasks = s.query(Task).filter(Task.org_id==org_id).order_by(Task.created_at.desc()).all()
    return templates.TemplateResponse("components/tasks.html", {"request": request, "tasks": tasks})

@app.get("/leads", response_class=HTMLResponse)
def list_leads(request: Request):
    require_login(request); org_id = current_org_id(request)
    with get_session() as s: leads = s.query(Lead).filter(Lead.org_id==org_id).order_by(Lead.created_at.desc()).all()
    return templates.TemplateResponse("components/leads.html", {"request": request, "leads": leads, "csrf_token": generate_csrf(request)})

@app.get("/invoices", response_class=HTMLResponse)
def list_invoices(request: Request):
    require_login(request); org_id = current_org_id(request)
    with get_session() as s: invoices = s.query(Invoice).filter(Invoice.org_id==org_id).order_by(Invoice.created_at.desc()).all()
    return templates.TemplateResponse("components/invoices.html", {"request": request, "invoices": invoices, "csrf_token": generate_csrf(request)})

# -------- Intent runner --------
@app.post("/intent", response_class=HTMLResponse)
def run_intent(request: Request, q: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    require_login(request)
    intent, payload = parse_intent(q or "")
    if not intent:
        return templates.TemplateResponse("components/results.html", {"request": request, "warn":"Didn't understand. Try: add task call Megan tomorrow 3pm"})
    handler = ACTIONS.get(intent)
    if handler:
        res = handler(payload, request=request)
        msg = None
        if intent == "add_task" and res.get("ok"): msg = f"Task created (#{res.get('created_id')})."
        elif intent == "new_lead" and res.get("ok"): msg = f"Lead added (#{res.get('created_id')})."
        elif intent == "create_invoice" and res.get("ok"): msg = f"Invoice drafted (#{res.get('created_id')})."
        return templates.TemplateResponse("components/results.html", {"request": request, "msg": msg})
    if intent == "show_tasks": return list_tasks(request)
    if intent == "show_leads": return list_leads(request)
    if intent == "show_invoices": return list_invoices(request)
    return templates.TemplateResponse("components/results.html", {"request": request, "warn":"No handler registered."})

# -------- Settings --------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    u = require_login(request); org_id = current_org_id(request)
    with get_session() as s:
        org = s.get(Organization, org_id)
        role = user_role_in_org(u.id, org_id)
        def get_key(provider):
            k = s.query(APIKey).filter(APIKey.org_id==org_id, APIKey.provider==provider).first()
            return k.key if k else None
        openai = get_key("openai"); gemini = get_key("gemini"); xai = get_key("xai"); ollama = get_key("ollama")
    return templates.TemplateResponse("settings.html", {"request": request, "user": u, "org": org, "role": role, "openai": openai, "gemini": gemini, "xai": xai, "ollama": ollama, "csrf_token": generate_csrf(request)})

@app.post("/settings/api-keys")
def save_api_keys(request: Request, openai: str = Form(None), gemini: str = Form(None), xai: str = Form(None), ollama: str = Form(None), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request); require_role(request, "admin"); org_id = current_org_id(request)
    with get_session() as s:
        def up(provider, value):
            from .models import APIKey
            if value is None: return
            rec = s.query(APIKey).filter(APIKey.org_id==org_id, APIKey.provider==provider).first()
            if rec: rec.key = value
            else: s.add(APIKey(org_id=org_id, provider=provider, key=value))
        up("openai", openai); up("gemini", gemini); up("xai", xai); up("ollama", ollama); s.commit()
    return RedirectResponse("/settings", status_code=303)

@app.post("/settings/test-email")
def settings_test_email(request: Request, to: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request); require_role(request, "admin")
    org_id = current_org_id(request)
    from .connectors.google import gmail_send
    res = gmail_send(org_id, u.id, to, "Test from KeyOps-Plus", "This is a test email from your KeyOps-Plus instance.")
    return RedirectResponse("/settings", status_code=303)

# -------- OAuth --------
@app.get("/oauth/{provider}/login")
async def oauth_login(request: Request, provider: str):
    require_login(request); require_role(request, "admin")
    oauth = get_oauth()
    redirect_uri = settings.OAUTH_REDIRECT_BASE.rstrip('/') + f"/oauth/{provider}/callback"
    extra = {}
    if provider == 'google':
        extra = {'access_type':'offline','prompt':'consent'}
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri, **extra)

@app.get("/oauth/{provider}/callback")
async def oauth_callback(request: Request, provider: str):
    u = require_login(request); require_role(request, "admin")
    oauth = get_oauth()
    token = await oauth.create_client(provider).authorize_access_token(request)
    org_id = current_org_id(request)
    realm_id = request.query_params.get('realmId') if provider == 'intuit' else None
    import time as _t
    exp = token.get('expires_at') or (_t.time() + int(token.get('expires_in', 3600)))
    expires_at = datetime.utcfromtimestamp(exp)
    with get_session() as s:
        s.add(OAuthAccount(user_id=u.id, org_id=org_id, provider=provider, access_token=token.get('access_token',''), refresh_token=token.get('refresh_token'), scope=realm_id, expires_at=expires_at)); s.commit()
    return RedirectResponse("/settings", status_code=303)

# -------- AI --------
@app.get("/ai", response_class=HTMLResponse)
def ai_form(request: Request):
    u = require_login(request)
    return templates.TemplateResponse("ai.html", {"request": request, "user": u, "mode":"reply", "provider":"openai", "csrf_token": generate_csrf(request)})

@app.post("/ai", response_class=HTMLResponse)
def ai_generate(request: Request, mode: str = Form(...), provider: str = Form(...), context: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request)
    try:
        out = draft_email_reply(context, provider) if mode=="reply" else draft_proposal(context, provider)
    except Exception as e:
        out = f"Error: {e}"
    return templates.TemplateResponse("ai.html", {"request": request, "user": u, "mode": mode, "provider": provider, "context": context, "output": out, "csrf_token": generate_csrf(request)})

# -------- Lead actions --------
@app.post("/leads/email/{lead_id}")
def leads_email_send(request: Request, lead_id: int, subject: str = Form(...), body: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request); require_role(request, "admin")
    org_id = current_org_id(request)
    from .models import Lead, JobLog
    from .db import get_session
    from .connectors.google import gmail_send
    with get_session() as s:
        l = s.get(Lead, lead_id)
        if not l or l.org_id != org_id or not l.email:
            return RedirectResponse("/", status_code=303)
        res = gmail_send(org_id, u.id, l.email, subject, body)
        s.add(JobLog(org_id=org_id, event="lead_email", status="ok" if res.get("ok") else "fail", details=str(res))); s.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/leads/hold/{lead_id}")
def leads_hold_now(request: Request, lead_id: int):
    u = require_login(request); require_role(request, "admin")
    org_id = current_org_id(request)
    from .models import Lead, JobLog
    from .db import get_session
    from .connectors.google import calendar_create_event
    from datetime import datetime, timedelta
    with get_session() as s:
        l = s.get(Lead, lead_id)
        if not l or l.org_id != org_id:
            return RedirectResponse("/", status_code=303)
        now = datetime.utcnow()
        minute = 30 if now.minute < 30 else 0
        start = now.replace(minute=minute, second=0, microsecond=0)
        if start <= now: start = start + timedelta(minutes=30)
        end = start + timedelta(minutes=30)
        res = calendar_create_event(org_id, u.id, f"Call: {l.name}", start.isoformat(), end.isoformat())
        s.add(JobLog(org_id=org_id, event="lead_hold_now", status="ok" if res.get("ok") else "fail", details=str(res))); s.commit()
    return RedirectResponse("/", status_code=303)

# -------- Recipes --------
@app.get("/recipes", response_class=HTMLResponse)
def recipes_page(request: Request):
    u = require_login(request); require_role(request, "admin"); org_id = current_org_id(request)
    with get_session() as s:
        rs = s.query(Recipe).filter(Recipe.org_id==org_id).order_by(Recipe.created_at.desc()).all()
    return templates.TemplateResponse("recipes.html", {"request": request, "user": u, "recipes": rs, "csrf_token": generate_csrf(request)})

@app.post("/recipes", response_class=HTMLResponse)
def recipes_create(request: Request, name: str = Form(...), trigger_model: str = Form(...), condition: str = Form(""), actions_json: str = Form("[]"), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request); require_role(request, "admin"); org_id = current_org_id(request)
    with get_session() as s:
        r = Recipe(org_id=org_id, name=name, trigger_model=trigger_model, condition=condition, actions_json=actions_json)
        s.add(r); s.commit()
    return RedirectResponse("/recipes", status_code=303)

@app.post("/recipes/toggle/{rid}")
def recipes_toggle(request: Request, rid: int, _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request); require_role(request, "admin")
    with get_session() as s:
        r = s.get(Recipe, rid)
        if r: r.enabled = not r.enabled; s.add(r); s.commit()
    return RedirectResponse("/recipes", status_code=303)

# -------- Chains --------
@app.get("/chains", response_class=HTMLResponse)
def chains_page(request: Request):
    u = require_login(request)
    return templates.TemplateResponse("chains.html", {"request": request, "user": u, "csrf_token": generate_csrf(request)})

@app.post("/chains", response_class=HTMLResponse)
def chains_run(request: Request, mode: str = Form(...), text: str = Form(...), _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request)
    prefix = {"summarize":"Summarize in 5 bullets: ", "todos":"Extract TODOs as bullets: ", "reply":"Draft a brief professional reply: "}.get(mode, "")
    out = run_chain(prefix + text, provider="openai")
    return templates.TemplateResponse("chains.html", {"request": request, "user": u, "output": out, "csrf_token": generate_csrf(request)})

# -------- Invoices: refresh, resend, mark paid --------
@app.get("/invoices/refresh/{invoice_id}")
def invoice_refresh_status(request: Request, invoice_id: int):
    u = require_login(request)
    org_id = current_org_id(request)
    from .db import get_session
    from .models import Invoice, JobLog
    from .connectors import stripe_conn
    with get_session() as s:
        inv = s.get(Invoice, invoice_id)
        if not inv or inv.org_id != org_id or not inv.stripe_checkout_id:
            return RedirectResponse("/", status_code=303)
        res = stripe_conn.get_checkout_session(org_id, request.session.get('uid'), inv.stripe_checkout_id)
        if res.get("ok"):
            d = res["data"]
            inv.stripe_checkout_status = d.get("status")
            inv.stripe_payment_status = d.get("payment_status")
            if (d.get("status") in ("complete","expired") and d.get("payment_status")=="paid") or d.get("payment_status")=="paid":
                inv.status = "paid"
            s.add(inv); s.add(JobLog(org_id=org_id, event="stripe_status_refresh", status="ok", details=str({k:d.get(k) for k in ("id","status","payment_status")}))); s.commit()
        else:
            s.add(JobLog(org_id=org_id, event="stripe_status_refresh", status="fail", details=str(res))); s.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/invoices/resend/{invoice_id}")
def invoice_resend(request: Request, invoice_id: int, _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request)
    org_id = current_org_id(request)
    from .db import get_session
    from .models import Invoice, Lead, Organization, JobLog
    from .connectors.google import gmail_send
    with get_session() as s:
        inv = s.get(Invoice, invoice_id)
        if not inv or inv.org_id != org_id:
            return RedirectResponse("/", status_code=303)
        to_email = inv.to_email
        if not to_email:
            lead = s.query(Lead).filter(Lead.org_id==org_id, Lead.name==inv.to_name).first()
            to_email = lead.email if lead and lead.email else None
        if not to_email:
            s.add(JobLog(org_id=org_id, event="invoice_resend", status="fail", details="No recipient email found")); s.commit()
            return RedirectResponse("/", status_code=303)
        org = s.get(Organization, org_id)
        subject = f"Invoice #{inv.id} from {org.name}"
        url = inv.stripe_checkout_url or "(link pending)"
        body = f"Hi {inv.to_name},\n\nHere is your invoice for {inv.description} totaling ${inv.amount:.2f}.\n\nPay securely here: {url}\n\nThanks,\n{org.name}"
        res = gmail_send(org_id, u.id, to_email, subject, body)
        s.add(JobLog(org_id=org_id, event="invoice_resend", status="ok" if res.get("ok") else "fail", details=str(res))); s.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/invoices/mark-paid/{invoice_id}")
def invoice_mark_paid(request: Request, invoice_id: int, _csrf: str = Form(...)):
    verify_csrf(request, _csrf)
    u = require_login(request); require_role(request, "admin")
    org_id = current_org_id(request)
    from .db import get_session
    from .models import Invoice, JobLog
    with get_session() as s:
        inv = s.get(Invoice, invoice_id)
        if not inv or inv.org_id != org_id:
            return RedirectResponse("/", status_code=303)
        inv.status = "paid"
        s.add(inv); s.add(JobLog(org_id=org_id, event="invoice_mark_paid", status="ok", details=f"invoice_id={invoice_id}")); s.commit()
    return RedirectResponse("/", status_code=303)
