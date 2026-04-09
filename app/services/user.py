from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.user import User


def _normalize_name(user_info: dict[str, Any], email: str) -> str:
    display_name = (user_info.get("name") or email).strip()
    return display_name[:255] or email


def serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "total_score": user.total_score or 0,
        "disabled": bool(user.disabled),
    }


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


def list_users_by_score(db: Session) -> list[User]:
    return db.query(User).order_by(User.total_score.desc(), User.id.asc()).all()


def get_or_create_google_user(db: Session, user_info: dict[str, Any]) -> User:
    email = user_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google user info is missing the email field.",
        )

    email = str(email).strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google user email is empty.",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email[:255],
            full_name=_normalize_name(user_info, email),
            avatar_url=(user_info.get("picture") or None),
        )
        db.add(user)
    else:
        user.full_name = _normalize_name(user_info, email)
        user.avatar_url = user_info.get("picture") or user.avatar_url

    db.commit()
    db.refresh(user)

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    return user
