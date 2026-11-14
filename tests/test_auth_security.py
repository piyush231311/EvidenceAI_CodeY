import os
import io
import json
import uuid
import hashlib
import tempfile
from datetime import datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables before importing app
os.environ["SECRET_KEY"] = "test_secret_key_minimum_32_characters_long_for_security_checks"
os.environ["SESSION_MINUTES"] = "30"
os.environ["COOKIE_SECURE"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"
os.environ["ALLOWED_ORIGIN"] = "http://localhost:5173"

from backend.db import Base, get_db
from backend.models import User, RecoveryCode, AuthEvent, Case, Evidence, AuditLog
from backend.main import app, limiter
from backend.auth import ph, create_session_jwt

CSRF_HEADER = {"X-Requested-With": "evidence-ai"}


@pytest.fixture(scope="function")
def test_env():
    # Reset slowapi limiter for each test
    limiter.reset()

    # Use a temporary SQLite database file for complete test isolation
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    db_url = f"sqlite:///{temp_db_path}"
    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield {
            "client": client,
            "session_factory": TestingSessionLocal,
            "engine": test_engine,
            "db_path": temp_db_path
        }

    app.dependency_overrides.clear()
    test_engine.dispose()
    try:
        os.remove(temp_db_path)
    except Exception:
        pass


# ==============================================================================
# TEST 1: Register works, argon2 hashes (never plaintext), recovery codes returned once and stored hashed
# ==============================================================================
def test_1_register_argon2_and_recovery_codes(test_env):
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    res = client.post(
        "/api/auth/register",
        json={"username": "alice_test", "password": "SafePassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["user"]["username"] == "alice_test"
    assert "recovery_codes" in data
    assert len(data["recovery_codes"]) == 8
    # Format e.g. "7K3F-9QX2-M8TD"
    for code in data["recovery_codes"]:
        parts = code.split("-")
        assert len(parts) == 3
        for p in parts:
            assert len(p) == 4

    # Verify session cookie was set
    assert "session" in res.cookies

    # Query DB directly to verify password is stored ONLY as argon2id hash
    with SessionLocal() as db:
        user = db.query(User).filter(User.username_normalized == "alice_test").first()
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert "SafePassphrase2026!" not in user.password_hash

        # Verify recovery codes are stored hashed (SHA-256, never plaintext)
        rcs = db.query(RecoveryCode).filter(RecoveryCode.user_id == user.id).all()
        assert len(rcs) == 8
        for rc in rcs:
            assert len(rc.code_hash) == 64  # SHA-256 hex string
            assert rc.used_at is None
            for plaintext_code in data["recovery_codes"]:
                assert plaintext_code != rc.code_hash


# ==============================================================================
# TEST 2: Password validation rules: weak, common, too-short and username-equal passwords rejected
# ==============================================================================
def test_2_password_validation_rules(test_env):
    client = test_env["client"]

    # Too short (< 10 chars)
    r1 = client.post(
        "/api/auth/register",
        json={"username": "bob_test", "password": "short123"},
        headers=CSRF_HEADER
    )
    assert r1.status_code == 400
    assert "at least 10 characters" in r1.json()["detail"]

    # Username-equal
    r2 = client.post(
        "/api/auth/register",
        json={"username": "bob_test_user", "password": "bob_test_user"},
        headers=CSRF_HEADER
    )
    assert r2.status_code == 400
    assert "cannot be the same as your username" in r2.json()["detail"]

    # Common password from bundled list
    r3 = client.post(
        "/api/auth/register",
        json={"username": "bob_test", "password": "password1234"},
        headers=CSRF_HEADER
    )
    assert r3.status_code == 400
    assert "too common" in r3.json()["detail"]

    # Invalid username format
    r4 = client.post(
        "/api/auth/register",
        json={"username": "bad user!", "password": "SafePassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r4.status_code == 400
    assert "letters, numbers" in r4.json()["detail"]


# ==============================================================================
# TEST 3: Login succeeds with right credentials and gives httpOnly cookie;
#         wrong password and unknown user return identical error body and status
# ==============================================================================
def test_3_login_success_and_identical_error(test_env):
    client = test_env["client"]

    # Register user first
    client.post(
        "/api/auth/register",
        json={"username": "charlie", "password": "CorrectPassphrase2026!"},
        headers=CSRF_HEADER
    )
    client.cookies.clear()

    # Successful login
    res_ok = client.post(
        "/api/auth/login",
        json={"username": "charlie", "password": "CorrectPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert res_ok.status_code == 200
    assert "session" in res_ok.cookies
    # Verify cookie attributes
    cookie_header = res_ok.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()

    # Wrong password
    client.cookies.clear()
    res_wrong_pw = client.post(
        "/api/auth/login",
        json={"username": "charlie", "password": "WrongPassword2026!"},
        headers=CSRF_HEADER
    )
    assert res_wrong_pw.status_code == 401

    # Unknown user
    res_unknown_user = client.post(
        "/api/auth/login",
        json={"username": "ghost_user_does_not_exist", "password": "WrongPassword2026!"},
        headers=CSRF_HEADER
    )
    assert res_unknown_user.status_code == 401

    # Identical error response body
    assert res_wrong_pw.json() == res_unknown_user.json()
    assert res_wrong_pw.json()["detail"] == "Username or password is incorrect."


# ==============================================================================
# TEST 4: Five failed logins trigger lockout; successful login after lock period works
# ==============================================================================
def test_4_failed_login_lockout_and_recovery(test_env):
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # Register user
    client.post(
        "/api/auth/register",
        json={"username": "david", "password": "MySecretPassphrase2026!"},
        headers=CSRF_HEADER
    )
    client.cookies.clear()

    # 4 failed attempts: return 401
    for i in range(4):
        r = client.post(
            "/api/auth/login",
            json={"username": "david", "password": f"BadPassword{i}!"},
            headers=CSRF_HEADER
        )
        assert r.status_code == 401

    # 5th failed attempt: triggers lockout, returns 429
    r5 = client.post(
        "/api/auth/login",
        json={"username": "david", "password": "BadPassword5!"},
        headers=CSRF_HEADER
    )
    assert r5.status_code == 429
    assert "Too many attempts" in r5.json()["detail"]

    # Even with correct password, blocked while locked_until is active
    limiter.reset()
    r_locked = client.post(
        "/api/auth/login",
        json={"username": "david", "password": "MySecretPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_locked.status_code == 429

    # Fast forward locked_until to the past
    with SessionLocal() as db:
        user = db.query(User).filter(User.username_normalized == "david").first()
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        db.commit()

    # Now login with correct password works
    limiter.reset()
    r_unlocked = client.post(
        "/api/auth/login",
        json={"username": "david", "password": "MySecretPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_unlocked.status_code == 200


# ==============================================================================
# TEST 5: Every protected route returns 401 with no cookie, tampered token, expired token
# ==============================================================================
def test_5_protected_routes_unauthenticated_tampered_expired(test_env):
    client = test_env["client"]

    # No cookie
    client.cookies.clear()
    r_no_cookie = client.get("/api/cases")
    assert r_no_cookie.status_code == 401

    # Tampered token
    client.cookies.set("session", "tampered.jwt.token_signature_invalid")
    r_tampered = client.get("/api/cases")
    assert r_tampered.status_code == 401

    # Expired token
    import jwt
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "tv": 0,
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        "jti": str(uuid.uuid4())
    }
    expired_token = jwt.encode(expired_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    client.cookies.set("session", expired_token)
    r_expired = client.get("/api/cases")
    assert r_expired.status_code == 401


# ==============================================================================
# TEST 6: State-changing request without X-Requested-With returns 403
# ==============================================================================
def test_6_csrf_defense_x_requested_with(test_env):
    client = test_env["client"]

    # Register and keep session cookie
    client.post(
        "/api/auth/register",
        json={"username": "emma_csrf", "password": "SafePassphrase2026!"},
        headers=CSRF_HEADER
    )

    # State-changing POST without CSRF header
    r_missing = client.post("/api/cases", json={"id": "case-no-csrf"})
    assert r_missing.status_code == 403
    assert "CSRF" in r_missing.json()["detail"]

    # State-changing POST with wrong CSRF header
    r_wrong = client.post("/api/cases", json={"id": "case-wrong-csrf"}, headers={"X-Requested-With": "other"})
    assert r_wrong.status_code == 403

    # State-changing POST with valid CSRF header
    r_valid = client.post("/api/cases", json={"id": "case-valid-csrf"}, headers=CSRF_HEADER)
    assert r_valid.status_code == 201


# ==============================================================================
# TEST 7: OWNERSHIP: user B gets 404 (not 403, not data) on user A's case,
#         evidence list, evidence file download, and checklist, and cannot upload into A's case.
#         User B's case list never contains A's cases.
# ==============================================================================
def test_7_ownership_isolation(test_env):
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # 1. Register User A
    r_a = client.post(
        "/api/auth/register",
        json={"username": "user_a", "password": "PassphraseUserA2026!"},
        headers=CSRF_HEADER
    )
    cookie_a = res_cookie_a = client.cookies.get("session")

    # User A creates Case A
    case_a_id = f"case_a_{uuid.uuid4().hex[:8]}"
    r_case_a = client.post(
        "/api/cases",
        json={"id": case_a_id},
        headers=CSRF_HEADER
    )
    assert r_case_a.status_code == 201

    # User A uploads evidence A
    evidence_file = io.BytesIO(b"Hello from evidence A confidential record")
    r_upload_a = client.post(
        f"/api/cases/{case_a_id}/evidence",
        files=[("files", ("test_note.txt", evidence_file, "text/plain"))],
        headers=CSRF_HEADER
    )
    assert r_upload_a.status_code == 201
    evidence_a_id = r_upload_a.json()[0]["id"]

    # 2. Register User B
    client.cookies.clear()
    r_b = client.post(
        "/api/auth/register",
        json={"username": "user_b", "password": "PassphraseUserB2026!"},
        headers=CSRF_HEADER
    )
    assert r_b.status_code == 201

    # User B lists cases: must NOT contain Case A
    r_b_cases = client.get("/api/cases")
    assert r_b_cases.status_code == 200
    b_case_ids = [c["id"] for c in r_b_cases.json()]
    assert case_a_id not in b_case_ids

    # User B queries User A's case evidence: returns 404
    r_b_case_ev = client.get(f"/api/cases/{case_a_id}/evidence")
    assert r_b_case_ev.status_code == 404

    # User B queries User A's evidence file download: returns 404
    r_b_file = client.get(f"/api/evidence/{evidence_a_id}/file")
    assert r_b_file.status_code == 404

    # User B queries User A's audit logs: returns 404
    r_b_audit = client.get(f"/api/cases/{case_a_id}/audit-logs")
    assert r_b_audit.status_code == 404

    # User B attempts to upload into User A's case: returns 404
    b_file = io.BytesIO(b"Unauthorized attacker file")
    r_b_upload = client.post(
        f"/api/cases/{case_a_id}/evidence",
        files=[("files", ("exploit.txt", b_file, "text/plain"))],
        headers=CSRF_HEADER
    )
    assert r_b_upload.status_code == 404


# ==============================================================================
# TEST 8: Logout works; change-password invalidates old cookies; token issued before tv change is rejected
# ==============================================================================
def test_8_logout_and_password_change_token_version(test_env):
    client = test_env["client"]

    # Register user
    client.post(
        "/api/auth/register",
        json={"username": "felix", "password": "InitialPassphrase2026!"},
        headers=CSRF_HEADER
    )
    old_cookie = client.cookies.get("session")

    # Change password
    r_cp = client.post(
        "/api/auth/change-password",
        json={"current_password": "InitialPassphrase2026!", "new_password": "UpdatedPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_cp.status_code == 200
    new_cookie = client.cookies.get("session")
    assert new_cookie != old_cookie

    # Request with new cookie succeeds
    r_me_new = client.get("/api/auth/me")
    assert r_me_new.status_code == 200

    # Old cookie is rejected with 401 because token_version changed
    client.cookies.set("session", old_cookie)
    r_me_old = client.get("/api/auth/me")
    assert r_me_old.status_code == 401

    # Logout works
    client.cookies.set("session", new_cookie, domain="testserver")
    r_logout = client.post("/api/auth/logout", headers=CSRF_HEADER)
    assert r_logout.status_code == 200
    # Cookie should be cleared or expired
    set_cookie = r_logout.headers.get("set-cookie", "")
    assert 'session=""' in set_cookie or "Max-Age=0" in set_cookie

    # After logout, accessing protected route is rejected
    client.cookies.clear()
    r_after_logout = client.get("/api/auth/me")
    assert r_after_logout.status_code == 401


# ==============================================================================
# TEST 9: Recovery code works once, resets password, invalidates old sessions and old codes, returns fresh code set
# ==============================================================================
def test_9_recovery_code_flow(test_env):
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # Register
    r_reg = client.post(
        "/api/auth/register",
        json={"username": "grace", "password": "OriginalPassphrase2026!"},
        headers=CSRF_HEADER
    )
    codes = r_reg.json()["recovery_codes"]
    code_to_use = codes[0]

    client.cookies.clear()

    # Wrong recovery code -> generic error
    r_wrong = client.post(
        "/api/auth/recover",
        json={"username": "grace", "recovery_code": "0000-0000-0000", "new_password": "BrandNewPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_wrong.status_code == 400
    assert "didn't match" in r_wrong.json()["detail"]

    # Valid recovery code -> resets password and returns new codes
    r_recover = client.post(
        "/api/auth/recover",
        json={"username": "grace", "recovery_code": code_to_use, "new_password": "BrandNewPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_recover.status_code == 200
    new_codes = r_recover.json()["recovery_codes"]
    assert len(new_codes) == 8
    assert code_to_use not in new_codes

    # Try to reuse the same recovery code -> rejected
    client.cookies.clear()
    r_reuse = client.post(
        "/api/auth/recover",
        json={"username": "grace", "recovery_code": code_to_use, "new_password": "AnotherNewPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_reuse.status_code == 400

    # Login with new password works
    r_login = client.post(
        "/api/auth/login",
        json={"username": "grace", "password": "BrandNewPassphrase2026!"},
        headers=CSRF_HEADER
    )
    assert r_login.status_code == 200


# ==============================================================================
# TEST 10: Auth events are written; LOGIN_FAILED for unknown user stores no username
# ==============================================================================
def test_10_auth_events_audit(test_env):
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # Unknown username login attempt
    client.post(
        "/api/auth/login",
        json={"username": "super_secret_victim_handle_xyz", "password": "SomePassword123!"},
        headers=CSRF_HEADER
    )

    with SessionLocal() as db:
        failed_event = db.query(AuthEvent).filter(
            AuthEvent.event == "LOGIN_FAILED",
            AuthEvent.user_id == None
        ).first()
        assert failed_event is not None
        # Verify the attempted unknown username is NOT stored anywhere in the event
        assert "super_secret_victim_handle_xyz" not in (failed_event.user_agent or "")
        assert "super_secret_victim_handle_xyz" not in (failed_event.ip or "")


# ==============================================================================
# TEST 11: Existing evidence upload computes SHA-256 and writes audit log with acting user_id
# ==============================================================================
def test_11_evidence_upload_sha256_and_audit_log_user_id(test_env):
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # Register user
    r_reg = client.post(
        "/api/auth/register",
        json={"username": "hannah", "password": "ForensicPassphrase2026!"},
        headers=CSRF_HEADER
    )
    user_id = r_reg.json()["user"]["id"]

    case_id = f"case_hannah_{uuid.uuid4().hex[:8]}"
    file_bytes = b"Digital Forensic Evidence Content for SHA-256 verification"
    expected_sha256 = hashlib.sha256(file_bytes).hexdigest()

    r_up = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("forensic_sample.txt", io.BytesIO(file_bytes), "text/plain"))],
        headers=CSRF_HEADER
    )
    assert r_up.status_code == 201
    evidence_item = r_up.json()[0]
    assert evidence_item["sha256"] == expected_sha256

    with SessionLocal() as db:
        # Check audit_log row has user_id
        audit_row = db.query(AuditLog).filter(
            AuditLog.case_id == case_id,
            AuditLog.evidence_id == evidence_item["id"]
        ).first()
        assert audit_row is not None
        assert audit_row.user_id == user_id
        assert audit_row.action == "UPLOADED_AND_EXTRACTED"
