from fastapi import APIRouter, Depends

from auth.firebase_auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "firebase_uid": current_user.firebase_uid,
    }
