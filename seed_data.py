"""
Sample data for the lead follow-up agent (all fake).

Dates are stored as "days ago" and converted to real dates when the app
starts. That way there are always overdue and due-today leads, whenever a
reviewer opens the app.

Chat format: lead_id -> list of (sender, days_ago, text), oldest first.
"""
from datetime import date, timedelta

REPS = ["Rahul", "Neha", "Vikram", "Anjali", "Karan"]

LEADS = [
    # id, name, company, phone, source, rep, last_contact_days_ago
    (1,  "Suresh Patel",     "Patel Agro Foods",         "+91 90000 10001", "IndiaMART",       "Rahul",  1),
    (2,  "Meena Iyer",       "Iyer Spices Pvt Ltd",      "+91 90000 10002", "Website form",    "Neha",   6),
    (3,  "Arjun Mehta",      "Mehta Pharma Packs",       "+91 90000 10003", "Trade show",      "Vikram", 12),
    (4,  "Kavita Rao",       "Rao Beverages",            "+91 90000 10004", "Referral",        "Anjali", 2),
    (5,  "Imran Sheikh",     "Sheikh Garments Export",   "+91 90000 10005", "Justdial",        "Karan",  20),
    (6,  "Deepak Nair",      "Nair Tea Estates",         "+91 90000 10006", "IndiaMART",       "Rahul",  9),
    (7,  "Sunita Joshi",     "Joshi Sweets & Snacks",    "+91 90000 10007", "Cold call",       "Neha",   30),
    (8,  "Rohit Verma",      "Verma Auto Components",    "+91 90000 10008", "Website form",    "Vikram", 3),
    (9,  "Farah Khan",       "Khan Dairy Products",      "+91 90000 10009", "Referral",        "Anjali", 14),
    (10, "Gaurav Singh",     "Singh Rice Mills",         "+91 90000 10010", "WhatsApp inbound","Karan",  0),
    (11, "Lakshmi Reddy",    "Reddy Pharma Distributors","+91 90000 10011", "Trade show",      "Rahul",  45),
    (12, "Manoj Tiwari",     "Tiwari Plastics",          "+91 90000 10012", "IndiaMART",       "Neha",   5),
    # Leads 13-22 have NO chat yet. The agent must handle that case.
    (13, "Pooja Desai",      "Desai Namkeen",            "+91 90000 10013", "Website form",    "Vikram", 4),
    (14, "Harish Kulkarni",  "Kulkarni Oil Mills",       "+91 90000 10014", "IndiaMART",       "Anjali", 11),
    (15, "Nisha Gupta",      "Gupta Cosmetics",          "+91 90000 10015", "Trade show",      "Karan",  18),
    (16, "Sanjay Malhotra",  "Malhotra Frozen Foods",    "+91 90000 10016", "Referral",        "Rahul",  2),
    (17, "Divya Menon",      "Menon Coir Exports",       "+91 90000 10017", "Justdial",        "Neha",   25),
    (18, "Ravi Chandra",     "Chandra Steel Fabricators","+91 90000 10018", "Cold call",       "Vikram", 7),
    (19, "Alok Pandey",      "Pandey Flour Mills",       "+91 90000 10019", "Website form",    "Anjali", 0),
    (20, "Shweta Bansal",    "Bansal Pickles",           "+91 90000 10020", "IndiaMART",       "Karan",  8),
    (21, "Tarun Ahuja",      "Ahuja Electricals",        "+91 90000 10021", "Trade show",      "Rahul",  35),
    (22, "Zoya Ansari",      "Ansari Leather Works",     "+91 90000 10022", "WhatsApp inbound","Neha",   1),
]

