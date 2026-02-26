from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import anthropic
import os
import re
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from typing import Optional, List, Dict

load_dotenv()

app = FastAPI()

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
CLINIC_HOURS    = "Mon-Fri: 9AM-7PM | Sat: 9AM-5PM | Sun: Closed"

# ── GOOGLE SHEETS SETUP ───────────────────────────────────────────────────────
def get_gsheet():
    """Connect to Google Sheets using service account credentials."""
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_json:
            print("WARNING: GOOGLE_CREDENTIALS not set. Leads will only print to terminal.")
            return None
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open(os.getenv("GOOGLE_SHEET_NAME", "Dental Leads")).sheet1
        return sheet
    except Exception as e:
        print(f"Google Sheets connection failed: {e}")
        return None

def save_lead_to_sheet(lead: dict):
    """Append a lead row to Google Sheets."""
    try:
        sheet = get_gsheet()
        if sheet is None:
            return False
        from datetime import datetime
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            lead.get("name", ""),
            lead.get("phone", ""),
            lead.get("reason", ""),
            lead.get("patient_status", ""),
            "New Lead"
        ]
        sheet.append_row(row)
        print("Lead saved to Google Sheets successfully!")
        return True
    except Exception as e:
        print(f"Failed to save to Google Sheets: {e}")
        return False

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
You have TWO roles - handle both naturally in the same conversation:

ROLE 1 - GENERAL CLINIC ASSISTANT:
Answer any questions the visitor has about the clinic using ONLY the knowledge base below.
This includes treatments, prices, hours, location, policies, FAQs, insurance, payments etc.
- Answer ONLY from the knowledge base. Do NOT guess or make up anything.
- If something is genuinely not in the knowledge base, say: "I don't have that info right
  now - our receptionist will be happy to help when they call you!"
- For location questions, always share the address AND this Google Maps link: {CLINIC_MAPS_URL}
- For phone questions, share: {CLINIC_PHONE}
- Keep answers concise and friendly.

ROLE 2 - LEAD CAPTURE AGENT:
When the visitor shows interest in booking or visiting, guide them through these steps
ONE question at a time:
1. Ask the reason for their visit.
2. Ask if they are a new or returning patient.
3. Ask for their full name.
4. Ask for their Indian mobile number (+91 format).
   (The system will validate it automatically - you will be told if it is valid or not.)
5. Once phone is confirmed valid, summarize their details and say the receptionist will call them shortly.

CRITICAL RULES:
- ALWAYS answer general questions from the knowledge base at ANY point in the conversation
  before, during, or after lead capture. Never stop being helpful.
- Ask only ONE question at a time.
- NEVER offer specific appointment times or slots.
- NEVER give medical advice or diagnosis.
- If someone describes severe symptoms (extreme pain, swelling, difficulty breathing),
  advise them to go to the ER immediately, then offer to collect their info for follow-up.
- Keep responses concise - this is a chat widget, not an essay.
- Format responses clearly:
  * Use **bold** for treatment names, prices, and important words
  * Use bullet points (starting with -) when listing multiple items
  * For prices always show like: Root Canal: Rs.3,500 - Rs.7,000
  * Never use headers like ## or ### - just bold and bullets are enough
  * Keep each bullet point short - one line max

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
    messages: list
    phone_confirmed: bool
    lead_saved: bool        # True once lead has been saved to sheet — never save again

class ChatResponse(BaseModel):
    reply: str
    phone_confirmed: bool
    lead_saved: bool
    lead: Optional[Dict] = None

# ── CHAT ENDPOINT ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):

    messages        = req.messages
    phone_confirmed = req.phone_confirmed
    lead_saved      = req.lead_saved      # if True, never save again
    user_text       = messages[-1]["content"] if messages else ""
    inject_note     = ""
    lead            = None
    just_confirmed  = False

    # ── Phone validation ──────────────────────────────────────────────────────
    if not phone_confirmed:
        validated = validate_indian_phone(user_text)
        if validated:
            phone_confirmed = True
            just_confirmed  = True
            inject_note = (
                f"[SYSTEM NOTE: Valid Indian phone number received: {validated}. "
                f"Phone is confirmed. Now do the closing step - summarize their name, "
                f"reason, patient status, and phone number {validated}, then say the "
                f"receptionist will call them shortly to schedule the appointment.]"
            )
        elif re.search(r'\d{5,}', user_text):
            inject_note = (
                "[SYSTEM NOTE: User entered something that looks like a phone number "
                "but it is NOT a valid Indian mobile number. Must be 10 digits starting "
                "with 6, 7, 8, or 9. Explain politely and ask again.]"
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

    # ── Save lead only once — when phone is confirmed AND lead not yet saved ───
    # We include reply in messages so extract_lead has the full closing summary
    if just_confirmed and not lead_saved:
        full_messages = messages + [{"role": "assistant", "content": reply}]
        lead = extract_lead(full_messages, user_text)
        if lead and lead.get("name") and lead.get("phone"):
            saved = save_lead_to_sheet(lead)
            if saved:
                lead_saved = True   # mark as saved so it never runs again
        
    return ChatResponse(
        reply=reply,
        phone_confirmed=phone_confirmed,
        lead_saved=lead_saved,
        lead=lead,
    )

# ── LEAD EXTRACTOR ────────────────────────────────────────────────────────────
def extract_lead(messages: list, last_message: str):
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    extraction_prompt = f"""
From this conversation, extract these fields:
- name: full name of the patient
- reason: reason for visit
- patient_status: new or returning
- phone: the phone number they provided

Conversation:
{conversation_text}
Last message: {last_message}

Reply in this exact format only (no extra text):
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

    print("\n" + "="*50)
    print("NEW LEAD CAPTURED")
    print("="*50)
    for k, v in lead.items():
        print(f"  {k.upper()}: {v}")
    print("="*50 + "\n")

    return lead

# ── DEBUG ENDPOINT ───────────────────────────────────────────────────────────
@app.get("/test-sheets")
async def test_sheets():
    """Test Google Sheets connection - remove after debugging."""
    import traceback
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_json:
            return {"status": "error", "message": "GOOGLE_CREDENTIALS env var not set"}
        
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Dental Leads")
        sheet = gc.open(sheet_name).sheet1
        
        # Try writing a test row
        from datetime import datetime
        sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), "TEST", "+91TEST", "Test", "Test", "Test Row"])
        return {"status": "success", "message": f"Connected to sheet: {sheet_name} and wrote test row!"}
    
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

# ── SERVE STATIC FILES ────────────────────────────────────────────────────────
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/widget.js")
async def serve_widget():
    return FileResponse("static/widget.js", media_type="application/javascript")

app.mount("/static", StaticFiles(directory="static"), name="static")
