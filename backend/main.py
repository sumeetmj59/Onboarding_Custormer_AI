# main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import uuid4
from pathlib import Path
import json
import datetime as dt
import os

from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# Environment / OpenAI setup
# -----------------------------

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Storage paths
# -----------------------------

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
REQUESTS_FILE = DATA_DIR / "requests.json"


# -----------------------------
# Models
# -----------------------------

class NetworkRequest(BaseModel):
    company_name: str
    industry: str
    contact_email: EmailStr
    regions: List[str]
    traffic_level: str           # low / medium / high
    cloud_providers: List[str]
    critical_apps: List[str]
    has_waf: bool
    has_mfa_for_admins: bool
    logging_strategy: str
    compliance: List[str]


class EvaluationResult(BaseModel):
    decision: str                # approve / needs_review / reject
    risk_score: int              # 0–100
    issues: List[str]
    summary: str


class StoredRequest(BaseModel):
    id: str
    created_at: dt.datetime
    request: NetworkRequest
    evaluation: Optional[EvaluationResult] = None


# -----------------------------
# Local JSON storage
# -----------------------------

def _load_requests() -> List[dict]:
    if not REQUESTS_FILE.exists():
        return []
    with REQUESTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_requests(items: List[dict]) -> None:
    with REQUESTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, default=str)


# -----------------------------
# Rule-based fallback engine
# -----------------------------

def evaluate_with_rules(req: NetworkRequest) -> EvaluationResult:
    score = 0
    issues = []

    if req.traffic_level.lower() == "high":
        score += 25
        issues.append("High expected traffic volume.")

    if len(req.regions) > 1:
        score += 15
        issues.append("Multiple regions increase attack surface.")

    if not req.has_waf:
        score += 25
        issues.append("No Web Application Firewall (WAF) present.")

    if not req.has_mfa_for_admins:
        score += 20
        issues.append("MFA disabled for admin accounts.")

    if "centralized" not in req.logging_strategy.lower():
        score += 10
        issues.append("Logging is not centralized.")

    if not any("PCI" in c.upper() or "ISO" in c.upper() for c in req.compliance):
        score += 15
        issues.append("Missing PCI/ISO compliance.")

    if score < 30:
        decision = "approve"
    elif score < 60:
        decision = "needs_review"
    else:
        decision = "reject"

    summary = (
        f"Rule-based fallback risk score: {score}/100 "
        f"with {len(issues)} issue(s)."
    )

    return EvaluationResult(
        decision=decision,
        risk_score=score,
        issues=issues,
        summary=summary
    )


# -----------------------------
# REAL GPT-based evaluation
# -----------------------------

def evaluate_with_gpt(req: NetworkRequest) -> EvaluationResult:
    req_json = json.dumps(req.model_dump(), indent=2)

    system_prompt = (
        "You are a senior Imperva security architect. "
        "You evaluate onboarding requests for new customer networks.\n\n"
        "Return ONLY a JSON object with:\n"
        "{\n"
        '  \"decision\": \"approve\" | \"needs_review\" | \"reject\",\n'
        '  \"risk_score\": integer 0-100,\n'
        '  \"issues\": [string],\n'
        '  \"summary\": string\n'
        "}\n"
        "Scoring guidance:\n"
        "- High risk: no WAF, no MFA, critical banking apps, high traffic, many regions.\n"
        "- Low risk: strong controls, PCI/ISO compliance, WAF/MFA enabled.\n"
        "Do NOT add extra text outside the JSON."
    )

    user_prompt = (
        "Evaluate this customer onboarding request:\n\n"
        f"{req_json}\n\n"
        "Return ONLY the JSON response."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content.strip()

        # Remove ```json wrappers if present
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json\n", "")

        data = json.loads(content)

        return EvaluationResult(
            decision=data.get("decision", "needs_review"),
            risk_score=int(data.get("risk_score", 50)),
            issues=data.get("issues", []),
            summary=data.get("summary", "")
        )

    except Exception as e:
        print("[WARN] GPT evaluation error, falling back:", e)
        fallback = evaluate_with_rules(req)
        fallback.summary = (
            "AI evaluation temporarily failed. "
            "This result was generated by the fallback rule-based engine."
        )
        return fallback


# -----------------------------
# FastAPI Application
# -----------------------------

app = FastAPI(title="Imperva Onboarding Evaluator (AI-Driven)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/evaluate/ai", response_model=EvaluationResult)
def evaluate_ai_endpoint(req: NetworkRequest):
    return evaluate_with_gpt(req)


@app.post("/evaluate/rules", response_model=EvaluationResult)
def evaluate_rules_endpoint(req: NetworkRequest):
    return evaluate_with_rules(req)


@app.post("/submit", response_model=StoredRequest)
def submit_request(req: NetworkRequest):
    all_items = _load_requests()

    new_id = str(uuid4())
    now = dt.datetime.utcnow().isoformat()

    stored = StoredRequest(
        id=new_id,
        created_at=dt.datetime.fromisoformat(now),
        request=req,
        evaluation=None
    )

    all_items.append(json.loads(stored.model_dump_json()))
    _save_requests(all_items)

    return stored


@app.get("/requests", response_model=List[StoredRequest])
def list_requests():
    all_items = _load_requests()
    return [StoredRequest.model_validate(i) for i in all_items]


@app.get("/requests/{request_id}", response_model=StoredRequest)
def get_request(request_id: str):
    all_items = _load_requests()
    for item in all_items:
        if item.get("id") == request_id:
            return StoredRequest.model_validate(item)
    raise HTTPException(status_code=404, detail="Request not found")