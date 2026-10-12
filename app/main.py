from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from .db import init_db, get_session
from .models import Task, Lead, Invoice
from .intents import parse_intent
from .plugins.base import REGISTRY  # noqa
from .plugins import todos, leads, invoices  # noqa

app = FastAPI(title="KeyOps — Command‑K for Your Business", version="0.1.0" )
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with get_session() as s:
        tasks = s.query(Task).order_by(Task.created_at.desc()).limit(6).all()
        leads = s.query(Lead).order_by(Lead.created_at.desc()).limit(6).all()
        invoices = s.query(Invoice).order_by(Invoice.created_at.desc()).limit(6).all()
    return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks, "leads": leads, "invoices": invoices})

@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(request: Request):
    with get_session() as s:
        tasks = s.query(Task).order_by(Task.created_at.desc()).all()
    return templates.TemplateResponse("components/tasks.html", {"request": request, "tasks": tasks})

@app.get("/leads", response_class=HTMLResponse)
def list_leads(request: Request):
    with get_session() as s:
        leads = s.query(Lead).order_by(Lead.created_at.desc()).all()
    return templates.TemplateResponse("components/leads.html", {"request": request, "leads": leads})

@app.get("/invoices", response_class=HTMLResponse)
def list_invoices(request: Request):
    with get_session() as s:
        invoices = s.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return templates.TemplateResponse("components/invoices.html", {"request": request, "invoices": invoices})

@app.post("/intent", response_class=HTMLResponse)
def run_intent(request: Request, q: str = Form(...)):
    intent, payload = parse_intent(q or "")
    if not intent:
        return templates.TemplateResponse("components/results.html", {"request": request, "warn": "Didn't understand. Try: add task call Megan tomorrow 3pm"})

    handler = REGISTRY.get(intent)
    # show_* intents have a handler that returns ok but the view renders.
    if handler:
        res = handler(payload)
        msg = None
        if intent == "add_task" and res.get("ok"):
            msg = f"Task created (#{res.get('created_id')})."
        elif intent == "new_lead" and res.get("ok"):
            msg = f"Lead added (#{res.get('created_id')})."
        elif intent == "create_invoice" and res.get("ok"):
            msg = f"Invoice drafted (#{res.get('created_id')})."
        return templates.TemplateResponse("components/results.html", {"request": request, "msg": msg})

    # If no plugin handler but a show_* intent, render corresponding section.
    if intent == "show_tasks":
        return list_tasks(request)
    if intent == "show_leads":
        return list_leads(request)
    if intent == "show_invoices":
        return list_invoices(request)

    return templates.TemplateResponse("components/results.html", {"request": request, "warn": "No handler registered for that."})
