from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from data.session import get_db
from models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if not user:
        user = User(email=payload.email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"message": f"Logged in as {user.id} - {user.email}"}

