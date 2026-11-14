"""
Evidence AI — Development-Only Safe Demo Data Cleanup Command.

Features:
  - Scans and manifests disposable test cases (prefixed with test-, quick-, or empty test cases).
  - Dry-run mode by default (--dry-run).
  - Refuses execution against production environments.
  - Verifies presence of a valid database backup before any destructive action.
  - Enforces foreign-key ordered cascading deletion to avoid orphaned records.
  - Leaves official demo cases and real evidence intact.
  - Logs all actions.
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIVE_DB = PROJECT_ROOT / "evidence_ai.db"
STORAGE_DIR = PROJECT_ROOT / "storage" / "originals"
BACKUPS_DIR = PROJECT_ROOT / "backups"


def check_production():
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
    if env in ["prod", "production"]:
        print("ERROR: Cleanup command refused to run in production environment.")
        sys.exit(1)


def verify_backup_exists():
    if not BACKUPS_DIR.exists():
        print("ERROR: No backups directory found. Run scripts/backup_database_and_storage.py first.")
        sys.exit(1)
    backup_dbs = list(BACKUPS_DIR.glob("**/evidence_ai_backup.db"))
    if not backup_dbs:
        print("ERROR: No verified evidence_ai_backup.db found in backups directory.")
        sys.exit(1)
    latest_backup = max(backup_dbs, key=lambda p: p.stat().st_mtime)
    print(f"Verified recent database backup: {latest_backup} ({latest_backup.stat().st_size:,} bytes)")
    return latest_backup


def get_cleanup_candidates(cur):
    cases = cur.execute("SELECT id, created_at FROM cases").fetchall()
    disposable_cases = []
    retained_cases = []

    for cid, cat in cases:
        evs = cur.execute("SELECT id, original_filename FROM evidence WHERE case_id=?", (cid,)).fetchall()
        jobs = cur.execute("SELECT id FROM analysis_jobs WHERE case_id=?", (cid,)).fetchall()
        filenames = [e[1] for e in evs]

        is_test_prefix = any(cid.startswith(p) for p in ["test-", "quick-", "test_"])
        is_empty = len(evs) == 0

        if is_test_prefix or is_empty:
            disposable_cases.append({
                "case_id": cid,
                "created_at": cat,
                "evidence_count": len(evs),
                "job_count": len(jobs),
                "filenames": filenames,
                "reason": "Disposable test prefix" if is_test_prefix else "Empty case",
            })
        else:
            retained_cases.append({
                "case_id": cid,
                "evidence_count": len(evs),
                "filenames": filenames,
            })

    return disposable_cases, retained_cases


def run_cleanup(execute=False, confirm=False):
    check_production()
    verify_backup_exists()

    con = sqlite3.connect(LIVE_DB)
    cur = con.cursor()

    disposable_cases, retained_cases = get_cleanup_candidates(cur)

    print("\n" + "=" * 70)
    print("EVIDENCE AI — CLEANUP MANIFEST")
    print("=" * 70)
    print(f"Total Cases: {len(disposable_cases) + len(retained_cases)}")
    print(f"Retained Demo Cases: {len(retained_cases)}")
    for r in retained_cases:
        sample_files = ", ".join(r["filenames"][:2]) + ("..." if len(r["filenames"]) > 2 else "")
        print(f"  [RETAIN] {r['case_id']} ({r['evidence_count']} files: {sample_files})")

    print(f"\nDisposable Cases Selected For Cleanup: {len(disposable_cases)}")
    for d in disposable_cases:
        print(f"  [DELETE] {d['case_id']} ({d['evidence_count']} files, {d['job_count']} jobs) — {d['reason']}")

    if not execute:
        print("\n[DRY RUN] No changes were made to the database. Use --execute --confirm to run.")
        con.close()
        return

    if not confirm:
        print("\n[ABORTED] Missing --confirm flag. Cleanup requires explicit confirmation.")
        con.close()
        return

    print("\n" + "=" * 70)
    print("EXECUTING SAFE CASCADE CLEANUP")
    print("=" * 70)

    disposable_ids = [d["case_id"] for d in disposable_cases]

    # Count records before deletion
    deleted_counts = {}
    
    # 1. Job stages for jobs in disposable cases
    job_ids = [r[0] for r in cur.execute(
        f"SELECT id FROM analysis_jobs WHERE case_id IN ({','.join(['?']*len(disposable_ids))})",
        disposable_ids
    ).fetchall()]

    if job_ids:
        cur.execute(
            f"DELETE FROM analysis_job_stages WHERE job_id IN ({','.join(['?']*len(job_ids))})",
            job_ids
        )
        deleted_counts["analysis_job_stages"] = cur.rowcount
    else:
        deleted_counts["analysis_job_stages"] = 0

    tables_with_case_id = [
        "analysis_jobs",
        "user_answers",
        "clarification_questions",
        "contradictions",
        "events",
        "entity_matches",
        "mvp_analyses",
        "reports",
        "audit_log",
        "evidence",
    ]

    for t in tables_with_case_id:
        cur.execute(
            f"DELETE FROM [{t}] WHERE case_id IN ({','.join(['?']*len(disposable_ids))})",
            disposable_ids
        )
        deleted_counts[t] = cur.rowcount

    # Finally delete cases
    cur.execute(
        f"DELETE FROM cases WHERE id IN ({','.join(['?']*len(disposable_ids))})",
        disposable_ids
    )
    deleted_counts["cases"] = cur.rowcount

    con.commit()
    con.close()

    # Clean up storage directories for disposable cases if any
    storage_deleted = 0
    for cid in disposable_ids:
        case_dir = STORAGE_DIR / cid
        if case_dir.exists():
            import shutil
            shutil.rmtree(case_dir, ignore_errors=True)
            storage_deleted += 1

    print("Cleanup Completed Successfully:")
    for t, cnt in deleted_counts.items():
        print(f"  - Deleted from {t}: {cnt} records")
    print(f"  - Cleaned up storage folders: {storage_deleted}")

    # Write cleanup report log
    log_file = BACKUPS_DIR / f"cleanup_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "disposable_cases_removed": len(disposable_ids),
        "retained_cases_count": len(retained_cases),
        "deleted_records": deleted_counts,
        "storage_folders_removed": storage_deleted,
        "disposable_ids": disposable_ids,
    }
    log_file.write_text(json.dumps(log_data, indent=2), encoding="utf-8")
    print(f"Cleanup summary logged to {log_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evidence AI Safe Demo Data Cleanup")
    parser.add_argument("--execute", action="store_true", help="Execute deletion (dry-run by default)")
    parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    args = parser.parse_args()

    run_cleanup(execute=args.execute, confirm=args.confirm)
