"""Google-only sign-in gate. No URL identity or anonymous fallback."""

from importlib.util import find_spec
from pathlib import Path
import base64

import streamlit as st

from streamlit_app.account_identity import (
    bind_account_state, google_configured, google_owner_id,
)


def _signin_page(ready: bool) -> None:
    logo = base64.b64encode(Path(__file__).with_name("ini_buta_icon_cropped.png").read_bytes()).decode("ascii")
    st.html("""<style>
    [data-testid="stAppViewContainer"]:has(.st-key-signin_surface) {
      background: radial-gradient(ellipse at 74% 22%, #fff0f2 0, transparent 42%),
                  linear-gradient(135deg,#f8f9fb 0%,#fff 48%,#e9edf2 100%);
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-signin_surface) {
      min-height:100svh; display:flex; flex-direction:column; justify-content:center;
      padding:64px 24px;
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-signin_surface) > [data-testid="stVerticalBlock"] {
      min-height:calc(100svh - 128px); justify-content:center;
    }
    .st-key-signin_surface {
      padding:48px 42px 34px; border-radius:30px;
      background:linear-gradient(145deg,rgba(255,255,255,.98),rgba(247,248,251,.94));
      border:1px solid rgba(255,255,255,.88);
      box-shadow:0 24px 80px rgba(39,48,66,.08),0 2px 8px rgba(39,48,66,.025);
    }
    .ini-signin-brand {display:flex;align-items:center;gap:14px;margin-bottom:34px;}
    .ini-signin-brand img {width:34px;height:72px;object-fit:contain;}
    .ini-signin-wordmark {font-size:26px;font-weight:600;letter-spacing:-.8px;color:#202631;}
    .ini-signin-wordmark span {color:#e51d42;}
    .ini-signin-tagline {font-size:11px;color:#687180;letter-spacing:.5px;margin-top:4px;}
    .ini-signin-title {font-size:30px;font-weight:500;letter-spacing:-.9px;color:#222936;line-height:1.25;margin:0 0 14px;}
    .ini-signin-copy {font-size:15px;line-height:1.7;color:#626c7a;margin:0 0 25px;}
    .st-key-google_signin button {min-height:52px;border-radius:13px;background:#fff;
      border:1px solid #e2e5eb;color:#27303e;box-shadow:0 3px 9px #22293605;}
    .st-key-google_signin button:disabled {color:#58616e;background:#f8f9fb;opacity:.8;}
    .st-key-google_signin button:not(:disabled):hover {border-color:#e51d42;background:#fffafb;}
    .st-key-google_signin button:focus-visible {outline:2px solid #e51d42;outline-offset:3px;}
    .ini-signin-footer {font-size:12px;text-align:center;color:#7b8491;margin-top:22px;line-height:1.7;}
    @media(max-width:600px) {
      [data-testid="stMainBlockContainer"]:has(.st-key-signin_surface) {padding:40px 18px;}
      .st-key-signin_surface {padding:34px 26px 28px;border-radius:24px;}
      .ini-signin-title {font-size:27px;}
    }
    </style>""")
    with st.container(horizontal_alignment="center"):
        with st.container(width=440, border=False, gap="small", key="signin_surface"):
            st.html(f'<div class="ini-signin-brand"><img src="data:image/png;base64,{logo}" alt="InI logo"><div><div class="ini-signin-wordmark">InI<span>.ai</span></div><div class="ini-signin-tagline">Question Intelligence</div></div></div><h1 class="ini-signin-title">Welcome to InI.</h1><p class="ini-signin-copy">A space for your questions.<br>A path for your learning.</p>')
            if st.button("Continue with Google", width="stretch", disabled=not ready, key="google_signin"):
                st.login("google")
            st.html('<div class="ini-signin-footer">Sign in to access your conversations<br>and continue your subject learning.</div>')
            if not ready:
                st.caption("Google sign-in will be available once account setup is complete.")


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
