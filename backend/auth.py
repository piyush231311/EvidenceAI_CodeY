import re
import secrets
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt

from fastapi import APIRouter, Request, Response, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import SECRET_KEY, SESSION_MINUTES, COOKIE_SECURE, COOKIE_SAMESITE
from backend.models import (
    User,
    RecoveryCode,
    AuthEvent,
    Case,
    UserRegisterRequest,
    UserLoginRequest,
    ChangePasswordRequest,
    RecoverAccountRequest,
    RegenerateRecoveryCodesRequest,
    AuthResponse,
    UserResponse
)
from backend.common_passwords import COMMON_PASSWORDS
from backend.db import get_db

# Password hasher with argon2id library defaults
ph = PasswordHasher()
# Precomputed dummy hash for constant-time mitigation when username does not exist
DUMMY_HASH = ph.hash("dummy_mitigation_passphrase_for_constant_time_checks_xyz")

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Auth router under /api/auth
auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
RECOVERY_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # 32 characters (5 bits/char)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_username(username: str) -> str:
    cleaned = username.strip()
    if not USERNAME_REGEX.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3-32 characters and can only contain letters, numbers, underscores, dots, and hyphens."
        )
    return cleaned


def validate_password(password: str, username: str) -> str:
    if len(password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 10 characters long."
        )
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 128 characters."
        )
    if password.strip().lower() == username.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be the same as your username."
        )
    if password.strip().lower() in COMMON_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password is too common. Please choose a more unique passphrase."
        )
    return password


def generate_single_recovery_code() -> str:
    p1 = "".join(secrets.choice(RECOVERY_CHARSET) for _ in range(4))
    p2 = "".join(secrets.choice(RECOVERY_CHARSET) for _ in range(4))
    p3 = "".join(secrets.choice(RECOVERY_CHARSET) for _ in range(4))
    return f"{p1}-{p2}-{p3}"


def hash_recovery_code(code: str) -> str:
    normalized = code.strip().upper().replace(" ", "").replace("-", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_recovery_codes_batch() -> List[str]:
    return [generate_single_recovery_code() for _ in range(8)]


def create_session_jwt(user_id: str, token_version: int) -> Tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=SESSION_MINUTES)
    payload = {
        "sub": user_id,
        "tv": token_version,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4())
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, exp


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=SESSION_MINUTES * 60
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key="session",
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )


def log_auth_event(db: Session, event: str, user_id: Optional[str], request: Request):
    client_ip = "unknown"
    if request.client:
        client_ip = request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    ua = request.headers.get("user-agent", "")[:200]

    entry = AuthEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event=event,
        ip=client_ip,
        user_agent=ua,
        created_at=utc_now()
    )
    db.add(entry)
    db.commit()


def get_current_user(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token."
        )

    user_id = payload.get("sub")
    token_version = payload.get("tv")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidated. Please sign in again."
        )

    # Sliding renewal: if token has less than half its lifetime left, reissue fresh cookie
    iat = payload.get("iat")
    exp = payload.get("exp")
    if iat and exp:
        total_lifetime = exp - iat
        now_ts = int(datetime.now(timezone.utc).timestamp())
        remaining = exp - now_ts
        if remaining < (total_lifetime / 2):
            new_token, _ = create_session_jwt(user.id, user.token_version)
            set_session_cookie(response, new_token)

    return user


def get_owned_case_or_404(case_id: str, user: User, db: Session) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return case


# ==============================================================================
# AUTH ENDPOINTS
# ==============================================================================

@auth_router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    username = validate_username(req.username)
    username_norm = username.lower()
    validate_password(req.password, username)

    existing = db.query(User).filter(User.username_normalized == username_norm).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken."
        )

    pwd_hash = ph.hash(req.password)
    user_id = str(uuid.uuid4())
    now = utc_now()
    user = User(
        id=user_id,
        username=username,
        username_normalized=username_norm,
        password_hash=pwd_hash,
        token_version=0,
        failed_attempts=0,
        created_at=now
    )
    db.add(user)

    # Generate 8 recovery codes
    codes = generate_recovery_codes_batch()
    for code in codes:
        rc = RecoveryCode(
            id=str(uuid.uuid4()),
            user_id=user_id,
            code_hash=hash_recovery_code(code),
            created_at=now
        )
        db.add(rc)

    db.commit()
    db.refresh(user)

    # Issue session cookie
    token, _ = create_session_jwt(user.id, user.token_version)
    set_session_cookie(response, token)

    log_auth_event(db, "REGISTERED", user.id, request)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        recovery_codes=codes
    )


