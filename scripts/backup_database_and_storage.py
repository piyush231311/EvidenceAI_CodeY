"""
Evidence AI — Pre-Cleanup Database & Storage Backup Script.
Performs:
  1. Safe SQLite online backup using sqlite3.Connection.backup API.
  2. Integrity check on the backup database.
  3. Row count validation against the live database.
  4. Complete copy of storage/originals.
  5. Verification that all backups are readable.
"""

import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIVE_DB = PROJECT_ROOT / "evidence_ai.db"
STORAGE_DIR = PROJECT_ROOT / "storage"

TIMESTAMP = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = PROJECT_ROOT / "backups" / f"pre_cleanup_{TIMESTAMP}"
BACKUP_DB = BACKUP_DIR / "evidence_ai_backup.db"
BACKUP_STORAGE = BACKUP_DIR / "storage_backup"


def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[1/5] Backing up SQLite database to {BACKUP_DB}...")

    # Use SQLite online backup API
    src_conn = sqlite3.connect(LIVE_DB)
    dst_conn = sqlite3.connect(BACKUP_DB)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    print(f"[2/5] Running PRAGMA integrity_check on backup database...")
    check_conn = sqlite3.connect(BACKUP_DB)
    check_cur = check_conn.cursor()
    integrity = check_cur.execute("PRAGMA integrity_check").fetchone()[0]
    assert integrity == "ok", f"Integrity check failed: {integrity}"
    print(f"      Integrity check: {integrity.upper()}")

    print(f"[3/5] Validating row counts between live DB and backup DB...")
    live_conn = sqlite3.connect(LIVE_DB)
    live_cur = live_conn.cursor()
    tables = [r[0] for r in live_cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    mismatch = False
    for t in sorted(tables):
        live_cnt = live_cur.execute(f"SELECT count(*) FROM [{t}]").fetchone()[0]
        bkp_cnt = check_cur.execute(f"SELECT count(*) FROM [{t}]").fetchone()[0]
        if live_cnt != bkp_cnt:
            print(f"      ERROR: Table {t} count mismatch: live={live_cnt}, bkp={bkp_cnt}")
            mismatch = True
        else:
            print(f"      Table {t}: {bkp_cnt} rows (verified)")
    assert not mismatch, "Row count mismatch between live and backup!"
    live_conn.close()
    check_conn.close()

    print(f"[4/5] Preserving uploaded evidence storage from {STORAGE_DIR}...")
    if STORAGE_DIR.exists():
        shutil.copytree(STORAGE_DIR, BACKUP_STORAGE, dirs_exist_ok=True)
        orig_files = list(STORAGE_DIR.rglob("*.*"))
        bkp_files = list(BACKUP_STORAGE.rglob("*.*"))
        print(f"      Storage backup complete: {len(bkp_files)} files copied (source had {len(orig_files)})")
        assert len(orig_files) == len(bkp_files), "Storage file count mismatch!"

    print(f"[5/5] Backup successfully verified at {BACKUP_DIR}")
    print(f"      Backup DB size: {BACKUP_DB.stat().st_size:,} bytes")


if __name__ == "__main__":
    backup()
