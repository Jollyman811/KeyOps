# KeyOps — Command‑K for Your Business (MVP)

KeyOps is a local‑first, plugin‑ready **command palette** that turns natural language into business actions.
Type things like:

- `add task call Megan re: onboarding tomorrow 3pm`
- `new lead John Appleseed from Acme, email john@acme.com, budget 5k`
- `create invoice for John Appleseed 1200 for "Logo design"`

…and it just happens.

This MVP ships with Tasks, Leads, and Invoices. It uses **FastAPI + SQLite (SQLModel) + Jinja + HTMX** (CDN) to keep setup dead simple.


## Quickstart

```bash
# 1) Create and activate a virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the server
uvicorn app.main:app --reload --port 8008

# 4) Open the app
# Visit http://127.0.0.1:8008 in your browser
```
*(If your shell blocks scripts on Windows, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in your PowerShell.)*

## What’s inside?

- **Command Palette**: Press **Ctrl/⌘ + K** or click the search box. Type an intent like “add task …”
- **Intents**: A tiny natural‑language parser (rule‑based) maps phrases to actions.
- **Plugins** (MVP-ready): Simple pattern for registering new resource modules (e.g., CRM, Proposals, Inventory).
- **Local‑first DB**: SQLite file (`keyops.db`) in your project folder.

## Roadmap ideas
- OAuth connectors (Gmail, Calendar, Stripe, QuickBooks/Gusto)
- Background jobs & automation recipes (e.g., “If lead is hot → email sequence”)
- Multi‑tenant accounts and role‑based permissions
- AI assist (LLM) to auto‑draft replies & proposals (Bring your own API key)

## License
MIT
