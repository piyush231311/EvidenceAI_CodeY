import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project root if it exists
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY environment variable is required and must be at least 32 characters long.\n"
        "Generate one using: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )

try:
    SESSION_MINUTES = int(os.getenv("SESSION_MINUTES", "30"))
except ValueError:
    SESSION_MINUTES = 30

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
if COOKIE_SAMESITE not in ("lax", "strict", "none"):
    COOKIE_SAMESITE = "lax"

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5173").rstrip("/")
