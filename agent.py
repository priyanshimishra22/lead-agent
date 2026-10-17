import json
import os
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

# Change the model in ONE place (or set GEMINI_MODEL in .env)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

VALID_TAGS = {"Hot", "Warm", "Cold"}

PROMPT_TEMPLATE = """You are a follow-up assistant for a sales rep at a small company that sells packaging machines to other businesses in India.

Today's date is {today}.

Read the lead and the WhatsApp chat below. Then decide:
1. tag: "Hot", "Warm" or "Cold"
2. reason: ONE short sentence explaining the tag, using facts from the chat
3. status: what is happening right now, exactly one of:
   - "buyer_waiting": the buyer sent the last message and it needs a reply from the rep
   - "rep_waiting": the rep sent the last message and is waiting for the buyer to reply
   - "deferred": the buyer said to talk later (for example "after Diwali" or "next month")
   - "new_lead": there is no chat yet
   - "closed": the buyer bought elsewhere or clearly said no
4. deferred_until: only if status is "deferred", the date the buyer asked to be contacted, as YYYY-MM-DD (just after the time they named). Otherwise null.
5. draft_message: the next WhatsApp message the rep should send

TAG RULES
- Hot: the buyer asked for a price, quote, discount, demo, stock or delivery date, or said they will order, AND the conversation is recent. A buyer waiting for the rep's reply on a recent request is always Hot.
- Warm: the buyer is interested but has not committed (comparing vendors, asked for details, postponed a visit, asked to talk later), or it is a new enquiry.
- Cold: the buyer has not replied for 21 days or more (check "Days since last contact"), or the buyer bought elsewhere or said no.

DRAFT RULES
- Short, polite WhatsApp style, 1 to 3 sentences, written as the rep.
- Use the buyer's first name. Match the language and tone of the chat (for example Hinglish if the buyer used Hinglish).
- Use ONLY facts that appear in the chat. Never invent prices, discounts, delivery dates, company names or promises.
- Only promise actions that are already in the chat. Do not mention internal teams or checks (such as a dispatch team or a manager) unless the chat already does. If the buyer is waiting for a price approval, say you are confirming and will reply shortly. Do not offer a number.
- Answer what the buyer actually asked in the first sentence, but ONLY with facts already confirmed in the chat.
- If the buyer asks whether something is possible (for example delivery by a certain date, a discount, or stock) and the chat has not confirmed it, do NOT say yes. Say you are confirming and will reply shortly.
- Never repeat a question the rep has already asked in the chat.
- No formal sign-offs such as "Best regards". Do not say which company the rep works for.
- If the status is "deferred", write the message as if it will be sent on the date the buyer asked for.
- If there is no chat, write a friendly first message mentioning their enquiry from the lead source. Introduce yourself with your first name only, for example "this is Vikram".
- If the buyer bought elsewhere, write a short, gracious message that keeps the door open.
- Proofread carefully: no typos, and a space between every word.

LEAD
Name: {name}
Company: {company}
Source: {source}
Rep: {rep}
Last contact: {last_contact}
Days since last contact: {days_since}
Last message was sent by: {last_sender}

CHAT (oldest first)
{chat}

Reply with ONLY a JSON object with exactly these keys: "tag", "reason", "status", "deferred_until", "draft_message".
"""


def format_chat(messages):
    if not messages:
        return "(no chat yet)"
    return "\n".join(f"[{m['date']}] {m['sender']}: {m['text']}" for m in messages)


def last_sender_of(messages):
    return messages[-1]["sender"] if messages else None


def build_prompt(lead, messages, today):
    days_since = (today - date.fromisoformat(lead["last_contact"])).days
    return PROMPT_TEMPLATE.format(
        today=today.strftime("%Y-%m-%d (%A)"),
        name=lead["name"],
        company=lead["company"],
        source=lead["source"],
        rep=lead["rep"],
        last_contact=lead["last_contact"],
        days_since=days_since,
        last_sender=last_sender_of(messages) or "nobody (no chat yet)",
        chat=format_chat(messages),
    )


def call_llm(prompt):
    """Send the prompt to Gemini and return the raw text answer."""
    # Imported here so the app can still start if the AI library/key is missing
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):  # remove ```json fences if the model adds them
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)


VALID_STATUSES = {"buyer_waiting", "rep_waiting", "deferred", "new_lead", "closed"}


