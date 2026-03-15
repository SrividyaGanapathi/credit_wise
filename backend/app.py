from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.recommendations import router as recommend_router
from api.usage import router as usage_router
from api.users import router as users_router
from config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(recommend_router)
app.include_router(usage_router)
app.include_router(users_router)

@app.get("/health")
def health():
    return {"ok": True}
