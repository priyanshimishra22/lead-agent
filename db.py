import json
import os
import sqlite3
from datetime import date, timedelta

from seed_data import get_seed

DB_PATH = "leads.db"
PRECOMPUTED_PATH = "precomputed.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    company       TEXT NOT NULL,
    phone         TEXT,
    source        TEXT,
    rep           TEXT,
    last_contact  TEXT,
    tag           TEXT,
    reason        TEXT,
    next_followup TEXT,
    draft         TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    sender  TEXT NOT NULL,
    date    TEXT NOT NULL,
    text    TEXT NOT NULL
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    if count == 0:
        leads, chats = get_seed()
        for l in leads:
            conn.execute(
                "INSERT INTO leads (id, name, company, phone, source, rep, last_contact) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (l["id"], l["name"], l["company"], l["phone"], l["source"], l["rep"], l["last_contact"]),
            )
        for m in chats:
            conn.execute(
                "INSERT INTO messages (lead_id, sender, date, text) VALUES (?, ?, ?, ?)",
                (m["lead_id"], m["sender"], m["date"], m["text"]),
            )
        apply_precomputed(conn)
        conn.commit()
    conn.close()


def apply_precomputed(conn):
    """Load agent results saved earlier, so the app starts ready without calling the AI."""
    if not os.path.exists(PRECOMPUTED_PATH):
        return
    with open(PRECOMPUTED_PATH, encoding="utf-8") as f:
        results = json.load(f)
    today = date.today()
    for lead_id, r in results.items():
        due = today + timedelta(days=r["followup_offset_days"])
        conn.execute(
            "UPDATE leads SET tag=?, reason=?, next_followup=?, draft=? WHERE id=?",
            (r["tag"], r["reason"], due.isoformat(), r["draft"], int(lead_id)),
        )


def load_lead(lead_id):
    """Return (lead_dict, list_of_message_dicts) for one lead."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if row is None:
        conn.close()
        return None, []
    msgs = conn.execute(
        "SELECT sender, date, text FROM messages WHERE lead_id = ? ORDER BY id", (lead_id,)
    ).fetchall()
    conn.close()
    return dict(row), [dict(m) for m in msgs]


def save_analysis(lead_id, result):
    """Save the agent's result (tag, reason, next_followup, draft) on the lead."""
    conn = get_conn()
    conn.execute(
        "UPDATE leads SET tag=?, reason=?, next_followup=?, draft=? WHERE id=?",
        (result["tag"], result["reason"], result["next_followup"], result["draft"], lead_id),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    conn = get_conn()
    print("leads:", conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0])
    print("messages:", conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
    row = conn.execute("SELECT * FROM leads WHERE id = 4").fetchone()
    print(dict(row))
    for m in conn.execute("SELECT sender, date, text FROM messages WHERE lead_id = 4 ORDER BY id"):
        print(dict(m))
    conn.close()
