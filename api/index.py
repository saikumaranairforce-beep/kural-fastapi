from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from datetime import datetime
import random
import json
import os
import secrets

# 🚀 Create app
app = FastAPI()

# 🌐 CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 Supabase setup (PUT YOUR VALUES)
SUPABASE_URL = os.getenv("https://zawftoslsjbptffmtwpb.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inphd2Z0b3Nsc2picHRmZm10d3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxNzUyOTQsImV4cCI6MjA5Mjc1MTI5NH0.0BBcsCCgewtd3GeZ27VsxqvHxqMqL9O9PQbFMnMEFR4")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 📂 Load JSON data
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
file_path = os.path.join(BASE_DIR, "kurals.json")

with open(file_path, "r", encoding="utf-8") as f:
    kurals = json.load(f)

# 🔐 Generate API key
def generate_api_key():
    return secrets.token_urlsafe(32)

# ✅ Validate API key + usage
def validate_api_key(api_key: str):
    response = supabase.table("api_keys").select("*").eq("api_key", api_key).execute()

    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    user = response.data[0]

    # 🔄 Daily reset
    today = datetime.utcnow().date()
    last_reset = datetime.fromisoformat(user["last_reset"]).date()

    if today > last_reset:
        supabase.table("api_keys").update({
            "usage_count": 0,
            "last_reset": str(today)
        }).eq("api_key", api_key).execute()
        user["usage_count"] = 0

    # 🚫 Limit check
    if user["usage_count"] >= user["limit_per_day"]:
        raise HTTPException(status_code=429, detail="Daily limit exceeded")

    # ➕ Increase usage
    supabase.table("api_keys").update({
        "usage_count": user["usage_count"] + 1
    }).eq("api_key", api_key).execute()

    return user
@app.get("/debug-env")
def debug_env():
    return {
        "url": SUPABASE_URL,
        "key_exists": SUPABASE_KEY is not None
    }
    
@app.get("/test-db")
def test_db():
    try:
        res = supabase.table("api_keys").select("*").limit(1).execute()
        return {
            "status": "success",
            "data": res.data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# 🏠 Home
@app.get("/")
def home():
    return {"message": "Tamil Kural API running"}

# ❤️ Health check
@app.get("/health")
def health():
    return {"status": "ok"}

# 🔑 Create API key
@app.post("/create-api-key")
def create_api_key(plan: str = "free"):
    key = generate_api_key()

    limit = 100 if plan == "free" else 1000

    supabase.table("api_keys").insert({
        "api_key": key,
        "plan": plan,
        "limit_per_day": limit,
        "usage_count": 0,
        "last_reset": str(datetime.utcnow().date())
    }).execute()

    return {
        "api_key": key,
        "plan": plan,
        "limit": limit
    }

# 📖 Get Kural by ID
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

    return {"error": "Kural not found"}

# 🎲 Random
@app.get("/random")
def random_kural(api_key: str = Query(...)):
    validate_api_key(api_key)
    return random.choice(kurals)

# 🔍 Search
@app.get("/search")
def search_kural(q: str, api_key: str = Query(...)):
    validate_api_key(api_key)

    results = [
        k for k in kurals
        if q.lower() in k.get("tamil", "").lower()
        or q.lower() in k.get("meaning", "").lower()
    ]

    return {"count": len(results), "results": results}

# 🧭 Filter
@app.get("/filter")
def filter_kural(category: str, api_key: str = Query(...)):
    validate_api_key(api_key)

    results = [
        k for k in kurals
        if k.get("category", "").lower() == category.lower()
    ]

    return {"count": len(results), "results": results}