"""Google-account settings with owner-checked conversation controls."""
from datetime import datetime, timezone
from html import escape

import streamlit as st

from streamlit_app.account_identity import bind_account_state, google_owner_id
from streamlit_app.account_data import (
    conversation_summary, delete_all_conversations, export_conversations,
)
from streamlit_app.user_profile_menu import profile_identity


SETTINGS_CSS = """<style>
div[role="dialog"]:has(.st-key-ini_account_settings){
  border:1px solid #eef0f4;border-radius:24px;
  box-shadow:0 28px 90px #17203326;background:#fff;
}
.st-key-ini_account_settings{color:#242b38;}
.st-key-ini_account_settings [data-testid="stCaptionContainer"]{color:#737d8b;}
.st-key-ini_account_settings [role="tablist"]{gap:28px;margin:8px 0 22px;background:transparent;}
.st-key-ini_account_settings [role="tab"]{padding:10px 0;font-size:14px;}
.st-key-ini_account_settings [role="tab"][aria-selected="true"]{color:#c62e4b;}
.st-key-ini_account_settings .react-aria-SelectionIndicator{background:#e51d42 !important;}
.st-key-ini_account_settings button{border-radius:11px;min-height:40px;box-shadow:none;}
.st-key-ini_account_settings button p{font-size:14px;font-weight:400;}
.ini-settings-identity{display:flex;align-items:center;gap:18px;padding:10px 0 28px;}
.ini-settings-avatar{display:grid;place-items:center;width:56px;height:56px;flex:none;
  border-radius:50%;background:#172033;color:#fff;font-size:18px;font-weight:400;}
.ini-settings-name{font-size:23px;font-weight:500;letter-spacing:-.5px;line-height:1.35;overflow-wrap:anywhere;}
.ini-settings-email{font-size:14px;color:#737d8b;margin-top:4px;overflow-wrap:anywhere;}
.ini-settings-row{display:flex;justify-content:space-between;align-items:center;gap:16px;
  padding:17px 0;border-top:1px solid #edf0f4;font-size:14px;}
.ini-settings-row>span:first-child{color:#687383;}
.ini-settings-connected{display:inline-flex;align-items:center;gap:7px;color:#32745c;font-size:12px;}
.ini-settings-connected::before{content:"";width:6px;height:6px;border-radius:50%;background:#439b76;}
.ini-settings-note{font-size:13px;line-height:1.75;color:#737d8b;padding:17px 0 8px;max-width:580px;}
.ini-settings-summary{display:flex;gap:36px;padding:4px 0 26px;}
.ini-settings-stat{font-size:27px;font-weight:400;line-height:1.25;letter-spacing:-.6px;}
.ini-settings-stat-label{font-size:12px;color:#737d8b;margin-top:5px;letter-spacing:0;}
.ini-settings-section-title{font-size:16px;font-weight:500;margin:0 0 6px;color:#293141;}
.ini-settings-copy{font-size:13px;color:#737d8b;line-height:1.7;margin:0 0 15px;}
.st-key-ini_settings_export_section{padding:22px;background:#f6f8fa;border-radius:16px;margin-bottom:18px;}
.st-key-ini_settings_prepare button,.st-key-ini_settings_download button{
  background:#fff;border:1px solid #e7eaf0;box-shadow:0 3px 9px #17203308;}
.st-key-ini_settings_danger [data-testid="stExpander"]{border:1px solid #f2e6e9;border-radius:14px;background:#fffbfc;}
.st-key-ini_settings_danger [data-testid="stExpander"] summary p{color:#ac3851;font-size:13px;}
.st-key-ini_settings_confirm_delete button:not(:disabled){background:#c83251;border-color:#c83251;color:#fff;}
.st-key-ini_settings_confirm_delete button:disabled{opacity:.5;}
@media(max-width:600px){
  div[role="dialog"]:has(.st-key-ini_account_settings){border-radius:20px;max-width:calc(100vw - 24px);}
  .ini-settings-name{font-size:20px;}.ini-settings-identity{gap:13px;}
  .ini-settings-summary{gap:26px;}.st-key-ini_settings_export_section{padding:17px;}
}
</style>"""


def _current_owner(expected_owner: str | None = None) -> str | None:
    """Recheck authentication even during a dialog-only rerun."""
    try:
        client_id = st.secrets["auth"]["google"]["client_id"]
        owner = google_owner_id(dict(st.user), client_id)
    except (KeyError, TypeError, FileNotFoundError):
        return None
    if not owner or st.session_state.get("_authenticated_owner") != owner:
        return None
    if expected_owner is not None and owner != expected_owner:
        return None
    return owner


