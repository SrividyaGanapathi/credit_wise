from fastapi import FastAPI

from api.auth import router as auth_router
from api.recommendations import router as recommend_router
from api.usage import router as usage_router
from api.users import router as users_router
from config import settings
from data.init_db import init_db

app = FastAPI()


@app.on_event("startup")
def on_startup():
    if settings.auto_init_db:
        init_db()

app.include_router(auth_router)
app.include_router(recommend_router)
app.include_router(usage_router)
app.include_router(users_router)

@app.get("/health")
def health():
    return {"ok": True}
