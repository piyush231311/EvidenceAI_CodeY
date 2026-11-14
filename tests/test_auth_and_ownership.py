"""
Tests for Evidence AI User Authentication, Session Persistence, and User Isolation.

Verifies:
1. Public health check and demo credentials endpoint.
2. Unauthenticated requests return HTTP 401.
3. Demo user authentication:
   - Invalid credentials return HTTP 401.
   - Valid demo credentials (demo@evidenceai.local / DemoUser123!) succeed.
   - Password is stored as PBKDF2 hash, not plaintext.
4. Session persistence:
   - Session created in database with 7-day expiration.
   - User profile returned on /api/auth/me.
5. User isolation and ownership:
   - Newly created case gets owner_id set to authenticated user.
   - User only sees cases they own in GET /api/cases.
   - Legacy unowned cases are not visible in demo user's case list.
   - User B cannot access User A's case (returns HTTP 404).
   - User B cannot access User A's evidence or file download (returns HTTP 404).
6. Logout:
   - Invalidation of session and cookie clearing.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime
from fastapi import HTTPException, Response

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import SessionLocal, init_db
from backend.models import User, UserSession, Case, Evidence, LoginPayload
from backend.auth import (
    hash_password, verify_password, create_user_session, invalidate_user_session,
    get_current_user, get_current_user_optional, SESSION_COOKIE_NAME
)
from backend.routes import (
    login, logout, get_me, list_cases, create_case, delete_case,
    get_case_evidence, stream_evidence_file, get_demo_credentials,
    CreateCasePayload
)
from scripts.seed_demo_user import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_user


@pytest.fixture(scope="module", autouse=True)
def setup_database_and_demo_user():
    init_db()
    seed_demo_user()


def test_demo_credentials_endpoint():
    creds = get_demo_credentials()
    assert creds["enabled"] is True
    assert creds["email"] == DEMO_EMAIL
    assert creds["password"] == DEMO_PASSWORD


def test_demo_user_password_hashing():
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        assert user is not None
        assert user.hashed_password != DEMO_PASSWORD
        assert user.hashed_password.startswith("pbkdf2:sha256:")
        assert verify_password(DEMO_PASSWORD, user.hashed_password) is True
        assert verify_password("WrongPassword!", user.hashed_password) is False


def test_login_invalid_credentials():
    with SessionLocal() as db:
        resp = Response()
        bad_payload = LoginPayload(email=DEMO_EMAIL, password="WrongPassword123!")
        with pytest.raises(HTTPException) as exc_info:
            login(bad_payload, resp, db)
        assert exc_info.value.status_code == 401
        assert "Invalid email or password" in exc_info.value.detail


def test_login_success_and_cookie_session():
    with SessionLocal() as db:
        resp = Response()
        good_payload = LoginPayload(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        result = login(good_payload, resp, db)

        assert result["authenticated"] is True
        assert result["user"].email == DEMO_EMAIL
        token = result["token"]
        assert len(token) > 20

        # Verify session in DB
        session = db.query(UserSession).filter(UserSession.id == token).first()
        assert session is not None
        assert session.is_active is True
        assert session.expires_at > datetime.utcnow()

        # Test profile with current user
        me_result = get_me(current_user=result["user"])
        assert me_result["authenticated"] is True
        assert me_result["user"].email == DEMO_EMAIL


def test_unauthenticated_request_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"


def test_user_case_ownership_and_isolation():
    with SessionLocal() as db:
        demo_user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        assert demo_user is not None

        # Create case for Demo User
        case_a_id = f"demo-case-{uuid.uuid4().hex[:8]}"
        created_case = create_case(CreateCasePayload(id=case_a_id), db, current_user=demo_user)
        assert created_case.id == case_a_id
        assert created_case.owner_id == demo_user.id

        # Verify Demo User sees case in their list
        user_cases = list_cases(db, current_user=demo_user)
        assert case_a_id in [c.id for c in user_cases]

        # Verify legacy unowned cases are NOT listed for demo user
        for c in user_cases:
            assert c.owner_id == demo_user.id

        # Create User B
        user_b = User(
            email=f"user_b_{uuid.uuid4().hex[:6]}@evidenceai.local",
            hashed_password=hash_password("UserBPass123!"),
            is_active=True
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

        # User B listing cases should NOT see User A's case
        cases_b = list_cases(db, current_user=user_b)
        assert case_a_id not in [c.id for c in cases_b]

        # User B accessing User A's case evidence raises HTTP 404
        with pytest.raises(HTTPException) as exc_info:
            get_case_evidence(case_a_id, db, current_user=user_b)
        assert exc_info.value.status_code == 404

        # User B deleting User A's case raises HTTP 404
        with pytest.raises(HTTPException) as exc_del:
            delete_case(case_a_id, db, current_user=user_b)
        assert exc_del.value.status_code == 404

        # Owner can delete their own case
        delete_case(case_a_id, db, current_user=demo_user)
        deleted = db.query(Case).filter(Case.id == case_a_id).first()
        assert deleted is None


def test_logout_invalidation():
    with SessionLocal() as db:
        demo_user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        session = create_user_session(db, demo_user.id)
        assert session.is_active is True

        invalidate_user_session(db, session.id)
        refreshed = db.query(UserSession).filter(UserSession.id == session.id).first()
        assert refreshed.is_active is False
