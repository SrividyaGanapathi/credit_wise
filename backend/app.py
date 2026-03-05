from fastapi import FastAPI
from pydantic import BaseModel

from api.auth import router as auth_router
from data.init_db import init_db

app = FastAPI()

class Transaction(BaseModel):
    amount: float
    category: str
    country: str = "United States of America"
    channel: str = "Online"

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth_router)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/recommend")
def recommend(txn: Transaction):
    if txn.category.lower() == "dining":
        return {"best_card": "card 1",
                "reason": "3x cashback on dining"}
    elif txn.category.lower() == "travel":
        return {"best_card": "card 2",
                "reason": "5x cashback on travel"}
    else:
        return {"best_card": "card 3",
                "reason": "2x cashback on all other purchases"}
    