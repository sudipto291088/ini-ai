"""Sidebar profile actions using native, keyboard-accessible controls."""
from collections.abc import Callable, Mapping
import base64
from html import escape
import re

import streamlit as st

PROFILE_MENU_VERSION = 4


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
[data-testid="stPopoverBody"]:has(.st-key-account_profile_panel){
  width:264px;max-width:calc(100vw - 24px);padding:8px !important;
  border:1px solid #e9ecf1;border-radius:16px;
  box-shadow:0 14px 42px #1720331f,0 3px 10px #1720330a;background:#fff;
}
.st-key-account_profile_panel,.st-key-account_profile_panel [data-testid="stVerticalBlock"]{gap:2px !important;}
.ini-profile-menu-header{display:flex;align-items:center;gap:11px;padding:10px 9px 13px;
  margin:0 2px 6px;border-bottom:1px solid #edf0f4;min-width:0;}
.ini-profile-menu-avatar{display:grid;place-items:center;width:32px;height:32px;flex:none;
  border-radius:50%;background:#172033;color:#fff;font-size:11px;font-weight:400;}
.ini-profile-menu-identity{min-width:0;}
.ini-profile-menu-name{font-size:14px;font-weight:400;line-height:20px;color:#252d3a;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ini-profile-menu-kind{font-size:11px;line-height:17px;color:#818998;}
.st-key-account_profile_panel button{
  width:100%;height:38px !important;min-height:38px !important;padding:0 10px !important;
  justify-content:flex-start !important;text-align:left;gap:10px;
  border:0;border-radius:9px;background:transparent;box-shadow:none;color:#303947;
}
.st-key-account_profile_panel button p{font-size:14px;font-weight:400;line-height:20px;margin:0;}
.st-key-account_profile_panel button > div{justify-content:flex-start !important;}
.st-key-account_profile_panel button [data-has-shortcut]{gap:10px;}
.st-key-account_profile_panel button [data-testid="stIconMaterial"]{font-size:18px;line-height:18px;}
.st-key-account_profile_panel button:not(:disabled):hover{background:#f3f5f8;color:#202733;}
.st-key-account_profile_panel button:focus-visible{outline:2px solid #e76b80;outline-offset:-2px;}
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


def _close_profile_menu() -> None:
    st.session_state["account_profile_menu"] = False


def profile_header_html(name: str, initials: str, signed_in: bool) -> str:
    kind = "Google account" if signed_in else "Local workspace"
    return f'''<div class="ini-profile-menu-header">
      <div class="ini-profile-menu-avatar" aria-hidden="true">{escape(initials)}</div>
      <div class="ini-profile-menu-identity"><div class="ini-profile-menu-name" title="{escape(name, quote=True)}">{escape(name)}</div>
      <div class="ini-profile-menu-kind">{kind}</div></div></div>'''


def render_user_profile_menu(*, can_sign_out: bool, on_exit: Callable[[], None],
                             on_settings: Callable[[], None] | None = None) -> None:
    if st.session_state.pop("_settings_deleted_notice", False):
        st.toast("Your saved conversations and subject curricula were deleted.")
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
                        type="tertiary", width="stretch", key="account_profile_menu",
                        on_change="rerun"):
            with st.container(key="account_profile_panel", gap=None):
                st.html(profile_header_html(name, initials, can_sign_out))
                if st.button("Settings", icon=":material/settings:", disabled=on_settings is None, type="tertiary",
                             help="Manage your account and conversations." if on_settings
                             else "Account settings are available with Google sign-in.", width="stretch",
                             key="account_profile_settings", on_click=_close_profile_menu):
                    on_settings()
                st.button("Exit", icon=":material/logout:", on_click=on_exit, type="tertiary",
                          disabled=not can_sign_out, width="stretch",
                          help="Sign out of InI. Your saved chats will remain."
                          if can_sign_out else "Local developer mode has no signed-in account.",
                          key="account_profile_exit")