CHATS = {
    # 1: Asked price, got quote, will confirm tomorrow -> likely HOT
    1: [("buyer", 4, "Hello, saw your carton sealing machine on IndiaMART. What is the price?"),
        ("rep",   4, "Hi Suresh ji, our semi-auto carton sealer SC-450 is Rs 68,000 + GST. Delivery in 7 days."),
        ("buyer", 3, "Ok. Can you send quotation?"),
        ("rep",   3, "Sent on mail. Please check."),
        ("buyer", 1, "Got it. Will confirm tomorrow after talking to my partner.")],
    # 2: Wanted demo, went quiet after rep's last message -> WARM, rep must chase
    2: [("rep",   14, "Hello Meena ma'am, thanks for your enquiry about the shrink wrap tunnel."),
        ("buyer", 13, "Yes, can we see it running before we decide?"),
        ("rep",   12, "Sure, we can do a demo at our Peenya unit. Friday 11am works?"),
        ("buyer", 12, "Friday not possible. Will tell you."),
        ("rep",    6, "Hi ma'am, just checking if next week works for the demo?")],
    # 3: Asked for brochure at expo, then silence -> WARM drifting COLD
    3: [("buyer", 15, "Collected your card at the expo. Please send brochure for strapping machines."),
        ("rep",   15, "Thanks Arjun sir! Sending brochure and price list now."),
        ("rep",   14, "(sent brochure.pdf)"),
        ("buyer", 12, "Thanks, will look and revert.")],
    # 4: Wants 2 machines, asked discount + delivery, rep hasn't replied -> HOT, urgent
    4: [("buyer", 5, "Need 2 stretch wrapping machines for our new plant."),
        ("rep",   5, "Great Kavita ji! Our SW-200 is Rs 1.9L each."),
        ("buyer", 4, "Can you do Rs 3.5L for both? And how soon can you deliver?"),
        ("rep",   3, "Let me check with my manager on the price. Delivery 10 days."),
        ("buyer", 2, "Please reply fast, we want to finalise this week.")],
    # 5: "Not now, after Diwali" (Hinglish) -> COLD for now, follow up AFTER Diwali
    5: [("rep",   25, "Hello Imran sir, following up on the vacuum packing machine."),
        ("buyer", 24, "Abhi budget nahi hai. Diwali ke baad baat karte hain."),
        ("rep",   24, "Theek hai sir, Diwali ke baad call karunga."),
        ("buyer", 20, "Ok")],
    # 6: Comparing with a cheaper competitor -> WARM
    6: [("buyer", 12, "Your tea packing machine price is Rs 4.2L. Another vendor says Rs 3.6L."),
        ("rep",   12, "Sir ours has 2 year warranty and local service. Can I explain the difference on a call?"),
        ("buyer", 10, "Ok send details of warranty."),
        ("rep",    9, "Sent the warranty and service terms PDF.")],
    # 7: Sent catalogue, no reply for a month -> COLD
    7: [("rep",   34, "Hello Sunita ji, we make packaging machines for snacks. Can I send details?"),
        ("buyer", 34, "Yes send on WhatsApp"),
        ("rep",   33, "Sent catalogue. Please call me for any questions."),
        ("rep",   30, "Hi ma'am, did you get a chance to see it?")],
    # 8: Urgent need, will send PO, rep hasn't replied -> HOT, most urgent
    8: [("buyer", 4, "Need strapping machine urgently. Our dispatch is next Monday. Do you have stock?"),
        ("rep",   4, "Yes sir, ST-100 is in stock at Rs 42,000 + GST."),
        ("buyer", 3, "Can you deliver by Friday? I will send PO tomorrow.")],
    # 9: Site visit postponed by buyer -> WARM
    9: [("rep",   20, "Hi Farah ma'am, I'd like to visit your plant to check requirements."),
        ("buyer", 19, "Sure, come next Tuesday."),
        ("rep",   18, "Great, Tuesday 11am confirmed."),
        ("buyer", 15, "Sorry something came up, need to postpone. Will let you know."),
        ("rep",   14, "No problem ma'am, whenever you are free.")],
    # 10: Brand new enquiry today, rep asked a question -> WARM (waiting on buyer)
    10: [("buyer", 0, "Hello, do you make vacuum packing machines for 5kg rice bags?"),
         ("rep",   0, "Yes sir! Can I know your daily volume?")],
    # 11: Bought elsewhere -> COLD, basically closed
    11: [("rep",   50, "Hello Lakshmi ma'am, quote for the sleeve wrapping machine attached."),
         ("buyer", 47, "Thanks."),
         ("buyer", 45, "Sorry, we have finalised with another supplier. Will contact in future.")],
    # 12: Will order today if 8% discount; rep owes an answer -> HOT
    12: [("buyer", 8, "SC-450 quote received. Best price?"),
         ("rep",   8, "Sir Rs 68,000 is best."),
         ("buyer", 7, "Competitor giving 62,000. If you give 8% off, I will order today."),
         ("rep",   7, "Let me check with owner and tell you."),
         ("buyer", 5, "Any update?")],
}


def _d(days_ago, today):
    return (today - timedelta(days=days_ago)).isoformat()


def get_seed(today=None):
    """Return (leads, chats) with real dates, ready to insert into the DB."""
    today = today or date.today()
    leads = [
        {"id": i, "name": n, "company": c, "phone": p, "source": s,
         "rep": r, "last_contact": _d(ago, today)}
        for (i, n, c, p, s, r, ago) in LEADS
    ]
    chats = []
    for lead_id, msgs in CHATS.items():
        for order, (sender, ago, text) in enumerate(msgs):
            chats.append({"lead_id": lead_id, "sender": sender,
                          "date": _d(ago, today), "order": order, "text": text})
    return leads, chats


if __name__ == "__main__":
    leads, chats = get_seed()
    print(f"{len(leads)} leads, {len({c['lead_id'] for c in chats})} chats, {len(chats)} messages")
    for l in leads[:3]:
        print(l)
