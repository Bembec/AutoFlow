"""
Central configuration for AutoFlow.

Loads private settings from backend/.env and defines every file path
the workflow reads from or writes to.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# backend/ is three levels above this file: backend/src/autoflow/config.py
BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.getenv("AUTOFLOW_DATA_DIR", BACKEND_DIR / "data"))

# Input enquiries (defaults to the fake sample data in the repository)
INPUT_CSV_PATH = Path(os.getenv(
    "AUTOFLOW_INPUT_CSV", BACKEND_DIR / "data" / "sample" / "customers.csv"
))

# Generated files (ignored by git)
OUTPUT_DIR = DATA_DIR / "output"
PROCESSED_CSV_PATH = OUTPUT_DIR / "processed_customers.csv"
EMAIL_PREVIEWS_PATH = OUTPUT_DIR / "email_previews.txt"
ACTIVITY_LOG_PATH = OUTPUT_DIR / "activity.log"
DATABASE_PATH = OUTPUT_DIR / "autoflow.db"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# SQLite by default; set DATABASE_URL for PostgreSQL in production
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DATABASE_PATH.as_posix()}"

# How long a login token stays valid
ACCESS_TOKEN_TTL_HOURS = int(os.getenv("ACCESS_TOKEN_TTL_HOURS", "24"))

# development | staging | production
ENVIRONMENT = os.getenv("AUTOFLOW_ENV", "development").lower()

# Browser origins allowed to call the API directly (comma-separated).
# Not needed when the web app proxies /api on the same origin.
CORS_ORIGINS = [o.strip() for o in os.getenv("AUTOFLOW_CORS_ORIGINS", "").split(",") if o.strip()]


class UnsafeConfiguration(Exception):
    """Staging/production settings that would put customer data at risk."""


def check_deployment_settings():
    """Refuse to start staging/production with development-only settings."""

    if ENVIRONMENT == "development":
        return

    problems = []

    if not os.getenv("AUTOFLOW_SECRET_KEYS"):
        problems.append("AUTOFLOW_SECRET_KEYS must be set (no development key file).")
    if DATABASE_URL.startswith("sqlite"):
        problems.append("DATABASE_URL must point to PostgreSQL.")
    if not PUBLIC_URL.startswith("https://"):
        problems.append("AUTOFLOW_PUBLIC_URL must use https.")
    if ENVIRONMENT == "production" and os.getenv("EMAIL_TEST_RECIPIENT"):
        problems.append("EMAIL_TEST_RECIPIENT redirects real emails; unset it in production.")

    if problems:
        raise UnsafeConfiguration(f"Unsafe {ENVIRONMENT} settings: " + " ".join(problems))


# Public address of the API, used in webhook and OAuth callback URLs
PUBLIC_URL = os.getenv("AUTOFLOW_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")

# Workspace used by the command-line workflow (python -m autoflow)
LOCAL_WORKSPACE_SLUG = "local"
