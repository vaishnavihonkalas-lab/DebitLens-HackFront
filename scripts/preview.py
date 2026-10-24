"""Start explicit SQLite preview. Run after installing backend requirements."""

import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
os.chdir(root / "backend")
sys.path.insert(0, str(root / "backend"))
os.environ["STORAGE_MODE"] = "sqlite"
os.environ.setdefault("SQLITE_PATH", str(root / "local-data/debitlens.db"))
import uvicorn

uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
