from __future__ import annotations
import re
from typing import Optional, Tuple, Dict, Any
import dateparser

# Very small, rule-based intent parser to keep this MVP offline and predictable.
# Returns (intent_name, payload_dict) or (None, {}).
def parse_intent(text: str) -> Tuple[Optional[str], Dict[str, Any]]:
    t = text.strip().lower()

    # add task {title} [due {date/time}]
    m = re.match(r"add\s+task\s+(?P<title>.+?)(?:\s+for\s+(?P<when>.+))?$", t)
    if m:
        title = m.group('title').strip()
        when = m.group('when')
        due = dateparser.parse(when) if when else None
        return "add_task", {"title": title, "due": due}

    # new lead {name} from {company}, email {email}, budget {amount}
    lm = re.match(r"new\s+lead\s+(?P<name>[^,]+?)(?:\s+from\s+(?P<company>[^,]+))?(?:,\s*email\s+(?P<email>[^,]+))?(?:,\s*phone\s+(?P<phone>[^,]+))?(?:,\s*budget\s+(?P<budget>[^,]+))?", t)
    if lm:
        d = {k: (lm.group(k).strip() if lm.group(k) else None) for k in ("name", "company", "email", "phone", "budget")}
        # coerce budget
        if d.get("budget"):
            try:
                d["budget"] = float(re.sub(r"[^0-9.]+", "", d["budget"]))  # strip non-numeric
            except Exception:
                d["budget"] = None
        return "new_lead", d

    # create invoice for {to_name} {amount} for "{description}"
    im = re.match(r"create\s+invoice\s+for\s+(?P<to>.+?)\s+(?P<amount>[-0-9.,]+)\s+for\s+\"(?P<desc>.+)\"", t)
    if im:
        amt_str = im.group("amount")
        try:
            amt = float(amt_str.replace(",", ""))
        except Exception:
            amt = 0.0
        return "create_invoice", {"to_name": im.group("to").strip(), "amount": amt, "description": im.group("desc").strip()}

    # show {tasks|leads|invoices}
    sm = re.match(r"show\s+(tasks|leads|invoices)$", t)
    if sm:
        return f"show_{sm.group(1)}", {}

    return None, {}
