"""Vercel serverless entry point."""
import sys
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Workaround: set data dir to /tmp on Vercel (read-only filesystem elsewhere)
import os
if "VERCEL" in os.environ:
    os.environ["DATA_DIR"] = "/tmp/data"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/data/reports.db"

from backend.main import app