def _after_delete(owner: str) -> None:
    # Discard the current in-memory chat so it cannot be saved back on the next rerun.
    st.session_state.clear()
    bind_account_state(st.session_state, owner)
    st.session_state["_settings_deleted_notice"] = True
    st.query_params.clear()
    st.rerun()


def render_settings_content(expected_owner: str, *, on_deleted=None) -> None:
    owner = _current_owner(expected_owner)
    if owner is None:
        st.error("Please sign in again to manage your account.")
        return
    claims = dict(st.user)
    name, initials = profile_identity(claims)
    email = claims.get("email")
    email = email if isinstance(email, str) else "Email unavailable"
    st.html(SETTINGS_CSS)
    with st.container(key="ini_account_settings"):
        st.caption("Manage your account and saved conversations.")
        account, conversations = st.tabs(["Account", "Conversations"])
        with account:
            st.html(f'''<div class="ini-settings-identity">
              <div class="ini-settings-avatar">{escape(initials)}</div>
              <div><div class="ini-settings-name">{escape(name)}</div>
              <div class="ini-settings-email">{escape(email)}</div></div></div>
              <div class="ini-settings-row"><span>Sign-in method</span><span>Google</span></div>
              <div class="ini-settings-row"><span>Account connection</span><span class="ini-settings-connected">Connected</span></div>
              <div class="ini-settings-note">Your name and email come from your Google sign-in profile.
              InI does not have access to your Gmail inbox, Drive files, or contacts.</div>''')
            st.link_button("Privacy policy", "?page=privacy", type="tertiary", width="content")
        with conversations:
            try:
                summary = conversation_summary(owner)
            except Exception:
                st.error("Your saved conversations are temporarily unavailable. Please try again shortly.")
                return
            count, subjects = summary["conversations"], summary["curricula"]
            st.html(f'''<div class="ini-settings-summary">
              <div class="ini-settings-stat">{count}<div class="ini-settings-stat-label">Saved conversations</div></div>
              <div class="ini-settings-stat">{subjects}<div class="ini-settings-stat-label">Subject curricula</div></div></div>''')
            with st.container(key="ini_settings_export_section"):
                st.html('''<div class="ini-settings-section-title">Keep a copy</div>
                  <div class="ini-settings-copy">Download your saved conversations and subject learning as a JSON file.</div>''')
                if st.button("Prepare export", icon=":material/download:", width="content",
                             key="ini_settings_prepare", disabled=not (count or subjects)):
                    if _current_owner(expected_owner) != owner:
                        st.error("Your account changed. Close Settings and sign in again.")
                        return
                    try:
                        data = export_conversations(owner)
                    except Exception:
                        st.error("The export could not be prepared. Please try again.")
                    else:
                        st.session_state["_ini_settings_export"] = {"owner": owner, "data": data}
                prepared = st.session_state.get("_ini_settings_export")
                if prepared and prepared.get("owner") == owner:
                    st.download_button("Download JSON", data=prepared["data"],
                                       file_name=f"ini-chats-{datetime.now(timezone.utc):%Y-%m-%d}.json",
                                       mime="application/json", on_click="ignore", icon=":material/file_download:",
                                       width="content", key="ini_settings_download")
                    st.caption("Your export is ready. Keep downloaded copies somewhere private.")
                elif not (count or subjects):
                    st.caption("Your conversations will appear here after you start a chat.")
            with st.container(key="ini_settings_danger"):
                with st.expander("Delete all conversations", icon=":material/delete_outline:"):
                    st.caption("Permanently delete your saved conversations and subject curricula from InI. This cannot be undone. Your Google account is unaffected.")
                    confirmation = st.text_input("Type DELETE to confirm", placeholder="DELETE",
                                                 key="ini_settings_delete_phrase")
                    if st.button("Permanently delete", type="primary", icon=":material/delete_forever:",
                                 width="content", key="ini_settings_confirm_delete",
                                 disabled=confirmation.strip() != "DELETE" or not (count or subjects)):
                        if _current_owner(expected_owner) != owner:
                            st.error("Your account changed. Nothing was deleted.")
                            return
                        try:
                            delete_all_conversations(owner)
                        except Exception:
                            st.error("Your conversations could not be deleted. Please try again.")
                            return
                        (on_deleted or _after_delete)(owner)


@st.dialog("Settings", width="medium")
def _settings_dialog(expected_owner: str) -> None:
    render_settings_content(expected_owner)


def show_account_settings() -> None:
    owner = _current_owner()
    if owner is None:
        st.error("Please sign in again to manage your account.")
        return
    st.session_state.pop("_ini_settings_export", None)
    st.session_state.pop("ini_settings_delete_phrase", None)
    _settings_dialog(owner)
