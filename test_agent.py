from datetime import date
import agent
from db import init_db, get_conn

init_db()
conn = get_conn()

def load(lead_id):
    lead = dict(conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone())
    msgs = [dict(m) for m in conn.execute("SELECT sender,date,text FROM messages WHERE lead_id=? ORDER BY id", (lead_id,))]
    return lead, msgs

if __name__ == "__main__":
    for lead_id in [4, 8, 5, 11, 13]:
        lead, msgs = load(lead_id)
        r = agent.analyze_lead(lead, msgs)
        print(f"\n--- {lead['name']} (lead {lead_id}) ---")
        for k, v in r.items():
            print(f"{k}: {v}")
