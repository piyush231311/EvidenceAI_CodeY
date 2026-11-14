import sys
from pathlib import Path
from sqlalchemy import text
from backend.db import engine, Base
from backend.models import User, RecoveryCode, AuthEvent, Case, AuditLog

def run_auth_migration():
    """
    Idempotent database migration:
    - Creates users, recovery_codes, auth_events tables
    - Adds user_id to cases (nullable in DB, with index)
    - Backfills existing cases to the first registered user if present
    - Adds user_id to audit_log (with index)
    """
    print("[Migration] Starting auth schema migration...")
    # 1. Ensure all defined tables are created
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        # 2. Check and migrate cases.user_id
        res_cases = conn.execute(text("PRAGMA table_info(cases)"))
        cases_cols = [row[1] for row in res_cases.fetchall()]
        if "user_id" not in cases_cols:
            print("[Migration] Adding column 'user_id' to 'cases' table...")
            conn.execute(text("ALTER TABLE cases ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)"))
            conn.commit()

        # Add index on cases.user_id
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cases_user_id ON cases(user_id)"))
        conn.commit()

        # Check for backfill
        res_first_user = conn.execute(text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")).fetchone()
        res_unassigned = conn.execute(text("SELECT COUNT(*) FROM cases WHERE user_id IS NULL")).scalar()

        if res_first_user and res_unassigned > 0:
            first_user_id = res_first_user[0]
            print(f"[Migration] Backfilling {res_unassigned} unassigned case(s) to first user {first_user_id}...")
            conn.execute(
                text("UPDATE cases SET user_id = :uid WHERE user_id IS NULL"),
                {"uid": first_user_id}
            )
            conn.commit()
        elif res_unassigned > 0:
            print(f"[Migration] Notice: {res_unassigned} case(s) currently have user_id NULL (no users created yet).")
        else:
            print("[Migration] All cases are properly assigned to users.")

        # 3. Check and migrate audit_log.user_id
        res_audit = conn.execute(text("PRAGMA table_info(audit_log)"))
        audit_cols = [row[1] for row in res_audit.fetchall()]
        if "user_id" not in audit_cols:
            print("[Migration] Adding column 'user_id' to 'audit_log' table...")
            conn.execute(text("ALTER TABLE audit_log ADD COLUMN user_id VARCHAR(36)"))
            conn.commit()

        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log(user_id)"))
        conn.commit()

    print("[Migration] Auth schema migration completed successfully.")

if __name__ == "__main__":
    run_auth_migration()