@auth_router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(req: UserLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    username_norm = req.username.strip().lower()
    user = db.query(User).filter(User.username_normalized == username_norm).first()

    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Username or password is incorrect."
    )

    if not user:
        # Constant-time mitigation: run dummy verify so response timing is indistinguishable
        try:
            ph.verify(DUMMY_HASH, req.password)
        except Exception:
            pass
        # For unknown user, do NOT store attempted username
        log_auth_event(db, "LOGIN_FAILED", None, request)
        raise generic_error

    # Check account lockout
    now = utc_now()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again in a few minutes."
        )

    # Verify password
    try:
        ph.verify(user.password_hash, req.password)
        is_valid = True
    except VerifyMismatchError:
        is_valid = False
    except Exception:
        is_valid = False

    if not is_valid:
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=5)
        db.commit()

        log_auth_event(db, "LOGIN_FAILED", user.id, request)

        if user.failed_attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Try again in a few minutes."
            )
        raise generic_error

    # Reset failed attempts on success
    user.failed_attempts = 0
    user.locked_until = None

    # Check if argon2 parameters need updating
    if ph.check_needs_rehash(user.password_hash):
        user.password_hash = ph.hash(req.password)

    user.last_login_at = now
    db.commit()

    token, _ = create_session_jwt(user.id, user.token_version)
    set_session_cookie(response, token)

    log_auth_event(db, "LOGIN_SUCCESS", user.id, request)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        recovery_codes=None
    )


@auth_router.post("/logout")
def logout(
    request: Request,
    response: Response,
    all_devices: bool = Query(False),
    db: Session = Depends(get_db)
):
    user_id: Optional[str] = None
    token = request.cookies.get("session")
    if token:
        try:
            # Decode without verifying expiration so logout works even if expired
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
            user_id = payload.get("sub")
            if all_devices and user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.token_version += 1
                    db.commit()
        except Exception:
            pass

    clear_session_cookie(response)
    log_auth_event(db, "LOGOUT", user_id, request)

    return {"detail": "Logged out successfully."}


@auth_router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@auth_router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ph.verify(user.password_hash, req.current_password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    validate_password(req.new_password, user.username)

    user.password_hash = ph.hash(req.new_password)
    user.token_version += 1
    db.commit()

    # Re-issue session cookie for this current session
    new_token, _ = create_session_jwt(user.id, user.token_version)
    set_session_cookie(response, new_token)

    log_auth_event(db, "PASSWORD_CHANGED", user.id, request)

    return {"detail": "Password changed successfully."}


@auth_router.post("/recover", response_model=AuthResponse)
@limiter.limit("5/minute")
def recover(
    req: RecoverAccountRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    generic_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Those details didn't match."
    )

    username_norm = req.username.strip().lower()
    user = db.query(User).filter(User.username_normalized == username_norm).first()

    if not user:
        try:
            ph.verify(DUMMY_HASH, req.new_password)
        except Exception:
            pass
        log_auth_event(db, "LOGIN_FAILED", None, request)
        raise generic_error

    # Validate recovery code
    code_hash = hash_recovery_code(req.recovery_code)
    rc = db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.code_hash == code_hash,
        RecoveryCode.used_at == None
    ).first()

    if not rc:
        log_auth_event(db, "LOGIN_FAILED", user.id, request)
        raise generic_error

    validate_password(req.new_password, user.username)

    # Mark this code used and invalidate all old unused codes
    now = utc_now()
    rc.used_at = now
    db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.used_at == None
    ).update({"used_at": now})

    # Update password and invalidate all sessions
    user.password_hash = ph.hash(req.new_password)
    user.failed_attempts = 0
    user.locked_until = None
    user.token_version += 1

    # Issue 8 new recovery codes
    new_codes = generate_recovery_codes_batch()
    for code in new_codes:
        new_rc = RecoveryCode(
            id=str(uuid.uuid4()),
            user_id=user.id,
            code_hash=hash_recovery_code(code),
            created_at=now
        )
        db.add(new_rc)

    db.commit()

    token, _ = create_session_jwt(user.id, user.token_version)
    set_session_cookie(response, token)

    log_auth_event(db, "RECOVERY_USED", user.id, request)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        recovery_codes=new_codes
    )


@auth_router.post("/recovery-codes/regenerate")
def regenerate_recovery_codes(
    req: RegenerateRecoveryCodesRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ph.verify(user.password_hash, req.current_password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    # Invalidate all existing codes
    now = utc_now()
    db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.used_at == None
    ).update({"used_at": now})

    # Generate 8 new recovery codes
    new_codes = generate_recovery_codes_batch()
    for code in new_codes:
        new_rc = RecoveryCode(
            id=str(uuid.uuid4()),
            user_id=user.id,
            code_hash=hash_recovery_code(code),
            created_at=now
        )
        db.add(new_rc)

    db.commit()

    log_auth_event(db, "RECOVERY_CODES_REGENERATED", user.id, request)

    return {"recovery_codes": new_codes}
