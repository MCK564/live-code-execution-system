from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from dependencies.auth import get_current_access_claims
from schemas.user import UserResponse
from services.redis_service import get_user_cache, set_user_cache
from services.user import get_user_by_id, list_users, list_users_by_score, serialize_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    claims: dict = Depends(get_current_access_claims),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token subject is invalid.",
        ) from exc

    cached_user = await get_user_cache(user_id)
    if cached_user:
        if cached_user.get("disabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled.",
            )
        return cached_user

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    serialized_user = serialize_user(user)
    await set_user_cache(serialized_user)
    return serialized_user


@router.get("/me/sessions")
async def get_current_user_sessions():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User sessions are not implemented yet.",
    )


@router.get("/score-ranking", response_model=list[UserResponse])
async def get_ranking_users(db: Session = Depends(get_db)):
    return [serialize_user(user) for user in list_users_by_score(db)]


@router.get("/", response_model=list[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    return [serialize_user(user) for user in list_users(db)]
