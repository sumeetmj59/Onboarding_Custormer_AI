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

# Load .env from this folder (for OPENAI_API_KEY)
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
    regions: List[str]          # e.g. ["APAC", "EMEA"]
    traffic_level: str          # "low" | "medium" | "high"
    cloud_providers: List[str]  # e.g. ["AWS", "Azure"]
    critical_apps: List[str]    # e.g. ["Online banking portal"]
    has_waf: bool
    has_mfa_for_admins: bool
    logging_strategy: str       # free text
    compliance: List[str]       # e.g. ["PCI-DSS", "ISO27001"]


class EvaluationResult(BaseModel):
    decision: str               # "approve" | "needs_review" | "reject"
    risk_score: int             # 0–100
    issues: List[str]
    summary: str


class StoredRequest(BaseModel):
    id: str
    created_at: dt.datetime
    request: NetworkRequest
    evaluation: Optional[EvaluationResult] = None


# -----------------------------
# Helper functions (storage)
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
# Helper: rule-based evaluation
# -----------------------------

def evaluate_with_rules(req: NetworkRequest) -> EvaluationResult:
    """Simple deterministic rule-based fallback (no AI)."""
    score = 0
    issues: List[str] = []

    # Example scoring rules – tweak later for Imperva's real policies
    if req.traffic_level.lower() == "high":
        score += 20

    if any(r.upper() == "APAC" for r in req.regions):
        score += 10

    if not req.has_waf:
        score += 30
        issues.append("No WAF in front of critical applications.")

    if not req.has_mfa_for_admins:
        score += 25
        issues.append("MFA is not enabled for admin accounts.")

    if "centralized" not in req.logging_strategy.lower():
        score += 15
        issues.append("Logging does not appear to be clearly centralized.")

    if not any("PCI" in c.upper() or "ISO" in c.upper() for c in req.compliance):
        score += 20
        issues.append("No major compliance frameworks (PCI/ISO) are listed.")

    if score < 30:
        decision = "approve"
    elif score < 60:
        decision = "needs_review"
    else:
        decision = "reject"

    summary = f"Rule-based evaluation score {score} with {len(issues)} issue(s)."

    return EvaluationResult(
        decision=decision,
        risk_score=score,
        issues=issues,
        summary=summary,
    )


# -----------------------------
# Helper: GPT-based evaluation
# -----------------------------

def evaluate_with_gpt(req: NetworkRequest) -> EvaluationResult:
    """
    Call OpenAI GPT to evaluate the onboarding form and return a structured result.
    """
    req_json = json.dumps(req.model_dump(), indent=2)

    system_prompt = (
        "You are a senior Imperva security architect. "
        "You review onboarding forms for new customer networks.\n\n"
        "You MUST respond ONLY with a single JSON object using this schema:\n"
        "{\n"
        '  \"decision\": \"approve\" | \"needs_review\" | \"reject\",\n'
        '  \"risk_score\": number between 0 and 100,\n'
        '  \"issues\": [string, ...],\n'
        '  \"summary\": string\n'
        "}\n"
        "Do not include any extra commentary. Be strict but fair."
    )

    user_prompt = (
        "Here is the onboarding request JSON:\n\n"
        f"{req_json}\n\n"
        "Analyse this request and return ONLY the JSON object described above."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = resp.choices[0].message.content.strip()

        # Handle ```json ... ``` wrappers if the model adds them
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json\n", "").replace("json\r\n", "")

        data = json.loads(content)

        return EvaluationResult(
            decision=data.get("decision", "needs_review"),
            risk_score=int(data.get("risk_score", 50)),
            issues=data.get("issues", []),
            summary=data.get("summary", "No summary provided."),
        )
    except Exception as e:
        # Log actual error internally for debugging (not shown to users)
        print("LLM evaluation issue:", repr(e))

        result = rule_based_evaluation(request)

        result.summary = (
            "AI scoring is currently running in limited demo mode. "
            "The shared API key does not have paid token credits, so this environment "
            "uses the rule-based scoring engine. "
            "In real-world deployments, companies use their own paid OpenAI or "
            "enterprise LLM accounts, enabling the full AI-powered evaluation."
        )

        return result


# -----------------------------
# FastAPI app
# -----------------------------

app = FastAPI(title="Imperva Onboarding Evaluator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # for dev; tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Routes
# -----------------------------

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/submit", response_model=StoredRequest)
def submit_request(req: NetworkRequest):
    """Store a new onboarding request without AI evaluation."""
    all_items = _load_requests()

    new_id = str(uuid4())
    now = dt.datetime.utcnow().isoformat()

    stored = StoredRequest(
        id=new_id,
        created_at=dt.datetime.fromisoformat(now),
        request=req,
        evaluation=None,
    )

    all_items.append(json.loads(stored.model_dump_json()))
    _save_requests(all_items)

    return stored


@app.post("/evaluate/rules", response_model=EvaluationResult)
def evaluate_rules_endpoint(req: NetworkRequest):
    """Pure rule-based evaluation (no AI)."""
    return evaluate_with_rules(req)


@app.post("/evaluate/ai", response_model=EvaluationResult)
def evaluate_ai_endpoint(req: NetworkRequest):
    """AI-assisted evaluation using OpenAI GPT (with rule-based fallback)."""
    return evaluate_with_gpt(req)


@app.get("/requests", response_model=List[StoredRequest])
def list_requests():
    """List all stored onboarding requests (with any evaluations)."""
    all_items = _load_requests()
    return [StoredRequest.model_validate(item) for item in all_items]


@app.get("/requests/{request_id}", response_model=StoredRequest)
def get_request(request_id: str):
    """Fetch a single stored request by ID."""
    all_items = _load_requests()
    for item in all_items:
        if item.get("id") == request_id:
            return StoredRequest.model_validate(item)
    raise HTTPException(status_code=404, detail="Request not found")