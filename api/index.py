from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from datetime import datetime
import random
import json
import os
import secrets

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI()

# ─── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Supabase ────────────────────────────────────────────────────────────────
# BUG FIX 1: os.getenv() takes a *variable name* (string key), NOT the actual value.
# Wrong:  os.getenv("https://zawft...")  → always returns None
# Right:  os.getenv("SUPABASE_URL")     → reads env var named SUPABASE_URL

def get_supabase():
    url = os.getenv("SUPABASE_URL")   # set this in Vercel + GitHub Secrets
    key = os.getenv("SUPABASE_KEY")   # set this in Vercel + GitHub Secrets
    if not url or not key:
        raise Exception("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
    return create_client(url, key)

# BUG FIX 2: supabase global was commented out → NameError everywhere.
# We create it once at startup so all functions can use it.
try:
    supabase = get_supabase()
except Exception as e:
    supabase = None
    print(f"[WARNING] Supabase not initialized: {e}")

# ─── Load kurals.json ────────────────────────────────────────────────────────
# BUG FIX 3: dirname(dirname(__file__)) goes UP two levels — wrong for api/index.py.
# Your structure: root/api/index.py and root/kurals.json
# So we only need to go up ONE level (dirname once).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
file_path = os.path.join(BASE_DIR, "kurals.json")

try:
    with open(file_path, "r", encoding="utf-8") as f:
        kurals = json.load(f)
except FileNotFoundError:
    kurals = []
    print(f"[WARNING] kurals.json not found at {file_path}")
@app.get("/hello")
def hello():
    return {"message": "hello working"}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def generate_api_key():
    return secrets.token_urlsafe(32)

def get_db():
    """Returns supabase client or raises a clean HTTP error."""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not connected. Check SUPABASE_URL and SUPABASE_KEY env vars.")
    return supabase

# BUG FIX 4: validate_api_key was calling bare `supabase` (NameError when commented out).
# Now uses get_db() which gives a clear error message if env vars are missing.
def validate_api_key(api_key: str):
    db = get_db()
    response = db.table("api_keys").select("*").eq("api_key", api_key).execute()

    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    user = response.data[0]

    # Daily reset
    today = datetime.utcnow().date()
    last_reset = datetime.fromisoformat(user["last_reset"]).date()

    if today > last_reset:
        db.table("api_keys").update({
            "usage_count": 0,
            "last_reset": str(today)
        }).eq("api_key", api_key).execute()
        user["usage_count"] = 0

    # Limit check
    if user["usage_count"] >= user["limit_per_day"]:
        raise HTTPException(status_code=429, detail="Daily limit exceeded")

    # Increment usage
    db.table("api_keys").update({
        "usage_count": user["usage_count"] + 1
    }).eq("api_key", api_key).execute()

    return user

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"message": "Tamil Kural API running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/hello")
def hello():
    return {"message": "hello working"}

# BUG FIX 5: Duplicate /test-db route removed (FastAPI silently ignores the second one).
@app.get("/test-db")
def test_db():
    try:
        db = get_db()
        res = db.table("api_keys").select("*").limit(1).execute()
        return {"status": "success", "data": res.data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug-env")
def debug_env():
    return {
        "SUPABASE_URL_set": os.getenv("SUPABASE_URL") is not None,
        "SUPABASE_KEY_set": os.getenv("SUPABASE_KEY") is not None,
        "kurals_loaded": len(kurals),
        "kurals_path": file_path,
    }

# ─── API Key Management ───────────────────────────────────────────────────────

@app.post("/create-api-key")
def create_api_key(plan: str = "free"):
    db = get_db()
    key = generate_api_key()
    limit = 100 if plan == "free" else 1000

    db.table("api_keys").insert({
        "api_key": key,
        "plan": plan,
        "limit_per_day": limit,
        "usage_count": 0,
        "last_reset": str(datetime.utcnow().date())
    }).execute()

    return {
        "api_key": key,
        "plan": plan,
        "limit_per_day": limit
    }

# ─── Kural Endpoints ─────────────────────────────────────────────────────────

@app.get("/kural/{kural_id}")
def get_kural(kural_id: int, api_key: str = Query(...)):
    validate_api_key(api_key)
    for k in kurals:
        if k["id"] == kural_id:
            return {
                "id": k["id"],
                "tamil": k.get("tamil"),
                "meaning": k.get("meaning")
            }
    raise HTTPException(status_code=404, detail="Kural not found")

@app.get("/random")
def random_kural(api_key: str = Query(...)):
    validate_api_key(api_key)
    if not kurals:
        raise HTTPException(status_code=500, detail="No kurals loaded")
    return random.choice(kurals)

@app.get("/search")
def search_kural(q: str, api_key: str = Query(...)):
    validate_api_key(api_key)
    results = [
        k for k in kurals
        if q.lower() in k.get("tamil", "").lower()
        or q.lower() in k.get("meaning", "").lower()
    ]
    return {"count": len(results), "results": results}

@app.get("/filter")
def filter_kural(category: str, api_key: str = Query(...)):
    validate_api_key(api_key)
    results = [
        k for k in kurals
        if k.get("category", "").lower() == category.lower()
    ]
    return {"count": len(results), "results": results}