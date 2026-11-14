"""
Evidence AI - Seed Demo User Script

Creates or updates the development-only demo account:
  Email: demo@evidenceai.local
  Password: DemoUser123!

Usage:
  python scripts/seed_demo_user.py [--assign-demo-cases]
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import SessionLocal, init_db
from backend.models import User, Case
from backend.auth import hash_password

DEMO_EMAIL = "demo@evidenceai.local"
DEMO_PASSWORD = "DemoUser123!"


def seed_demo_user(assign_demo_cases: bool = False):
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        print("[ERROR] Cannot seed demo user in PRODUCTION environment. Aborting.")
        sys.exit(1)

    init_db()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        hashed = hash_password(DEMO_PASSWORD)

        if not user:
            user = User(
                email=DEMO_EMAIL,
                hashed_password=hashed,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[SUCCESS] Created demo user: {DEMO_EMAIL} (ID: {user.id})")
        else:
            user.hashed_password = hashed
            user.is_active = True
            db.commit()
            print(f"[SUCCESS] Updated demo user: {DEMO_EMAIL} (ID: {user.id})")

        if assign_demo_cases:
            unowned_cases = db.query(Case).filter(Case.owner_id.is_(None)).all()
            for c in unowned_cases:
                c.owner_id = user.id
            db.commit()
            print(f"[INFO] Assigned {len(unowned_cases)} unowned cases to demo user.")
        else:
            print("[INFO] Existing legacy cases remain unassigned (legacy isolation enforced).")

    print("[DONE] Demo user seed complete.")
    print(f"       Email:    {DEMO_EMAIL}")
    print(f"       Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Evidence AI demo user.")
    parser.add_argument(
        "--assign-demo-cases",
        action="store_true",
        help="Assign existing unowned legacy cases to the demo user."
    )
    args = parser.parse_args()
    seed_demo_user(assign_demo_cases=args.assign_demo_cases)
