"""Sidebar profile actions using native, keyboard-accessible controls."""
from collections.abc import Callable, Mapping
import base64
from html import escape
import re

import streamlit as st


PROFILE_TRIGGER_CSS = """<style>
.st-key-account_profile_menu button{padding:4px 45px 4px 7px;min-height:44px;justify-content:flex-start;}
.st-key-account_profile_menu button > div > div[aria-hidden="true"]{display:none;}
.st-key-account_profile_menu [data-testid="stMarkdownContainer"]{min-width:0;max-width:100%;}
.st-key-account_profile_menu [data-testid="stMarkdownContainer"] p{
  display:block;font-size:14px;font-weight:400;line-height:30px;margin:0;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.st-key-account_profile_menu [data-testid="stMarkdownContainer"] img{
  width:30px;height:30px;max-height:30px;display:inline-block;vertical-align:middle;margin:0 10px 0 0;
}
</style>"""


def profile_identity(claims: Mapping) -> tuple[str, str]:
    """Use only Google sign-in's basic profile; never infer a name from email."""
    if not claims.get("is_logged_in"):
        return "User profile", "U"
    name = claims.get("name") or claims.get("given_name")
    if not isinstance(name, str) or not name.strip():
        return "User profile", "U"
    name = " ".join(name.split())[:120]
    parts = name.split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    return name, initials


def render_user_profile_menu(*, can_sign_out: bool, on_exit: Callable[[], None]) -> None:
    name, initials = profile_identity(dict(st.user) if can_sign_out else {})
    label = re.sub(r'([\\`*_{}\[\]()<>!|~])', r'\\\1', name)
    avatar_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">'
        '<circle cx="15" cy="15" r="15" fill="#111827"/>'
        '<text x="15" y="19" text-anchor="middle" font-family="sans-serif" '
        f'font-size="11" font-weight="400" fill="white">{escape(initials)}</text></svg>'
    )
    avatar = base64.b64encode(avatar_svg.encode("utf-8")).decode("ascii")
    st.html(PROFILE_TRIGGER_CSS)
    with st.container(key="account_profile_footer"):
        with st.popover(f"![](data:image/svg+xml;base64,{avatar}) {label}",
                        help="Open user profile", type="tertiary", width="stretch", key="account_profile_menu"):
            if name != "User profile":
                st.text(name)
            st.button("Settings", icon=":material/settings:", disabled=True, type="tertiary",
                      help="Settings are not available yet.", width="stretch",
                      key="account_profile_settings")
            st.button("Exit", icon=":material/logout:", on_click=on_exit, type="tertiary",
                      disabled=not can_sign_out, width="stretch",
                      help="Sign out of InI. Your saved chats will remain."
                      if can_sign_out else "Local developer mode has no signed-in account.",
                      key="account_profile_exit")
