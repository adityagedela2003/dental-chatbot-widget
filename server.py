from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import anthropic
import os
import re
from dotenv import load_dotenv
from typing import Optional, List, Dict

load_dotenv()

app = FastAPI()

# ── CORS — allows any website to call this API ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # In production, replace * with client's domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Anthropic client ──────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"

# ── CLINIC CONSTANTS ──────────────────────────────────────────────────────────
CLINIC_NAME     = "Bright Smile Dental Clinic"
CLINIC_PHONE    = "+91 98765 43210"
CLINIC_ADDRESS  = "12, MG Road, Bengaluru, Karnataka 560001"
CLINIC_MAPS_URL = "https://maps.google.com/?q=Bright+Smile+Dental+MG+Road+Bengaluru"
CLINIC_HOURS    = "Mon–Fri: 9AM–7PM | Sat: 9AM–5PM | Sun: Closed"

# ── LOAD KNOWLEDGE BASE ───────────────────────────────────────────────────────
def load_knowledge_base():
    try:
        with open("clinic_knowledge.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Knowledge base not found."

KNOWLEDGE_BASE = load_knowledge_base()

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""
You are Aria, a warm, professional, and knowledgeable virtual assistant for {CLINIC_NAME}.
You have TWO roles — handle both naturally in the same conversation:

ROLE 1 — GENERAL CLINIC ASSISTANT:
Answer any questions the visitor has about the clinic using ONLY the knowledge base below.
This includes treatments, prices, hours, location, policies, FAQs, insurance, payments etc.
- Answer ONLY from the knowledge base. Do NOT guess or make up anything.
- If something is genuinely not in the knowledge base, say: "I don't have that info right
  now — our receptionist will be happy to help when they call you!"
- For location questions, always share the address AND this Google Maps link: {CLINIC_MAPS_URL}
- For phone questions, share: {CLINIC_PHONE}
- Keep answers concise and friendly.

ROLE 2 — LEAD CAPTURE AGENT:
When the visitor shows interest in booking or visiting, guide them through these steps
ONE question at a time:
1. Ask the reason for their visit.
2. Ask if they are a new or returning patient.
3. Ask for their full name.
4. Ask for their Indian mobile number (+91 format).
5. Ask them to re-enter the number to confirm.
   (You will be told by the system if it matched or not — act accordingly.)
6. Once confirmed, summarize their details and say the receptionist will call them shortly.

CRITICAL RULES:
- ALWAYS answer general questions from the knowledge base at ANY point in the conversation
  — before, during, or after lead capture. Never stop being helpful.
- Ask only ONE question at a time.
- NEVER offer specific appointment times or slots.
- NEVER give medical advice or diagnosis.
- If someone describes severe symptoms (extreme pain, swelling, difficulty breathing),
  advise them to go to the ER immediately, then offer to collect their info for follow-up.
- Keep responses concise — this is a chat widget, not an essay.
- Format responses clearly using this simple style:
  * Use **bold** for treatment names, prices, and important words
  * Use bullet points (starting with -) when listing multiple items like treatments or policies
  * Use line breaks between sections for readability
  * For prices always show like: Root Canal: Rs.3,500 - Rs.7,000
  * Never use headers like ## or ### — just bold and bullets are enough
  * Keep each bullet point short — one line max

================================================================
CLINIC KNOWLEDGE BASE:
================================================================
{KNOWLEDGE_BASE}
================================================================
"""

# ── PHONE VALIDATION ──────────────────────────────────────────────────────────
def validate_indian_phone(text: str):
    cleaned = re.sub(r"[\s\-\.]", "", text)
    match = re.search(r"(?:\+91|91|0)?([6-9]\d{9})", cleaned)
    if match and len(match.group(1)) == 10:
        return f"+91{match.group(1)}"
    return None

# ── REQUEST / RESPONSE MODELS ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    messages: list           # full conversation history [{role, content}]
    phone_first: Optional[str] = None  # first phone entry (or null)
    awaiting_confirm: bool   # are we waiting for phone confirmation?
    phone_confirmed: bool    # has phone been confirmed already?

class ChatResponse(BaseModel):
    reply: str
    phone_first: Optional[str] = None
    awaiting_confirm: bool
    phone_confirmed: bool
    lead: Optional[Dict] = None  # filled when lead capture is complete

# ── CHAT ENDPOINT ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):

    messages        = req.messages
    phone_first     = req.phone_first
    awaiting_confirm = req.awaiting_confirm
    phone_confirmed  = req.phone_confirmed

    user_text  = messages[-1]["content"] if messages else ""
    inject_note = ""
    lead        = None

    # ── Phone validation logic ────────────────────────────────────────────────
    if not phone_confirmed:
        validated = validate_indian_phone(user_text)

        if awaiting_confirm:
            if validated:
                if validated == phone_first:
                    phone_confirmed  = True
                    awaiting_confirm = False
                    inject_note = (
                        f"[SYSTEM NOTE: Phone confirmed successfully. "
                        f"Both entries matched: {validated}. "
                        f"Now do the closing step — summarize their name, reason, "
                        f"patient status, and phone number, then say the receptionist "
                        f"will call them shortly to schedule the appointment.]"
                    )
                else:
                    phone_first      = None
                    awaiting_confirm = False
                    inject_note = (
                        "[SYSTEM NOTE: The two phone numbers did NOT match. "
                        "Tell the user kindly and ask them to enter their phone number again.]"
                    )
            else:
                inject_note = (
                    "[SYSTEM NOTE: The confirmation entry was not a valid Indian phone number. "
                    "Ask them to re-enter a valid +91 number.]"
                )

        else:
            if validated:
                phone_first      = validated
                awaiting_confirm = True
                inject_note = (
                    f"[SYSTEM NOTE: Valid Indian phone received: {validated}. "
                    f"Ask the user to re-enter the same number to confirm it.]"
                )
            elif re.search(r'\d{5,}', user_text):
                inject_note = (
                    "[SYSTEM NOTE: User entered something that looks like a phone number "
                    "but it is NOT valid. Must be 10 digits starting with 6-9. "
                    "Explain politely and ask again.]"
                )

    # ── Build API messages ────────────────────────────────────────────────────
    api_messages = messages[:-1] + [{
        "role": "user",
        "content": f"{user_text}\n\n{inject_note}" if inject_note else user_text
    }]

    # ── Call Claude ───────────────────────────────────────────────────────────
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=api_messages,
        temperature=0.3,
    )
    reply = response.content[0].text

    # ── Extract lead when capture is complete ─────────────────────────────────
    if phone_confirmed:
        # Try to extract lead data from conversation history
        lead = extract_lead(messages, phone_first)

    return ChatResponse(
        reply=reply,
        phone_first=phone_first,
        awaiting_confirm=awaiting_confirm,
        phone_confirmed=phone_confirmed,
        lead=lead,
    )

# ── LEAD EXTRACTOR ────────────────────────────────────────────────────────────
def extract_lead(messages: list, phone: str):
    """Ask Claude to extract structured lead data from the conversation."""
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    extraction_prompt = f"""
From this conversation, extract the following fields as plain text:
- name: (full name of the patient)
- reason: (reason for visit)
- patient_status: (new or returning)
- phone: (use {phone})

Conversation:
{conversation_text}

Reply in this exact format (no extra text):
name: <value>
reason: <value>
patient_status: <value>
phone: <value>
"""
    result = client.messages.create(
        model=MODEL,
        max_tokens=150,
        messages=[{"role": "user", "content": extraction_prompt}],
        temperature=0,
    )
    raw = result.content[0].text.strip()
    lead = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            lead[key.strip()] = val.strip()

    # Print to terminal (simulating DB save / email to clinic)
    print("\n" + "="*50)
    print("NEW LEAD CAPTURED")
    print("="*50)
    for k, v in lead.items():
        print(f"  {k.upper()}: {v}")
    print("="*50 + "\n")

    return lead

# ── SERVE STATIC FILES ────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/widget.js")
async def serve_widget():
    return FileResponse("static/widget.js", media_type="application/javascript")
