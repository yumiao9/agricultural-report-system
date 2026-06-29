"""Vercel serverless entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os

if "VERCEL" in os.environ:
    os.environ["DATA_DIR"] = "/tmp/data"
    # If DATABASE_URL is already set via Vercel env (cleaned for asyncpg), use it
    if not os.environ.get("DATABASE_URL"):
        pg_url = os.environ.get("POSTGRES_URL", "")
        if pg_url:
            pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://")
            pg_url = pg_url.replace("postgres://", "postgresql+asyncpg://")
            pg_url = pg_url.replace("?channel_binding=require", "")
            pg_url = pg_url.replace("&channel_binding=require", "")
            pg_url = pg_url.replace("?sslmode=require", "?ssl=require")
            pg_url = pg_url.replace("&sslmode=require", "&ssl=require")
            os.environ["DATABASE_URL"] = pg_url
        else:
            os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/data/reports.db"

from backend.main import app
