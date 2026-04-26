from fastapi import FastAPI, Query, HTTPException
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import os



app = FastAPI(root_path="/api")

API_KEYS = {
    "free123": {"limit": 10, "usage": 0},
    "pro123": {"limit": 1000, "usage": 0},
}
@app.get("/generate-key")
def generate_key():
    return {"api_key": "free123"}  # later generate dynamically

# ✅ Enable CORS (for your GitHub site later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def validate_api_key(api_key: str):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    user = API_KEYS[api_key]

    if user["usage"] >= user["limit"]:
        raise HTTPException(status_code=429, detail="Usage limit exceeded")

    user["usage"] += 1
    return user 
    user = validate_api_key(api_key)
# ✅ Load JSON file
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
file_path = os.path.join(BASE_DIR, "kurals.json")

with open(file_path, "r", encoding="utf-8") as f:
    kurals = json.load(f)

# 🏠 Home
@app.get("/")
def home():
    return {"message": "Tamil Kural API running"}

# 📖 Get Kural by ID
@app.get("/kural/{kural_id}")
def get_kural(kural_id: int, api_key: str = Query(...)):
    validate_api_key(api_key)

    for k in kurals:
        if k["id"] == kural_id:
            return k 

    return {"error": "Kural not found"}

# 🎲 Random Kural
@app.get("/random")
def random_kural(api_key: str = Query(...)):
    validate_api_key(api_key)
    return random.choice(kurals)
#@app.get("/random")
#def random_kural():
#    return random.choice(kurals)

# 🔍 Search (by word)
@app.get("/search")
def search_kural(q: str = Query(...)):
    results = [
        k for k in kurals
        if q.lower() in k["tamil"].lower() or q.lower() in k["meaning"].lower()
    ]
    return {"count": len(results), "results": results}

# 🧭 Filter by category
@app.get("/filter")
def filter_category(category: str):
    results = [k for k in kurals if k["category"].lower() == category.lower()]
    return {"count": len(results), "results": results}