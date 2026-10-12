"""Loopback-only answer engine for the isolated hosted authentication test."""
from threading import Thread
import time
from types import SimpleNamespace

import requests
import streamlit as st
import uvicorn

TEST_API_BASE = "http://127.0.0.1:8012"


def provider_post(url, **kwargs):
    payload = kwargs.get("json")
    if url == "https://api.openai.com/v1/responses" and isinstance(payload, dict) and str(payload.get("model", "")).startswith("gpt-4"):
        # Keep compatibility scoped to this test process and original model.
        kwargs["json"] = {key: value for key, value in payload.items() if key != "reasoning"}
    return requests.post(url, **kwargs)


@st.cache_resource(show_spinner=False)
def start_test_engine():
    from api import llm_answers
    llm_answers.requests = SimpleNamespace(post=provider_post)
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
