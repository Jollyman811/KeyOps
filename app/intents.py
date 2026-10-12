import re, dateparser
def parse_intent(text: str):
    t = (text or '').strip().lower()
    m = re.match(r"add\s+task\s+(?P<title>.+?)(?:\s+tomorrow|\s+for\s+(?P<when>.+))?$", t)
    if m:
        when = m.group('when')
        return "add_task", {"title": m.group('title').strip(), "due": dateparser.parse(when) if when else None}
    lm = re.match(r"new\s+lead\s+(?P<name>[^,]+?)(?:\s+from\s+(?P<company>[^,]+))?(?:,\s*email\s+(?P<email>[^,]+))?(?:,\s*phone\s+(?P<phone>[^,]+))?(?:,\s*budget\s+(?P<budget>[^,]+))?", t)
    if lm:
        import re as _re
        d = {k: (lm.group(k).strip() if lm.group(k) else None) for k in ("name","company","email","phone","budget")}
        if d.get("budget"):
            try: d["budget"] = float(_re.sub(r"[^0-9.]+","", d["budget"]))
            except: d["budget"] = None
        return "new_lead", d
    im = re.match(r"create\s+invoice\s+for\s+(?P<to>.+?)\s+(?P<amount>[-0-9.,]+)\s+for\s+\"(?P<desc>.+)\"", t)
    if im:
        try: amt = float(im.group("amount").replace(",",""))
        except: amt = 0.0
        return "create_invoice", {"to_name": im.group("to").strip(), "amount": amt, "description": im.group("desc").strip()}
    sm = re.match(r"show\s+(tasks|leads|invoices)$", t)
    if sm: return f"show_{sm.group(1)}", {}
    return None, {}
