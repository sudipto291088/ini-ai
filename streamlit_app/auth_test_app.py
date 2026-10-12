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

import streamlit as st
from streamlit_app.google_signin import require_google_account
from streamlit_app.auth_test_engine import TEST_API_BASE, start_test_engine

st.set_page_config(page_title="InI.ai", layout="wide", initial_sidebar_state="expanded")
require_google_account()
# Only this isolated entry point opts into the new database when configured.
database_url = str(st.secrets.get("INI_DATABASE_URL", "")).strip()
os.environ["INI_STORAGE_BACKEND"] = "postgres" if database_url else "sqlite"
if database_url:
    os.environ["INI_DATABASE_URL"] = database_url
    from streamlit_app.storage_sqlite import init_db
    from streamlit_app.storage_postgres import StorageUnavailable
    try:
        init_db()
    except StorageUnavailable as exc:
        st.error(str(exc))
        st.stop()
api_key = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
if not api_key:
    st.error("The test answer engine is not configured yet.")
    st.stop()
os.environ["OPENAI_API_KEY"] = api_key
os.environ["INI_LLM_MODEL"] = str(st.secrets.get("INI_LLM_MODEL", "gpt-5-mini")).strip() or "gpt-5-mini"
for setting in ("INI_LLM_MAX_TOKENS",):
    if setting in st.secrets:
        os.environ[setting] = str(st.secrets[setting])
os.environ["INI_API_BASE"] = TEST_API_BASE
try:
    start_test_engine()
except RuntimeError:
    st.error("The test answer engine could not start. Please try again shortly.")
    st.stop()
runpy.run_path(str(app_dir / "app.py"), run_name="__main__")
