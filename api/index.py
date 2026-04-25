from fastapi import FastAPI
import random

app = FastAPI()

kurals = [
    {"id": 1, "text": "அகர முதல எழுத்தெல்லாம்...", "meaning": "All letters begin with A"},
    {"id": 2, "text": "கற்றது கைமண் அளவு...", "meaning": "What we know is a handful"},
]

@app.get("/")
def home():
    return {"message": "Tamil Kural API is running"}

@app.get("/kural/{id}")
def get_kural(id: int):
    for k in kurals:
        if k["id"] == id:
            return k
    return {"error": "Not found"}

@app.get("/random")
def random_kural():
    return random.choice(kurals)