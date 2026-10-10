"""Google-only sign-in gate. No URL identity or anonymous fallback."""

from importlib.util import find_spec
from pathlib import Path

import streamlit as st

from streamlit_app.account_identity import (
    bind_account_state, google_configured, google_owner_id,
)


def _signin_page(ready: bool) -> None:
    with st.container(horizontal=True, horizontal_alignment="center"):
        with st.container(width=440, border=False):
            st.space("large")
            st.image(str(Path(__file__).with_name("ini_buta_icon_cropped.png")), width=48)
            st.subheader("Welcome to InI.ai")
            st.write("Continue your questions. Keep your learning together.")
            st.space("medium")
            if st.button("Continue with Google", width="stretch", disabled=not ready, key="google_signin"):
                st.login("google")
            st.caption("Sign in to access your conversations and subject learning.")
            if not ready:
                st.info("Google sign-in is being configured. Conversation access is locked until it is ready.")


def require_google_account() -> str:
    try:
        configuration = st.secrets.to_dict()
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        configuration = {}
    ready = google_configured(configuration) and find_spec("authlib") is not None
    claims = dict(st.user) if ready else {}
    client_id = configuration["auth"]["google"]["client_id"] if ready else ""
    owner_id = google_owner_id(claims, client_id) if ready else None
    # Old visitor links are not credentials, and must not be kept in new links.
    if "visitor" in st.query_params:
        del st.query_params["visitor"]
    if owner_id is None:
        st.session_state.clear()
        if claims.get("is_logged_in"):
            st.warning("Your sign-in has expired or could not be verified. Please sign in again.")
            if st.button("Sign out and try again", key="invalid_google_logout"):
                st.logout()
        _signin_page(ready)
        st.stop()
    bind_account_state(st.session_state, owner_id)
    return owner_id


def sign_out() -> None:
    st.session_state.clear()
    st.query_params.clear()
    st.logout()
