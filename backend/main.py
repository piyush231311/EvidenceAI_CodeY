import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routes import router as api_router

# Initialize FastAPI application
app = FastAPI(
    title="Evidence AI - Intake API",
    description="Victim-first digital evidence intake and forensic preservation platform.",
    version="1.0.0"
)

# CORS configuration supporting Netlify frontend, Render deployment, and local dev
raw_origins = os.getenv("CORS_ORIGINS", "").strip()
if raw_origins:
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https:\/\/.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure storage directories exist and initialize database schema
@app.on_event("startup")
def on_startup():
    storage_path = os.getenv("STORAGE_DIR", "storage/originals")
    Path(storage_path).mkdir(parents=True, exist_ok=True)
    init_db()


# Include API routes
app.include_router(api_router)


@app.get("/api/health")
def health_check():
    """
    Lightweight, fast liveness probe for Render, load balancers, and container monitors.
    Returns immediately with zero ML/model overhead.
    """
    return {"status": "healthy", "service": "Evidence AI Intake API"}