def compute_due(status, tag, last_contact, today, deferred_until=None):
    """Turn the AI's judgement into a follow-up date using fixed rules."""
    if status == "buyer_waiting":
        return last_contact                      # was due the day the buyer wrote
    if status == "rep_waiting":
        if tag == "Hot":
            return last_contact + timedelta(days=2)
        if tag == "Warm":
            return last_contact + timedelta(days=4)
        return today + timedelta(days=14)        # Cold: try again later
    if status == "deferred":
        if deferred_until is None:
            return today + timedelta(days=14)
        return max(deferred_until, today)        # never in the past
    if status == "new_lead":
        if tag == "Cold":
            return today + timedelta(days=14)
        return max(last_contact + timedelta(days=2), today)  # first message: 2 days after it came in, or today
    return today + timedelta(days=30)            # closed: check back in a month


def validate(result, lead, messages, today):
    """Check the AI's answer. Raise ValueError if anything is wrong."""
    tag = str(result.get("tag", "")).strip().capitalize()
    if tag not in VALID_TAGS:
        raise ValueError(f"bad tag: {tag!r}")

    reason = str(result.get("reason", "")).strip()
    if not reason:
        raise ValueError("empty reason")

    draft = str(result.get("draft_message", "")).strip()
    if not draft:
        raise ValueError("empty draft")

    status = str(result.get("status", "")).strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"bad status: {status!r}")

    # Impossible combinations: reject so the agent retries
    last_sender = last_sender_of(messages)
    if status == "buyer_waiting" and last_sender != "buyer":
        raise ValueError("status buyer_waiting but the buyer did not send the last message")
    if status == "new_lead" and messages:
        raise ValueError("status new_lead but there is a chat")
    if status in ("buyer_waiting", "rep_waiting") and not messages:
        raise ValueError("waiting status but there is no chat")

    deferred_until = None
    if status == "deferred":
        try:
            deferred_until = date.fromisoformat(str(result.get("deferred_until", "")).strip())
        except ValueError:
            deferred_until = None                # compute_due will use a safe default
        if deferred_until and deferred_until > today + timedelta(days=365):
            deferred_until = None

    last_contact = date.fromisoformat(lead["last_contact"])
    due = compute_due(status, tag, last_contact, today, deferred_until)
    return {"tag": tag, "reason": reason[:300], "next_followup": due.isoformat(),
            "draft": draft, "status": status}


def fallback_analysis(lead, messages, today):
    """Simple rules used when the AI fails, so the app never breaks."""
    first = lead["name"].split()[0]
    last_contact = date.fromisoformat(lead["last_contact"])
    days_since = (today - last_contact).days

    if not messages:
        return {
            "tag": "Warm",
            "reason": "New lead with no conversation yet.",
            "next_followup": today.isoformat(),
            "draft": f"Hi {first}, thanks for your enquiry about our packaging machines. "
                     f"What are you looking to pack, and what is your daily volume?",
        }

    if messages[-1]["sender"] == "buyer":
        tag = "Hot" if days_since <= 7 else "Warm"
        return {
            "tag": tag,
            "reason": "The buyer's last message has not been answered yet.",
            "next_followup": last_contact.isoformat(),
            "draft": f"Hi {first}, sorry for the delay. I am checking this and will get back to you shortly.",
        }

    if days_since <= 7:
        tag, due = "Warm", last_contact + timedelta(days=3)
    elif days_since <= 14:
        tag, due = "Warm", last_contact + timedelta(days=5)
    else:
        tag, due = "Cold", today + timedelta(days=14)
    return {
        "tag": tag,
        "reason": f"No reply from the buyer for {days_since} days.",
        "next_followup": due.isoformat(),
        "draft": f"Hi {first}, just checking if you had a chance to look at the details I shared. "
                 f"Happy to answer any questions.",
    }


def analyze_lead(lead, messages, today=None):
    """Main function: returns tag, reason, next_followup, draft, status, used_fallback."""
    today = today or date.today()
    prompt = build_prompt(lead, messages, today)
    for attempt in (1, 2):  # ask the AI, and retry once if its answer is unusable
        try:
            raw = call_llm(prompt)
            result = validate(parse_json(raw), lead, messages, today)
            result["used_fallback"] = False
            return result
        except Exception as e:  # API error, bad JSON, failed validation...
            print(f"[agent] lead {lead.get('id')}: attempt {attempt} failed ({str(e)[:150]})")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                break  # rate limit: retrying right away only wastes quota, use the fallback
    result = fallback_analysis(lead, messages, today)
    result["used_fallback"] = True
    return result
