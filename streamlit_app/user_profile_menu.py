"""Sidebar profile actions using native, keyboard-accessible controls."""
from collections.abc import Callable
import base64

import streamlit as st


def render_user_profile_menu(*, can_sign_out: bool, on_exit: Callable[[], None]) -> None:
    avatar = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="11" fill="#111827"/><text x="11" y="15" text-anchor="middle" font-family="sans-serif" font-size="11" fill="white">S</text></svg>').decode("ascii")
    with st.container(key="account_profile_footer"):
        with st.popover(f"![](data:image/svg+xml;base64,{avatar}) User profile",
                        type="tertiary", width="stretch", key="account_profile_menu"):
            st.button("Settings", icon=":material/settings:", disabled=True, type="tertiary",
                      help="Settings are not available yet.", width="stretch",
                      key="account_profile_settings")
            st.button("Exit app", icon=":material/logout:", on_click=on_exit, type="tertiary",
                      disabled=not can_sign_out, width="stretch",
                      help="Sign out of InI. Your saved chats will remain."
                      if can_sign_out else "Local developer mode has no signed-in account.",
                      key="account_profile_exit")
