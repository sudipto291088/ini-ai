"""Separate hosted Google-authentication test; not the production entry point."""
import os
from pathlib import Path
import runpy
import sys

app_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(app_dir.parent))
os.environ["INI_GOOGLE_SIGNIN_ENABLED"] = "1"
os.environ["INI_LOCAL_DEVELOPER"] = "0"
os.environ["INI_DB_PATH"] = str(app_dir / "auth_test_sessions.db")
runpy.run_path(str(app_dir / "app.py"), run_name="__main__")
