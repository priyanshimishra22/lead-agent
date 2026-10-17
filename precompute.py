"""Run the agent on every lead once and save the results to precomputed.json.

Run this on your laptop. Leads that already have a good (non-fallback) result are skipped,
so you can run it again if the free AI quota ran out part-way.
"""
import json
import os
import time
from datetime import date

from agent import analyze_lead
from db import PRECOMPUTED_PATH, get_conn, init_db, load_lead

init_db()
today = date.today()

conn = get_conn()
lead_ids = [r["id"] for r in conn.execute("SELECT id FROM leads ORDER BY id")]
conn.close()

results = {}
if os.path.exists(PRECOMPUTED_PATH):
    with open(PRECOMPUTED_PATH, encoding="utf-8") as f:
        results = json.load(f)

for lead_id in lead_ids:
    if str(lead_id) in results and not results[str(lead_id)].get("used_fallback"):
        continue  # already done properly
    lead, msgs = load_lead(lead_id)
    for attempt in range(3):
        r = analyze_lead(lead, msgs, today)
        if not r["used_fallback"]:
            break
        if attempt < 2:
            print(f"   lead {lead_id}: AI failed, waiting 60 seconds then trying again...")
            time.sleep(60)
    offset = (date.fromisoformat(r["next_followup"]) - today).days
    results[str(lead_id)] = {
        "tag": r["tag"],
        "reason": r["reason"],
        "followup_offset_days": offset,
        "draft": r["draft"],
        "status": r["status"] if "status" in r else None,
        "used_fallback": r["used_fallback"],
    }
    print(f"{lead_id:>2} {lead['name']:<18} {r['tag']:<5} due in {offset:>4} days  fallback={r['used_fallback']}")
    with open(PRECOMPUTED_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    time.sleep(5)  # free tier allows about 15 requests per minute

bad = [k for k, v in results.items() if v.get("used_fallback")]
print(f"\nDone. {len(results)} leads saved, {len(bad)} used the fallback.")
if bad:
    print("Run this script again to retry:", ", ".join(bad))
