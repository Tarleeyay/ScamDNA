# ScamDNA Guard Demo

Live Demo: https://<Tarleeyay>.github.io/<ScamDNA>/

## What it does
Paste a suspicious message -> get:
- Risk score
- Scam DNA profile (Urgency/Authority/Payment Trap/Trust Hijack/etc.)
- Explainable human-friendly reasons
- Safety tips

## Run locally
### Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

### Frontend
Open docs/index.html (or use Live Server)
