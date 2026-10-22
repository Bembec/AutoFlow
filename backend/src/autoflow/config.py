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
