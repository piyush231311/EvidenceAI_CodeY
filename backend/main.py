try:
    import ctranslate2
except ImportError:
    pass

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from backend.config import ALLOWED_ORIGIN
from backend.db import init_db
from backend.auth import limiter, auth_router
from backend.routes import router as api_router

# Initialize FastAPI application
app = FastAPI(
    title="Evidence AI - Intake API",
    description="Victim-first digital evidence intake and forensic preservation platform.",
    version="1.0.0"
)

# Attach rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration: strict allowed origin, credentials, explicit methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Requested-With", "Authorization"],
)


class SecurityAndCSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Enforce CSRF defense on state-changing API endpoints
        if request.url.path.startswith("/api"):
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                csrf_header = request.headers.get("x-requested-with", "")
                if csrf_header.lower() != "evidence-ai":
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Missing required CSRF protection header."}
                    )

        response = await call_next(request)

        # Set security headers on all /api responses
        if request.url.path.startswith("/api"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store"

        return response


app.add_middleware(SecurityAndCSRFMiddleware)


@app.on_event("startup")
def on_startup():
    Path("storage/originals").mkdir(parents=True, exist_ok=True)
    init_db()


# Include Auth and API routers
app.include_router(auth_router)
app.include_router(api_router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Evidence AI Intake API"}
