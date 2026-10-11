"""Google-only sign-in gate. No URL identity or anonymous fallback."""

from importlib.util import find_spec
from pathlib import Path
import base64
import os

import streamlit as st

from streamlit_app.account_identity import (
    bind_account_state, google_configured, google_owner_id,
)


def _signin_page(ready: bool) -> None:
    logo = base64.b64encode(Path(__file__).with_name("ini_buta_icon_cropped.png").read_bytes()).decode("ascii")
    st.html("""<style>
    [data-testid="stAppViewContainer"]:has(.st-key-signin_surface) {
      background: radial-gradient(ellipse at 66% 38%, #fcecef 0, transparent 42%),
                  radial-gradient(ellipse at 18% 82%,#e0e5ed 0,transparent 52%),
                  linear-gradient(125deg,#fafbfc,#f3f5f8);
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-signin_surface) {
      min-height:100svh; display:flex; flex-direction:column; justify-content:center;
      padding:64px 24px;
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-signin_surface) > [data-testid="stVerticalBlock"] {
      min-height:calc(100svh - 128px); justify-content:center;
    }
    .st-key-signin_surface {
      padding:16px; border-radius:32px;
      background:linear-gradient(150deg,#ffffff 10%,#fcfcfd 54%,#f3f5f9 100%);
      border:1px solid rgba(255,255,255,.92);
      box-shadow:0 32px 70px -24px rgba(37,45,65,.20),0 6px 18px -8px rgba(37,45,65,.08),inset 0 1px 0 #fff;
    }
    .ini-signin-brand {display:flex;align-items:center;justify-content:center;gap:14px;margin-bottom:28px;}
    .ini-signin-brand img {width:35px;height:72px;object-fit:contain;}
    .ini-signin-wordmark {font-size:30px;font-weight:600;letter-spacing:-1px;color:#202631;}
    .ini-signin-wordmark span {color:#e51d42;}
    .ini-signin-tagline {font-size:10px;color:#687180;letter-spacing:.7px;margin-top:3px;}
    .ini-signin-title {text-align:center;font-size:30px;font-weight:500;letter-spacing:-1px;color:#222936;line-height:1.3;margin:0 0 12px;}
    .ini-signin-title::before {content:"";display:block;width:34px;height:2px;margin:0 auto 25px;
      background:linear-gradient(90deg,transparent,#e51d42,transparent);border-radius:2px;}
    .ini-signin-copy {text-align:center;font-size:14px;line-height:1.8;color:#626c7a;margin:0 0 25px;}
    .st-key-google_signin button {min-height:70px;height:70px;border-radius:16px;
      background:linear-gradient(165deg,#fff 0%,#fafbfc 55%,#eef1f5 100%);
      border:0;color:#1f1f1f;gap:10px;
      box-shadow:0 10px 20px -9px rgba(38,48,66,.28),0 3px 6px rgba(38,48,66,.06),
                 inset 0 1px 0 #fff,inset 0 -2px 3px rgba(110,124,146,.09);
      transition:box-shadow .18s ease,transform .18s ease;}
    .st-key-google_signin button::before {content:"";display:block;flex:0 0 20px;width:20px;height:20px;
      background:url("https://developers.google.com/static/identity/images/g-logo.png") center/contain no-repeat;}
    .st-key-google_signin button p {font-size:14px;font-weight:500;line-height:20px;}
    .st-key-google_signin button:disabled {color:#626770;opacity:1;cursor:not-allowed;}
    .st-key-google_signin button:not(:disabled):hover {transform:translateY(-1px);
      box-shadow:0 13px 24px -9px rgba(38,48,66,.3),0 4px 7px rgba(38,48,66,.07),inset 0 1px 0 #fff;}
    .st-key-google_signin button:not(:disabled):active {transform:translateY(1px);
      box-shadow:0 4px 9px rgba(38,48,66,.1),inset 0 1px 3px rgba(38,48,66,.08);}
    .st-key-google_signin button:focus-visible {outline:2px solid #e51d42;outline-offset:3px;}
    .ini-signin-footer {font-size:12px;text-align:center;color:#707986;margin-top:18px;line-height:1.75;}
    .st-key-signin_surface [data-testid="stCaptionContainer"] {text-align:center;font-size:11px;color:#7b8491;}
    .ini-signin-story {position:relative;overflow:hidden;min-height:480px;padding:34px 30px 22px;
      border-radius:23px;background:radial-gradient(ellipse at 78% 82%,#f3cdd5 0,transparent 48%),
      linear-gradient(145deg,#f6f7fa 0%,#e9edf3 65%,#f3e8ec 100%);}
    .ini-signin-story .ini-signin-brand {justify-content:flex-start;margin-bottom:46px;}
    .ini-signin-story h2 {font-size:38px;font-weight:500;letter-spacing:-1.5px;color:#252c39;line-height:1.18;margin:0 0 15px;}
    .ini-signin-story h2 span {color:#d91c40;}
    .ini-signin-story p {font-size:14px;color:#657081;line-height:1.7;max-width:280px;margin:0;}
    .ini-signin-art {width:100%;height:185px;display:block;margin-top:20px;overflow:visible;}
    .ini-signin-network {position:relative;height:150px;margin-top:24px;}
    .ini-signin-network::before {content:"";position:absolute;width:145px;height:145px;left:90px;top:0;border:1px solid #ffffff90;border-radius:50%;}
    .ini-signin-network::after {content:"";position:absolute;left:55px;right:35px;top:73px;height:1px;background:linear-gradient(90deg,#e51d4260,#a8b1c350);transform:rotate(-12deg);}
    .ini-signin-node {position:absolute;z-index:1;padding:11px 18px;background:#ffffffdc;border-radius:12px;color:#677180;font-size:11px;box-shadow:0 6px 18px #35425e0b;}
    .ini-signin-node.question {left:3%;top:55px;font-size:22px;color:#d91c40;padding:6px 25px;}
    .ini-signin-node.explore {left:39%;top:14px;}
    .ini-signin-node.connect {right:0;top:59px;}
    .ini-signin-node.understand {right:13%;top:112px;color:#d91c40;}
    .ini-signin-story-note {font-size:10px;color:#687180;letter-spacing:1px;text-transform:uppercase;margin-top:18px;}
    .st-key-signin_form {padding:32px 24px;}
    .st-key-signin_form .ini-signin-title {font-size:30px;}
    .st-key-signin_form .ini-signin-title::before {display:none;}
    .ini-signin-kicker {text-align:center;font-size:10px;letter-spacing:2px;color:#d91c40;text-transform:uppercase;margin-bottom:16px;}
    .st-key-signin_form .ini-signin-copy {margin-bottom:32px;}
    @media(max-width:600px) {
      [data-testid="stMainBlockContainer"]:has(.st-key-signin_surface) {padding:40px 18px;}
      .st-key-signin_surface {padding:12px;border-radius:26px;}
      .ini-signin-title {font-size:27px;}
      .ini-signin-story {min-height:0;padding:26px 24px;}
      .ini-signin-story .ini-signin-brand {margin-bottom:24px;}
      .ini-signin-story h2 {font-size:30px;}
      .ini-signin-art {height:145px;margin-top:12px;}
      .st-key-signin_form {padding:28px 18px;}
    }
    </style>""")
    with st.container(horizontal_alignment="center"):
        with st.container(width=920, border=False, gap="small", key="signin_surface"):
            story, form = st.columns([1.05, 1], gap="small", vertical_alignment="center")
            with story:
                st.html(f'''<section class="ini-signin-story">
                <div class="ini-signin-brand"><img src="data:image/png;base64,{logo}" alt="InI logo"><div><div class="ini-signin-wordmark">InI<span>.ai</span></div><div class="ini-signin-tagline">Question Intelligence</div></div></div>
                <h2>A question.<br><span>A new possibility.</span></h2>
                <p>Follow the connections.<br>Turn curiosity into understanding.</p>
                <div class="ini-signin-network" aria-label="A question connects to exploration and understanding"><span class="ini-signin-node question">?</span><span class="ini-signin-node explore">Explore</span><span class="ini-signin-node connect">Connect</span><span class="ini-signin-node understand">Understand</span></div>
                <div class="ini-signin-story-note">Built for a curious mind.</div></section>''')
            with form:
                with st.container(key="signin_form", gap="small"):
                    st.html('<div class="ini-signin-kicker">Your learning, continued</div><h1 class="ini-signin-title">Welcome to InI.</h1><p class="ini-signin-copy">A space for your questions.<br>A path for your learning.</p>')
                    with st.container(horizontal_alignment="center"):
                        if st.button("Continue with Google", width=240, disabled=not ready, key="google_signin"):
                            st.login("google")
                    st.html('<div class="ini-signin-footer">Sign in to keep your conversations<br>and subject learning together.</div>')
                    if not ready:
                        st.caption("Google sign-in is not connected yet.")


def local_developer_enabled() -> bool:
    """Opt-in only on a server explicitly bound to the loopback interface."""
    return os.environ.get("INI_LOCAL_DEVELOPER") == "1" and st.get_option("server.address") in {"127.0.0.1", "::1"}


def require_google_account() -> str:
    if local_developer_enabled():
        # Separate local workspace; never infer ownership from a copied URL.
        owner_id = "local-developer-workspace"
        if "visitor" in st.query_params:
            del st.query_params["visitor"]
        bind_account_state(st.session_state, owner_id)
        return owner_id
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
    if local_developer_enabled():
        st.rerun()
        return
    st.logout()
