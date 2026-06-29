"""Vercel serverless entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os

if "VERCEL" in os.environ:
    os.environ["DATA_DIR"] = "/tmp/data"
    # Use Neon Postgres if available, otherwise fallback to SQLite in /tmp
    pg_url = os.environ.get("POSTGRES_URL", "")
    if pg_url:
        pg_url = pg_url.replace("?sslmode=require", "?sslmode=require")
        os.environ["DATABASE_URL"] = pg_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/data/reports.db"

from backend.main import app
