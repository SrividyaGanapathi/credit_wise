from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Transaction(BaseModel):
    amount: float
    category: str
    country: str = "United States of America"
    channel: str = "Online"

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
    