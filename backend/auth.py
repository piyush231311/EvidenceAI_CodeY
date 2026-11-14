import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, UserSession

SESSION_COOKIE_NAME = "evidence_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 days
PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Secure password hashing using standard library PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        algorithm_spec, salt_hex, key_hex = parts
        _, hash_name, iterations_str = algorithm_spec.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        dk = hashlib.pbkdf2_hmac(hash_name, plain_password.encode("utf-8"), salt, int(iterations_str))
        return secrets.compare_digest(dk, expected_key)
    except Exception:
        return False


def create_user_session(db: Session, user_id: str) -> UserSession:
    """Creates a new active session for the given user."""
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    session = UserSession(
        id=token,
        user_id=user_id,
        created_at=now,
        expires_at=expires_at,
        is_active=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def invalidate_user_session(db: Session, token: str) -> None:
    """Deactivates a user session."""
    session = db.query(UserSession).filter(UserSession.id == token).first()
    if session:
        session.is_active = False
        db.commit()


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extracts session token from HTTP-only cookie or Authorization header.
    Returns the User if valid and active, or None.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        return None

    now = datetime.utcnow()
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == token,
            UserSession.is_active == True,
            UserSession.expires_at > now
        )
        .first()
    )
    if not session:
        return None

    user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
    return user


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Dependency that raises HTTP 401 if request is not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
