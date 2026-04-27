from fastapi import FastAPI, HTTPException, Query
from supabase import create_client
from datetime import datetime
import random
import json
import os
import secrets

app = FastAPI()

# ✅ Supabase connection
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise Exception("Missing Supabase ENV")

    return create_client(url, key)

# ✅ Load JSON (fix for Vercel)
BASE_DIR = os.path.dirname(__file__)
file_path = os.path.join(BASE_DIR, "../data/kurals.json")

with open(file_path, "r", encoding="utf-8") as f:
    kurals = json.load(f)

# 🔐 Generate API key
def generate_api_key():
    return secrets.token_urlsafe(32)

# ✅ Validate API key
def validate_api_key(api_key: str):
    supabase = get_supabase()

    res = supabase.table("api_keys").select("*").eq("api_key", api_key).execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    user = res.data[0]

    # daily reset
    today = datetime.utcnow().date()
    last_reset = datetime.fromisoformat(user["last_reset"]).date()

    if today > last_reset:
        supabase.table("api_keys").update({
            "usage_count": 0,
            "last_reset": str(today)
        }).eq("api_key", api_key).execute()

        user["usage_count"] = 0

    if user["usage_count"] >= user["limit_per_day"]:
        raise HTTPException(status_code=429, detail="Limit exceeded")

    supabase.table("api_keys").update({
        "usage_count": user["usage_count"] + 1
    }).eq("api_key", api_key).execute()

# 🏠 Home
@app.get("/")
def home():
    return {"message": "Tamil Kural API running"}

# 🔑 Create API key
@app.post("/create-api-key")
def create_api_key():
    supabase = get_supabase()

    key = generate_api_key()

    supabase.table("api_keys").insert({
        "api_key": key,
        "plan": "free",
        "limit_per_day": 100,
        "usage_count": 0,
        "last_reset": str(datetime.utcnow().date())
    }).execute()

    return {"api_key": key}

# 📖 Get Kural
@app.get("/kural/{id}")
def get_kural(id: int, api_key: str = Query(...)):
    validate_api_key(api_key)

    for k in kurals:
        if k["id"] == id:
            return {
                "line1": k["Line1"],
                "line2": k["Line2"],
                "meaning": k["Translation"]
            }

    return {"error": "Not found"}

# 🎲 Random
@app.get("/random")
def random_kural(api_key: str = Query(...)):
    validate_api_key(api_key)
    return random.choice(kurals)