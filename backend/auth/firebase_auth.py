from dataclasses import dataclass
from typing import Any, Optional

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from sqlalchemy.orm import Session

from config import settings
from data.session import get_db
from models.users import User


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    email: str
    firebase_uid: str
    is_anonymous: bool


def _get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        options: dict[str, Any] = {}
        if settings.firebase_project_id:
            options["projectId"] = settings.firebase_project_id
        return firebase_admin.initialize_app(options=options or None)


def verify_id_token(id_token: str) -> dict[str, Any]:
    _get_firebase_app()
    try:
        return firebase_auth.verify_id_token(id_token)
    except Exception as exc:  # pragma: no cover - Firebase SDK errors vary by type
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token",
        ) from exc


def _derive_email_from_claims(claims: dict[str, Any]) -> str:
    email = claims.get("email")
    if email:
        return email

    firebase_uid = claims["uid"]
    return f"firebase-anon-{firebase_uid}@cardwise.local"


def _is_anonymous_claims(claims: dict[str, Any]) -> bool:
    firebase_claims = claims.get("firebase", {})
    return firebase_claims.get("sign_in_provider") == "anonymous" or "email" not in claims


def _sync_user_from_claims(claims: dict[str, Any], db: Session) -> AuthenticatedUser:
    firebase_uid = claims["uid"]
    email = _derive_email_from_claims(claims)
    is_anonymous = _is_anonymous_claims(claims)

    user = db.query(User).filter(User.firebase_uid == firebase_uid).one_or_none()
    if user is None:
        user = db.query(User).filter(User.email == email).one_or_none()

    if user is None:
        user = User(email=email, firebase_uid=firebase_uid)
        db.add(user)
    else:
        user.email = email
        user.firebase_uid = firebase_uid

    db.commit()
    db.refresh(user)
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        firebase_uid=firebase_uid,
        is_anonymous=is_anonymous,
    )


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthenticatedUser]:
    if credentials is None:
        return None

    claims = verify_id_token(credentials.credentials)
    return _sync_user_from_claims(claims, db)


def get_current_user(
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
) -> AuthenticatedUser:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    return current_user
