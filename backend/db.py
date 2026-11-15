import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./evidence_ai.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Isolated database engine configuration - easily swappable for PostgreSQL
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and run schema migrations if necessary."""
    from . import models  # Ensure all SQLAlchemy models are registered
    Base.metadata.create_all(bind=engine)

    # Auto-migrate SQLite schema for any new columns added to entity_matches
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                res = conn.execute(text("PRAGMA table_info(entity_matches)"))
                cols = [row[1] for row in res.fetchall()]
                migrations = [
                    ("is_single_occurrence", "BOOLEAN DEFAULT 0"),
                    ("extraction_confidence", "FLOAT DEFAULT 1.0"),
                    ("classification_confidence", "FLOAT DEFAULT 1.0"),
                    ("ocr_confidence", "FLOAT"),
                    ("is_low_confidence", "BOOLEAN DEFAULT 0"),
                    ("requires_source_verification", "BOOLEAN DEFAULT 0"),
                    ("verification_reasons_json", "TEXT"),
                    ("related_entities_json", "TEXT"),
                    ("match_type", "VARCHAR(64)"),
                ]
                for col_name, col_type in migrations:
                    if col_name not in cols:
                        conn.execute(text(f"ALTER TABLE entity_matches ADD COLUMN {col_name} {col_type}"))

                # Auto-migrate clarification_questions table
                res_q = conn.execute(text("PRAGMA table_info(clarification_questions)"))
                cols_q = [row[1] for row in res_q.fetchall()]
                q_migrations = [
                    ("activity_name", "VARCHAR(128) DEFAULT ''"),
                    ("why_it_matters", "TEXT DEFAULT ''"),
                ]
                for col_name, col_type in q_migrations:
                    if col_name not in cols_q:
                        conn.execute(text(f"ALTER TABLE clarification_questions ADD COLUMN {col_name} {col_type}"))

                # Auto-migrate evidence table
                res_e = conn.execute(text("PRAGMA table_info(evidence)"))
                cols_e = [row[1] for row in res_e.fetchall()]
                e_migrations = [
                    ("extracted_text", "TEXT"),
                    ("extraction_confidence", "FLOAT"),
                    ("extraction_metadata", "TEXT"),
                    ("processing_time_ms", "FLOAT"),
                    ("review_status", "VARCHAR(32) DEFAULT 'INCLUDED'"),
                    ("quarantine_reason", "TEXT"),
                ]
                for col_name, col_type in e_migrations:
                    if col_name not in cols_e:
                        conn.execute(text(f"ALTER TABLE evidence ADD COLUMN {col_name} {col_type}"))

                # Auto-migrate analysis_jobs table for policy mode
                res_j = conn.execute(text("PRAGMA table_info(analysis_jobs)"))
                cols_j = [row[1] for row in res_j.fetchall()]
                j_migrations = [
                    ("policy_mode", "VARCHAR(32) DEFAULT 'DEVELOPMENT'"),
                    ("policy_version", "VARCHAR(16) DEFAULT '1.0.0'"),
                ]
                for col_name, col_type in j_migrations:
                    if col_name not in cols_j:
                        conn.execute(text(f"ALTER TABLE analysis_jobs ADD COLUMN {col_name} {col_type}"))

                # Auto-migrate cases table for owner_id
                res_c = conn.execute(text("PRAGMA table_info(cases)"))
                cols_c = [row[1] for row in res_c.fetchall()]
                if "owner_id" not in cols_c:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN owner_id VARCHAR(36)"))

                conn.commit()
        except Exception:
            pass
