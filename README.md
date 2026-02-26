# Bright Smile Dental — Embeddable Chat Widget

## Folder Structure

```
dental-widget/
├── server.py              ← FastAPI backend (handles Claude API calls)
├── requirements.txt
├── .env                   ← your Anthropic API key
├── clinic_knowledge.md    ← copy from the Streamlit project
└── static/
    ├── index.html         ← demo page (simulates a client's website)
    └── widget.js          ← the embeddable widget
```

## Setup

```bash
# 1. Create and activate venv
python -m venv venv
source venv/Scripts/activate   # Git Bash
# venv\Scripts\activate        # Windows CMD

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key to .env
echo ANTHROPIC_API_KEY=sk-ant-your-key-here > .env

# 4. Copy clinic_knowledge.md from your Streamlit project into this folder

# 5. Run the server
uvicorn server:app --reload --port 8000
```

## View the demo

Open your browser at: http://localhost:8000

You will see a fake client website with the chat widget floating in the bottom-right corner.

## Embed on any real website

Paste this ONE line before </body> in the client's HTML:

```html
<script src="http://localhost:8000/widget.js"></script>
```

When hosted on a real server, replace localhost:8000 with your actual server URL.
