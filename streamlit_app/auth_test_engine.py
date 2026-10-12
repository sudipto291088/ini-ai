"""Loopback-only answer engine for the isolated hosted authentication test."""
from threading import Thread
import time

import streamlit as st
import uvicorn

TEST_API_BASE = "http://127.0.0.1:8012"


@st.cache_resource(show_spinner=False)
def start_test_engine():
    # Never expose the internal API on a public interface. Browser requests go
    # through the authenticated Streamlit UI, not directly to this listener.
    server = uvicorn.Server(uvicorn.Config(
        "api.main:app", host="127.0.0.1", port=8012,
        lifespan="off", access_log=False, log_level="warning",
    ))
    worker = Thread(target=server.run, name="ini-auth-test-engine", daemon=True)
    worker.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if not worker.is_alive() or time.monotonic() >= deadline:
            raise RuntimeError("The isolated answer engine could not start.")
        time.sleep(0.05)
    return server
