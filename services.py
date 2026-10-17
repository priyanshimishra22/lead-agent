"""All the app's logic in plain functions. main.py just exposes them as web endpoints."""
from datetime import date

from agent import analyze_lead
from db import get_conn, load_lead, save_analysis

TAG_RANK = {"Hot": 0, "Warm": 1, "Cold": 2}


def _decorate(lead, today):
    """Add days_overdue and bucket (overdue / today / upcoming) for the screen."""
    lead = dict(lead)
    if lead.get("next_followup"):
        diff = (today - date.fromisoformat(lead["next_followup"])).days
    else:
        diff = -999
    lead["days_overdue"] = max(diff, 0)
    lead["bucket"] = "overdue" if diff > 0 else ("today" if diff == 0 else "upcoming")
    return lead


def _sort_key(lead):
    """Most urgent first: overdue + today (Hot before Warm before Cold, oldest first), then upcoming by date."""
    due = lead.get("next_followup") or "9999-12-31"
    rank = TAG_RANK.get(lead.get("tag"), 3)
    if lead["bucket"] == "upcoming":
        return (1, due, rank)
    return (0, rank, due)


def list_leads(rep=None, today=None):
    today = today or date.today()
    conn = get_conn()
    if rep:
        rows = conn.execute("SELECT * FROM leads WHERE rep = ?", (rep,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM leads").fetchall()
    conn.close()
    leads = [_decorate(r, today) for r in rows]
    leads.sort(key=_sort_key)
    return leads


def list_reps():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT rep FROM leads WHERE rep IS NOT NULL ORDER BY rep").fetchall()
    conn.close()
    return [r["rep"] for r in rows]


def get_lead_detail(lead_id, today=None):
    lead, messages = load_lead(lead_id)
    if lead is None:
        return None
    return {"lead": _decorate(lead, today or date.today()), "messages": messages}


def refresh_lead(lead_id, today=None):
    """Run the agent on this lead and save its tag, reason, date and draft."""
    lead, messages = load_lead(lead_id)
    result = analyze_lead(lead, messages, today)
    save_analysis(lead_id, result)
    return result


def create_lead(name, company, phone, source, rep, today=None):
    today = today or date.today()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO leads (name, company, phone, source, rep, last_contact) VALUES (?, ?, ?, ?, ?, ?)",
        (name, company, phone, source, rep, today.isoformat()),
    )
    lead_id = cur.lastrowid
    conn.commit()
    conn.close()
    refresh_lead(lead_id, today)
    return lead_id


def add_message(lead_id, sender, text, today=None):
    """Add a chat message, update last contact, and let the agent update the lead."""
    today = today or date.today()
    lead, _ = load_lead(lead_id)
    if lead is None:
        return None
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (lead_id, sender, date, text) VALUES (?, ?, ?, ?)",
        (lead_id, sender, today.isoformat(), text),
    )
    conn.execute("UPDATE leads SET last_contact = ? WHERE id = ?", (today.isoformat(), lead_id))
    conn.commit()
    conn.close()
    refresh_lead(lead_id, today)
    return lead_id


def mark_sent(lead_id, text, today=None):
    """The rep sent the (edited) draft: it becomes a rep message, then the agent plans the next step."""
    return add_message(lead_id, "rep", text, today)


def update_draft(lead_id, draft):
    lead, _ = load_lead(lead_id)
    if lead is None:
        return None
    conn = get_conn()
    conn.execute("UPDATE leads SET draft = ? WHERE id = ?", (draft, lead_id))
    conn.commit()
    conn.close()
    return lead_id
