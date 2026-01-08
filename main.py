from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI(title="ScamDNA Guard Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    text: str

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

DNA_KEYS = ["urgency", "authority", "payment_trap", "fear", "reward", "trust_hijack"]

# Simple pattern bank (tuneable)
PATTERNS = {
    "urgency": [
        r"\burgent\b", r"\bimmediately\b", r"\bwithin\b.*\b(minutes?|hours?)\b",
        r"ด่วน", r"ทันที", r"ภายใน\s*\d+\s*(นาที|ชั่วโมง)", r"หมดเขต", r"เร่งด่วน"
    ],
    "authority": [
        r"\bbank\b", r"\bofficial\b", r"\bpolice\b", r"\bgovernment\b",
        r"ธนาคาร", r"เจ้าหน้าที่", r"ตำรวจ", r"กรม", r"หน่วยงาน"
    ],
    "payment_trap": [
        r"\btransfer\b", r"\bpay\b", r"\bpayment\b", r"\bwallet\b", r"\bcrypto\b",
        r"โอน", r"จ่าย", r"ชำระ", r"พร้อมเพย์", r"วอลเล็ท", r"คริปโต"
    ],
    "fear": [
        r"\bsuspend(ed)?\b", r"\blocked\b", r"\blegal\b", r"\bviolation\b",
        r"ระงับ", r"ถูกล็อก", r"ผิดกฎหมาย", r"ดำเนินคดี", r"ถูกปิด"
    ],
    "reward": [
        r"\bwin\b", r"\bprize\b", r"\brefund\b", r"\bbonus\b", r"\bfree\b",
        r"รางวัล", r"ของฟรี", r"คืนเงิน", r"โบนัส", r"แจก"
    ],
    "trust_hijack": [
        r"http[s]?://", r"\bbit\.ly\b", r"\btinyurl\b", r"\.xyz\b", r"\.top\b",
        r"คลิก", r"ลิงก์", r"สแกน", r"QR"
    ]
}

def score_dimension(text: str, patterns: list[str]) -> int:
    hits = 0
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            hits += 1
    # scale: each hit adds 20 (cap 100)
    return clamp(hits * 20)

def extract_highlights(text: str):
    # highlight suspicious tokens (simple)
    keywords = ["ด่วน","ทันที","ระงับ","โอน","ชำระ","รางวัล","คลิก","สแกน","เจ้าหน้าที่","ธนาคาร",
                "urgent","immediately","suspend","transfer","pay","prize","refund","click","scan","bank"]
    found = []
    for k in keywords:
        if re.search(rf"\b{re.escape(k)}\b", text, flags=re.IGNORECASE):
            found.append(k)
    # keep unique, short
    uniq = []
    for x in found:
        if x.lower() not in [u.lower() for u in uniq]:
            uniq.append(x)
    return uniq[:8]

def overall_risk(dna: dict) -> int:
    # Weighted: payment + trust + urgency + authority matter more
    w = {
        "payment_trap": 0.25,
        "trust_hijack": 0.20,
        "urgency": 0.20,
        "authority": 0.15,
        "fear": 0.10,
        "reward": 0.10,
    }
    risk = 0.0
    for k, weight in w.items():
        risk += dna[k] * weight
    return int(clamp(round(risk)))

def level_from_score(score: int) -> str:
    if score >= 71: return "HIGH"
    if score >= 31: return "SUSPICIOUS"
    return "SAFE"

def generate_explanation(dna: dict) -> str:
    # pick top 2 traits
    top = sorted(dna.items(), key=lambda x: x[1], reverse=True)[:2]
    mapping = {
        "urgency": "urgency (forcing fast decisions)",
        "authority": "authority impersonation (posing as a trusted institution)",
        "payment_trap": "payment trap (pushing you to transfer/pay outside normal flow)",
        "fear": "fear tactic (threatening consequences)",
        "reward": "reward bait (promising prizes/refunds)",
        "trust_hijack": "trust hijack (suspicious links/QR to move you off-platform)"
    }
    traits = ", ".join(mapping[k] for k, _ in top if _ > 0)
    if not traits:
        return "No strong scam patterns detected. Still verify the sender if you are unsure."
    return f"This message shows signs of {traits}. Scammers use these tactics to reduce careful thinking and trigger quick actions."

def generate_tips(dna: dict):
    tips = []
    if dna["trust_hijack"] >= 40:
        tips.append("Avoid clicking links/QR from messages. Use official apps or type the website yourself.")
    if dna["payment_trap"] >= 40:
        tips.append("Never transfer money or share OTP from a message. Confirm via official bank channels.")
    if dna["urgency"] >= 40 or dna["fear"] >= 40:
        tips.append("Pause before acting. Urgent threats are a common scam tactic.")
    if dna["authority"] >= 40:
        tips.append("Verify the sender identity. Real institutions won’t pressure you via random SMS/chat.")
    if dna["reward"] >= 40:
        tips.append("Be cautious of prizes/refunds you didn’t request. Check with the official service.")
    if not tips:
        tips.append("If unsure, verify through an official contact method before taking any action.")
    return tips[:3]

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    text = req.text.strip()
    dna = {}
    for k in DNA_KEYS:
        dna[k] = score_dimension(text, PATTERNS[k])

    risk = overall_risk(dna)
    level = level_from_score(risk)

    return {
        "risk_score": risk,
        "risk_level": level,
        "dna": dna,
        "highlights": extract_highlights(text),
        "explanation": generate_explanation(dna),
        "tips": generate_tips(dna),
    }
