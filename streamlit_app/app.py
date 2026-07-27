import os
import sys
import time
import re
import secrets
import base64
from contextlib import nullcontext
from html import escape
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode
from pathlib import Path

# Streamlit Cloud launches this file from ``streamlit_app/``. Add the
# repository root explicitly so sibling application packages such as ``api``
# resolve identically in local and hosted environments.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st
import streamlit.components.v1 as components
from storage_sqlite import (
    init_db,
    save_session,
    list_sessions,
    load_session,
    delete_session,
    rename_session,
)
from time_utils import browser_local_now
from topic_profile import (
    extract_continue_journey,
    extract_core_explanation,
    extract_learning_paths,
    extract_learning_loop,
    extract_topic_profile,
    extract_your_question,
    split_prerequisite_items,
    split_prerequisites,
)
from response_profile import build_response_profile
# Product knowledge was introduced after the original Streamlit entry point.
# Keep startup resilient while a deployment rolls between revisions: an older
# checkout must still render instead of failing before the first frame.
try:
    from api.product_knowledge import answer_ini_product_query
except ModuleNotFoundError as exc:
    if exc.name != "api.product_knowledge":
        raise

    def answer_ini_product_query(
        text: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        return None

try:
    from api.context_resolution import find_contextual_topic_match
except ModuleNotFoundError as exc:
    if exc.name != "api.context_resolution":
        raise

    def find_contextual_topic_match(
        query: str,
        candidates: Iterable[str],
    ) -> Optional[Dict[str, object]]:
        return None

from api.interrogate import extract_topic as extract_learning_topic
from api.capability_boundary import assess_capability
from api.conversation_interpreter import interpret_turn
from fce_content import FCE_MESSAGES, FCE_QUOTES, FCE_TOPIC_EXAMPLES
from fce_component import render_fce



# Try autorefresh (for live clock). If not installed, app still runs.
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:
    st_autorefresh = None


# =========================
# Config
# =========================
DEFAULT_API_BASE = os.environ.get("INI_API_BASE", "http://127.0.0.1:8000")
DEV_MODE = os.environ.get("INI_DEV_MODE", "0") == "1"


# =========================
# Page Setup
# =========================
st.set_page_config(page_title="InI.ai", layout="wide", initial_sidebar_state="expanded")

visitor_param = st.query_params.get("visitor")
if isinstance(visitor_param, list):
    visitor_param = visitor_param[-1] if visitor_param else ""

visitor_id = str(visitor_param or "").strip()
if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", visitor_id):
    visitor_id = secrets.token_urlsafe(24)
    st.query_params["visitor"] = visitor_id

st.session_state.visitor_id = visitor_id

CSS = """
<style>
:root{
  --muted:#6b7280;
  --card:#ffffff;
  --stroke:#e5e7eb;
  --soft:#f8fafc;
  --ink:#0f172a;

  --bubbleUser:#eef2ff;
  --bubbleAsst:#ffffff;

  --litOver:#e0e7ff;
  --litQuiz:#ede9fe;
}

/* Material icons removed to prevent stray keyboard_double_arrow_right text rendering */

html, body{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
  color: var(--ink);
}
button, input, textarea, select, label, p, div, a{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
}

span{
  font-family: inherit;
}

/*
 * Script-only st.iframe bridges are rendered at one pixel high. Streamlit can
 * expose that pixel as a stray horizontal speck near the first query. Keep the
 * scripts active while removing their invisible host frames from page layout.
 */
[data-testid="stElementContainer"]:has(iframe[data-testid="stIFrame"][title="st.iframe"]){
  position: absolute !important;
  width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  pointer-events: none !important;
}

iframe[data-testid="stIFrame"][title="st.iframe"]{
  position: absolute !important;
  width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  border: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* Sidebar collapse icon: replace broken ligature text with a clean arrow */
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]{
  font-size: 0 !important;
  line-height: 1 !important;
  color: transparent !important;
  position: relative !important;
  display: inline-block !important;
  width: 1.5rem !important;
  height: 1.5rem !important;
}

[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before{
  content: "❮" !important;
  font-size: 1.15rem !important;
  line-height: 1.5rem !important;
  color: rgba(49, 51, 63, 0.6) !important;
  position: absolute !important;
  inset: 0 !important;
  text-align: center !important;
}

[data-testid="stSidebarCollapseButton"]{
  min-width: 2rem !important;
  min-height: 2rem !important;
}

.main .block-container{
  max-width: 980px;
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
}

/* --- Sidebar clock tile --- */
.clock_tile{
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.17);
  border-radius: 14px;
  background: var(--card);
  padding: 10px 10px;
  margin: 10px 0 12px 0;
  box-shadow:
    0 10px 26px rgba(15, 23, 42, 0.055),
    0 2px 7px rgba(15, 23, 42, 0.035);
}
.clock_center{
  display:flex;
  align-items:center;
  justify-content:center;
  gap: 8px;
  margin-top: 2px;
}
.clock_time{
  font-size: 36px;
  font-weight: 750;
  line-height: 1;
  letter-spacing: 0.5px;
}
.clock_ampm{
  font-size: 13px;
  font-weight: 650;
  color: var(--muted);
  margin-top: 12px;
}
.clock_row_bottom{
  display:flex;
  gap: 8px;
  margin-top: 10px;
}
.clock_box{
  flex:1;
  border: 1px solid var(--stroke);
  border-radius: 10px;
  background: var(--soft);
  padding: 6px 8px;
  text-align:center;
  font-size: 13px;
  font-weight: 650;
  color: var(--ink);
}

.badge{
  display:inline-block;
  padding: 3px 10px;
  border-radius:999px;
  font-size:12px;
  border:1px solid rgba(148, 163, 184, 0.16);
  background:rgba(248, 250, 252, 0.68);
  box-shadow:
    0 5px 14px rgba(15, 23, 42, 0.045),
    0 1px 3px rgba(15, 23, 42, 0.025);
}
.small{ font-size: 12px; }
.bigtitle{ font-size: 30px; font-weight: 750; margin: 0 0 12px 0; }

div[data-testid="stSidebar"] .block-container{
  padding-top: 1rem;
}

/* Sidebar navigation: clean text rows without button/card chrome. */
.ini-sidebar-nav{
  display:flex;
  flex-direction:column;
  gap:2px;
  margin-top:7px;
}
.ini-sidebar-nav-card{
  display:flex;
  align-items:center;
  min-height:38px;
  padding:8px 4px;
  border:0;
  border-radius:8px;
  background:transparent;
  color:var(--ink) !important;
  font-size:13px;
  font-weight:650;
  line-height:1.25;
  text-decoration:none !important;
  box-shadow:none;
  transition:background 160ms ease, color 160ms ease;
}
.ini-sidebar-nav-card:hover{
  background:rgba(15,23,42,.035);
  text-decoration:none !important;
}
.ini-sidebar-nav-card.is-active{
  background:transparent;
  font-weight:760;
}

/* Prevent Continue wrapping */
button[kind="secondary"]{
  min-width: 110px !important;
}

/* =========================
   UIB capsule (stable)
   ========================= */
.ini_uib_wrap{ margin-top: 120px; }
.ini_uib_outer{
  display:flex;
  justify-content:center;
  width:100%;
}
.ini_uib_capsule{
  width: min(980px, 100%);
  border: 1px solid var(--stroke);
  background: #fff;
  border-radius: 999px;
  padding: 14px 18px;
}
.ini_uib_capsule [data-testid="stHorizontalBlock"]{
  flex-wrap: nowrap !important;
  align-items:center !important;
}
.ini_uib_capsule [data-testid="column"]{
  min-width: 0 !important;
}
.ini_uib_capsule div[data-testid="stTextInput"] input{
  border-radius: 999px !important;
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}
.ini_uib_capsule [data-testid="column"]:nth-child(2) button,
.ini_uib_capsule [data-testid="column"]:nth-child(3) button,
.ini_uib_capsule [data-testid="column"]:nth-child(4) button{
  border-radius: 999px !important;
  width: 40px !important;
  height: 40px !important;
  padding: 0 !important;
  border: 1px solid var(--stroke) !important;
  background: #fff !important;
  font-weight: 900 !important;
}
.ini_lit_over .ini_uib_capsule [data-testid="column"]:nth-child(2) button{
  background: var(--litOver) !important;
  border-color: #c7d2fe !important;
}
.ini_lit_quiz .ini_uib_capsule [data-testid="column"]:nth-child(3) button{
  background: var(--litQuiz) !important;
  border-color: #ddd6fe !important;
}
.ini_hint{
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted);
  padding-left: 10px;
  display:flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  line-height: 1.2;
}
.ini_hint b{ color: var(--ink); }

.ini_session_row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:8px;
  margin: 2px 0 6px 0;
}

.ini_session_menu{
  position:relative;
  min-width:18px;
  text-align:right;
  opacity:0;
  transition:opacity 0.15s ease;
}

.ini_session_row:hover .ini_session_menu{
  opacity:1;
}

.ini_session_menu details{
  position:relative;
}

.ini_session_menu summary{
  list-style:none;
  cursor:pointer;
  color:#9aa0a6;
  font-size:18px;
  line-height:1;
  user-select:none;
}

.ini_session_menu summary::-webkit-details-marker{
  display:none;
}

.ini_session_dropdown{
  position:absolute;
  right:0;
  top:20px;
  min-width:90px;
  background:#fff;
  border:1px solid var(--stroke);
  border-radius:10px;
  box-shadow:0 8px 24px rgba(15,23,42,0.08);
  padding:6px 0;
  z-index:999;
}

.ini_session_dropdown a{
  display:block;
  padding:7px 10px;
  text-decoration:none !important;
  color:var(--ink) !important;
  font-size:13px;
}

.ini_session_dropdown a:hover{
  background:#f8fafc;
}

/* Make chat look cleaner */
.stChatMessage{
  padding-top: 0.25rem !important;
  padding-bottom: 0.25rem !important;
}
.stChatMessage .stMarkdown{
  line-height: 1.38;
}

/* Follow-up / session links */
.ini_plain_link{
  display:block;
  text-decoration:none !important;
  color: var(--ink) !important;
  text-align:left !important;
  margin: 6px 0;
  line-height: 1.55;
  border:none !important;
  outline:none !important;
  background:transparent !important;
  padding:0 !important;
  font-size: 0.95rem;
}
.ini_plain_link:hover{
  text-decoration:none !important;
}
.ini_sidebar_link{
  display:block;
  text-decoration:none !important;
  color: var(--ink) !important;
  text-align:left !important;
  padding: 6px 0;
  line-height: 1.4;
}
.ini_sidebar_link:hover{
  text-decoration:none !important;
}
.ini_popup_section{
  margin-top: 8px;
}

/* Responsive */
@media (max-width: 720px){
  html,
  body,
  [data-testid="stApp"],
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"]{
    width: 100% !important;
    max-width: 100vw !important;
    overflow-x: clip !important;
  }

  /* Keep mobile navigation compact without covering the entire display. */
  [data-testid="stSidebar"][aria-expanded="true"]{
    position: fixed !important;
    inset: 0 auto 0 0 !important;
    z-index: 2147482000 !important;
    width: min(70vw, 320px) !important;
    min-width: 0 !important;
    max-width: 320px !important;
    height: 100dvh !important;
    transform: none !important;
    background: #f5f6f8 !important;
    border-right: 1px solid rgba(15, 23, 42, 0.08) !important;
    box-shadow: 18px 0 42px rgba(15, 23, 42, 0.14) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
  }

  [data-testid="stSidebar"][aria-expanded="true"] .block-container{
    width: 100% !important;
    max-width: none !important;
    margin-inline: 0 !important;
    padding-inline: 18px !important;
  }

  [data-testid="stSidebar"][aria-expanded="true"]
  [data-testid="stSidebarCollapseButton"]{
    position: absolute !important;
    top: 12px !important;
    right: 12px !important;
    z-index: 2147482001 !important;
  }

  .main .block-container{ padding-left: 1rem; padding-right: 1rem; }
  .ini_uib_capsule{ padding: 10px 10px; }
  .ini_uib_capsule [data-testid="stHorizontalBlock"]{
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  .ini_uib_capsule [data-testid="column"]:nth-child(1){
    flex: 1 1 100% !important;
  }
  .ini_uib_capsule [data-testid="column"]:nth-child(2),
  .ini_uib_capsule [data-testid="column"]:nth-child(3),
  .ini_uib_capsule [data-testid="column"]:nth-child(4){
    flex: 0 0 auto !important;
  }
}

/* Preserve Streamlit material icon fonts */

/* Keep custom expander arrows */
.stExpander summary::before {
  content: "➤";
  display: inline-block;
  margin-right: 6px;
  font-size: 15px;
}

.stExpander details[open] > summary::before {
  content: "▼";
}


div[data-testid="stVerticalBlockBorderWrapper"]{
  background:linear-gradient(180deg, #ffffff 0%, #fbfcff 100%) !important;
  border:1px solid #eceff4 !important;
  border-radius:18px !important;
  padding:18px !important;
  margin:14px 0 20px 0 !important;
  box-shadow:0 12px 32px rgba(15,23,42,0.055) !important;
  overflow:hidden !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] > div{
  background:#ffffff !important;
}

/* Interrogate question mini wrappers */
div.stButton > button {
  width:100% !important;
  text-align:left !important;
  justify-content:flex-start !important;
  white-space:normal !important;
  height:auto !important;
  line-height:1.45 !important;
  padding:12px 14px !important;
  margin:5px 0 !important;

  background:#ffffff !important;
  color:#111827 !important;
  border:1px solid #e5e7eb !important;
  border-radius:14px !important;
  box-shadow:0 1px 4px rgba(15,23,42,0.05) !important;
}

/* Hover polish */
div.stButton > button:hover {
  background:#f8fafc !important;
  border-color:#d1d5db !important;
}

.ini-topic-profile {
  margin: 12px 0 20px;
  padding: 18px;
  border: 1px solid #eceff4;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.055);
}
.ini-topic-profile__title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: #f51b3f;
  font-size: 13px;
  font-weight: 800;
}
.ini-topic-profile__mark {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #fff1f4;
  border: 1px solid #ffd0da;
  box-shadow: inset 0 0 0 5px #f51b3f;
}
.ini-topic-profile__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.ini-topic-profile__item {
  min-height: 74px;
  padding: 13px 14px;
  border: 1px solid #f0f2f6;
  border-radius: 14px;
  background: #f7f8fa;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.035);
}
.ini-topic-profile__label {
  margin-bottom: 6px;
  color: #7b8493;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
.ini-topic-profile__value {
  color: #17211f;
  font-size: 14px;
  line-height: 1.4;
}
.ini-nc-prerequisites-panel {
  padding: 18px 18px 17px;
  border-color: #e9edf3;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
}
.ini-nc-prerequisites-panel .ini-topic-profile__title {
  margin-bottom: 11px;
  color: #17211f;
}
.ini-nc-prerequisites-panel__content {
  padding: 2px 0 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #3f4858;
  font-size: 14px;
  line-height: 1.55;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.025);
}
.ini-topic-profile.ini-conversation-profile {
  height: 100%;
  min-height: 176px;
  margin: 0;
  padding: 14px;
  border-radius: 16px;
  box-shadow: 0 9px 24px rgba(15, 23, 42, 0.045);
}
.ini-conversation-profile .ini-topic-profile__title {
  margin-bottom: 10px;
  color: #17211f;
  font-size: 12px;
}
.ini-conversation-profile .ini-topic-profile__grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
}
.ini-conversation-profile .ini-topic-profile__item {
  min-height: 58px;
  padding: 9px 10px;
  border-radius: 11px;
  box-shadow: none;
}
.ini-conversation-profile .ini-topic-profile__item:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}
.ini-conversation-profile .ini-topic-profile__label {
  margin-bottom: 3px;
  font-size: 8px;
}
.ini-conversation-profile .ini-topic-profile__value {
  font-size: 11px;
  line-height: 1.3;
}
@media (max-width: 700px) {
  .ini-topic-profile__grid { grid-template-columns: 1fr; }
  .ini-conversation-profile .ini-topic-profile__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.ini-nc-section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0 10px;
  color: #111827;
  font-size: 17px;
  font-weight: 850;
  letter-spacing: 0;
}
.ini-nc-section-title__mark {
  width: 25px;
  height: 25px;
  border-radius: 10px;
  background: #fff1f4;
  border: 1px solid #ffd0da;
  position: relative;
}
.ini-nc-section-title__mark::after {
  content: "";
  position: absolute;
  inset: 7px;
  border-radius: 999px;
  background: #f51b3f;
}
.ini-nc-section-subtitle {
  margin: -3px 0 14px 35px;
  color: #667085;
  font-size: 13px;
  line-height: 1.45;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-section-title) {
  position: relative !important;
  margin: 16px 0 22px !important;
  padding: 20px !important;
  border: 1px solid #e8ebf1 !important;
  border-radius: 20px !important;
  background: linear-gradient(145deg, #ffffff 0%, #fbfcff 72%, #fff7f8 100%) !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.065) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-section-title)::before {
  content: "";
  position: absolute;
  top: 0;
  left: 20px;
  right: 20px;
  height: 3px;
  border-radius: 0 0 99px 99px;
  background: linear-gradient(90deg, #f51b3f 0%, #ff8ba0 42%, rgba(255, 139, 160, 0) 82%);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-section-title) > div {
  background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-section-title) .ini-nc-section-title {
  margin-top: 0;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-section-title) .ini-nc-section-subtitle {
  padding-bottom: 12px;
  border-bottom: 1px solid #eef0f4;
}
.ini-nc-section-title {
  width: fit-content;
  padding: 7px 11px;
  border: 1px solid #ffd4dd;
  border-radius: 12px;
  background: #fff4f6;
  color: #f51b3f;
  font-size: 14px;
  font-weight: 850;
}
.ini-nc-section-title__mark {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  box-shadow: inset 0 0 0 4px #f51b3f;
}
.ini-nc-section-title__mark::after {
  display: none;
}
.ini-nc-section-subtitle {
  margin-left: 30px;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-section-title) [data-testid="stMarkdownContainer"] > p {
  color: #3f4858;
  line-height: 1.65;
}
.ini-nc-intro-copy {
  margin: 0;
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  color: #17211f;
  font-size: 14px;
  line-height: 1.55;
}
.ini-nc-prerequisites-list {
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 30px;
  row-gap: 9px;
  list-style: none;
}
.ini-nc-prerequisites-list li {
  position: relative;
  margin: 0;
  padding-left: 16px;
  color: #3f4858;
  line-height: 1.5;
}
.ini-nc-prerequisites-list li::before {
  position: absolute;
  top: 0.64em;
  left: 1px;
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: #9aa5b5;
  content: "";
}
@media (max-width: 700px) {
  .ini-nc-prerequisites-list {
    grid-template-columns: 1fr;
  }
}
.ini-nc-intro-copy p {
  margin: 0 0 10px;
}
.ini-nc-intro-copy p:last-child {
  margin-bottom: 0;
}
.ini-nc-followup-panel .ini-topic-profile__grid {
  display: flex;
  flex-direction: column;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
}
a.ini-nc-followup-panel__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 0;
  max-width: min(100%, 560px);
  padding: 10px 13px;
  border: 1px solid #f0f2f6;
  border-radius: 999px;
  background: #f7f8fa;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.035);
  color: #17211f !important;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.45;
  text-decoration: none !important;
}
a.ini-nc-followup-panel__item:hover {
  border-color: #d9dee7;
  background: #fbfcff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
}
.ini-nc-followup-panel__arrow {
  flex: 0 0 auto;
  margin-left: 14px;
  color: #667085;
  font-size: 16px;
}
.ini-nc-learning-paths {
  padding: 18px;
}
.ini-nc-your-question {
  padding: 20px 22px;
}
.ini-nc-your-question__prompt {
  margin: 2px 0 18px;
  color: #172033;
  font-size: clamp(17px, 1.35vw, 21px);
  font-weight: 550;
  line-height: 1.48;
  letter-spacing: -0.012em;
}
.ini-nc-your-question__insight {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  padding-top: 15px;
  border-top: 1px solid #f0f2f5;
}
.ini-nc-your-question__label {
  margin-bottom: 5px;
  color: #7b8493;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}
.ini-nc-your-question__value {
  color: #465164;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.55;
}
.ini-nc-core-explanation {
  padding: 20px 22px 54px;
}
.ini-nc-core-explanation__overview {
  margin: 0 0 17px;
  color: #3f4858;
  font-size: 14px;
  line-height: 1.62;
}
.ini-nc-core-explanation__rule {
  margin: 0 0 18px 20px;
  color: #172033;
  font-family: "Cambria Math", "STIX Two Math", Georgia, serif;
  font-size: clamp(18px, 1.45vw, 22px);
  font-weight: 700;
  line-height: 1.45;
}
.ini-nc-core-explanation__variables {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px 28px;
  margin: 0 0 20px 20px;
}
.ini-nc-core-explanation__variable {
  color: #566173;
  font-size: 13px;
  line-height: 1.5;
}
.ini-nc-core-explanation__variable strong {
  color: #222d3d;
  font-weight: 750;
}
.ini-nc-core-explanation__steps {
  display: flex;
  flex-direction: column;
  gap: 13px;
  margin-left: 20px;
}
.ini-nc-core-explanation__step {
  padding-left: 15px;
  border-left: 2px solid #edf0f4;
  color: #465164;
  font-size: 14px;
  line-height: 1.58;
}
.ini-nc-core-explanation__step strong,
.ini-nc-core-explanation__insight strong,
.ini-nc-core-explanation__example strong {
  color: #202b3a;
  font-weight: 750;
}
.ini-nc-core-explanation__insight,
.ini-nc-core-explanation__example {
  margin: 18px 0 0 20px;
  color: #465164;
  font-size: 14px;
  line-height: 1.6;
}
.ini-nc-learning-loop {
  padding: 20px 22px;
}
.ini-nc-learning-loop__track {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px 34px;
  margin-top: 3px;
}
.ini-nc-learning-loop__stage {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  min-width: 0;
}
.ini-nc-learning-loop__stage::after {
  position: absolute;
  top: 7px;
  right: -23px;
  color: #c3cad4;
  font-size: 15px;
  content: "→";
}
.ini-nc-learning-loop__stage:nth-child(3n)::after,
.ini-nc-learning-loop__stage:last-child::after {
  display: none;
}
.ini-nc-learning-loop__number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid #e3e7ed;
  border-radius: 50%;
  background: #f8f9fb;
  color: #394456;
  font-size: 11px;
  font-weight: 750;
}
.ini-nc-learning-loop__heading {
  margin: 1px 0 4px;
  color: #202b3a;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.35;
}
.ini-nc-learning-loop__copy {
  color: #5a6576;
  font-size: 13px;
  line-height: 1.48;
}
.ini-nc-learning-loop__outcome {
  margin: 19px 0 0 40px;
  color: #465164;
  font-size: 13px;
  line-height: 1.55;
}
.ini-nc-learning-loop__outcome strong {
  color: #202b3a;
  font-weight: 750;
}
.ini-nc-continue-journey {
  padding: 21px 22px 20px;
}
.ini-nc-continue-journey__path {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin-top: 3px;
}
.ini-nc-continue-journey__direction {
  position: relative;
  min-width: 0;
  padding: 2px 24px 3px;
}
.ini-nc-continue-journey__direction:first-child {
  padding-left: 0;
}
.ini-nc-continue-journey__direction:last-child {
  padding-right: 0;
}
.ini-nc-continue-journey__direction + .ini-nc-continue-journey__direction {
  border-left: 1px solid #edf0f4;
}
.ini-nc-continue-journey__number {
  display: block;
  margin-bottom: 7px;
  color: #d91639;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
}
.ini-nc-continue-journey__heading {
  margin-bottom: 6px;
  color: #202b3a;
  font-size: 14px;
  font-weight: 750;
  line-height: 1.38;
}
.ini-nc-continue-journey__copy {
  color: #5a6576;
  font-size: 13px;
  line-height: 1.55;
}
.ini-nc-continue-journey__destination {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #f0f2f5;
  color: #465164;
  font-size: 13px;
  line-height: 1.58;
}
.ini-nc-continue-journey__destination strong {
  color: #202b3a;
  font-weight: 750;
}
div[class*="st-key-nc_core_explanation_more_"] {
  position: relative;
  z-index: 1;
  width: fit-content;
  margin: -51px 0 17px 22px;
}
div[class*="st-key-nc_core_explanation_more_"] button {
  min-height: 0 !important;
  padding: 2px 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #d91639 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}
div[class*="st-key-nc_core_explanation_more_"] button:hover {
  color: #a90f2d !important;
  text-decoration: underline;
}
@media (max-width: 700px) {
  .ini-nc-your-question__insight {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .ini-nc-core-explanation__variables {
    grid-template-columns: 1fr;
  }
  .ini-nc-core-explanation__rule,
  .ini-nc-core-explanation__variables,
  .ini-nc-core-explanation__steps,
  .ini-nc-core-explanation__insight,
  .ini-nc-core-explanation__example {
    margin-left: 10px;
  }
  .ini-nc-learning-loop__track {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .ini-nc-learning-loop__stage::after {
    top: auto;
    right: auto;
    bottom: -15px;
    left: 8px;
    content: "↓";
  }
  .ini-nc-learning-loop__stage:nth-child(3n)::after {
    display: block;
  }
  .ini-nc-learning-loop__stage:last-child::after {
    display: none;
  }
  .ini-nc-learning-loop__outcome {
    margin-left: 36px;
  }
  .ini-nc-continue-journey__path {
    grid-template-columns: 1fr;
    gap: 15px;
  }
  .ini-nc-continue-journey__direction,
  .ini-nc-continue-journey__direction:first-child,
  .ini-nc-continue-journey__direction:last-child {
    padding: 0 0 15px;
  }
  .ini-nc-continue-journey__direction + .ini-nc-continue-journey__direction {
    padding-top: 15px;
    border-top: 1px solid #edf0f4;
    border-left: 0;
  }
}
.ini-nc-learning-paths__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px 34px;
}
.ini-nc-learning-paths__group {
  min-width: 0;
}
.ini-nc-learning-paths__heading {
  margin: 0 0 8px;
  color: #263142;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}
.ini-nc-learning-paths__list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.ini-nc-learning-paths__list li {
  position: relative;
  margin: 0 0 7px;
  padding-left: 15px;
  color: #465164;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.48;
}
.ini-nc-learning-paths__list li:last-child {
  margin-bottom: 0;
}
.ini-nc-learning-paths__list li::before {
  position: absolute;
  top: 0.65em;
  left: 1px;
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: #9aa5b5;
  content: "";
}
@media (max-width: 700px) {
  .ini-nc-learning-paths__grid {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker) {
  position: relative !important;
  margin: 12px 0 20px !important;
  padding: 18px !important;
  border: 1px solid #eceff4 !important;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.055) !important;
}
.st-key-root_response_card,
div[class*="st-key-branch_response_card_"]:not([class*="_row"]):not([class*="_clarification_cta_"]) {
  width: min(1180px, 100%) !important;
  margin: 0 !important;
  padding: 18px !important;
  border: 0 !important;
  border-radius: 20px !important;
  background: #ffffff !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.045) !important;
}
.st-key-root_response_card > div,
div[class*="st-key-branch_response_card_"]:not([class*="_row"]):not([class*="_clarification_cta_"]) > div {
  background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-carm-response-surface) {
  border: 0 !important;
  background:
    radial-gradient(circle at 8% 0%, rgba(245, 27, 63, 0.035), transparent 28%),
    #ffffff !important;
  box-shadow:
    0 22px 52px rgba(15, 23, 42, 0.075),
    0 2px 7px rgba(15, 23, 42, 0.035) !important;
}
.ini-carm-response-surface {
  display: none;
}
div[class*="st-key-root_response_card_row"],
div[class*="st-key-branch_response_card_"][class*="_row"] {
  width: min(1220px, 100%) !important;
  margin: 14px 0 20px !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  align-items: flex-start !important;
  gap: 10px !important;
}
.ini-response-avatar {
  width: 18px !important;
  height: 30px !important;
  min-width: 18px !important;
  max-width: 18px !important;
  object-fit: contain;
  display: block;
  margin: 18px 0 0 1px;
  filter: drop-shadow(0 3px 7px rgba(245, 27, 63, 0.16));
}
.ini-qmap-avatar-anchor {
  position: relative;
  height: 0;
  overflow: visible;
  z-index: 3;
}
.ini-qmap-avatar-anchor img {
  position: absolute;
  top: 18px;
  left: -27px;
  width: 18px !important;
  height: 30px !important;
  max-width: 18px !important;
  object-fit: contain;
  filter: drop-shadow(0 3px 7px rgba(245, 27, 63, 0.16));
}
@media (max-width: 700px) {
  .ini-qmap-avatar-anchor img {
    left: 2px;
  }
  .st-key-root_response_card,
  div[class*="st-key-branch_response_card_"]:not([class*="_row"]):not([class*="_clarification_cta_"]) {
    width: calc(100% - 28px) !important;
    margin-left: 28px !important;
  }
}
.ini-casual-response-copy {
  display: none;
}
div[data-testid="stColumn"]:has(.ini-casual-response-copy) {
  padding: 13px 10px 10px 3px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[data-testid="stColumn"]:has(.ini-casual-response-copy) p {
  margin: 0 !important;
  color: #273142 !important;
  font-size: 16px !important;
  line-height: 1.65 !important;
  font-weight: 400 !important;
}
div[class*="clarification_cta"] button {
  min-width: 150px !important;
  justify-content: flex-start !important;
  padding: 10px 15px !important;
  border: 1px solid #e3e7ed !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.085) !important;
  color: #273142 !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
  transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
}
div[class*="clarification_cta"] [data-testid="stElementContainer"],
div[class*="clarification_cta"] [data-testid="stButton"] {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}
div[class*="discussion_question_"] button {
  width: 100% !important;
  max-width: 100% !important;
  justify-content: flex-start !important;
  text-align: left !important;
  padding: 14px 16px !important;
  border: 0 !important;
  border-radius: 15px !important;
  background: #ffffff !important;
  color: #263142 !important;
  font-size: 15px !important;
  font-weight: 450 !important;
  box-shadow: 0 13px 30px rgba(15, 23, 42, 0.13) !important;
  transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
}
div[class*="discussion_question_"] button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 17px 38px rgba(15, 23, 42, 0.16) !important;
}
div[class*="discussion_question_"] button p {
  width: 100% !important;
  margin: 0 !important;
  text-align: left !important;
}
div[class*="discussion_question_"] button > div,
div[class*="discussion_question_"] button [data-testid="stMarkdownContainer"] {
  width: 100% !important;
  justify-content: flex-start !important;
  text-align: left !important;
}
div[class*="discussion_question_"] [data-testid="stElementContainer"],
div[class*="discussion_question_"] [data-testid="stButton"] {
  width: 100% !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.ini-discussion-question-inner {
  margin-bottom: 12px;
  padding: 13px 15px;
  border: 1px solid #e8ebf0;
  border-radius: 13px;
  background: #f7f8fa;
  color: #172033;
  font-size: 15px;
  line-height: 1.55;
}
div[class*="discussion_answer_card_"] {
  border: 1px solid #e7eaf0 !important;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.065) !important;
  padding: 18px !important;
}
div[class*="st-key-discussion_more_"] [data-testid="stElementContainer"],
div[class*="st-key-discussion_explain_"] [data-testid="stElementContainer"],
div[class*="st-key-discussion_previous_"] [data-testid="stElementContainer"],
div[class*="st-key-discussion_next_"] [data-testid="stElementContainer"],
div[class*="st-key-discussion_more_"] [data-testid="stButton"],
div[class*="st-key-discussion_explain_"] [data-testid="stButton"],
div[class*="st-key-discussion_previous_"] [data-testid="stButton"],
div[class*="st-key-discussion_next_"] [data-testid="stButton"] {
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[class*="st-key-discussion_more_"] button,
div[class*="st-key-discussion_explain_"] button,
div[class*="st-key-discussion_previous_"] button,
div[class*="st-key-discussion_next_"] button {
  min-width: 0 !important;
  width: auto !important;
  height: 36px !important;
  padding: 7px 13px !important;
  border: 1px solid #e1e5eb !important;
  border-radius: 11px !important;
  background: #ffffff !important;
  color: #465164 !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.065) !important;
  transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease !important;
}
div[class*="st-key-discussion_more_"] button:hover,
div[class*="st-key-discussion_explain_"] button:hover,
div[class*="st-key-discussion_previous_"] button:hover,
div[class*="st-key-discussion_next_"] button:hover {
  transform: translateY(-1px) !important;
  border-color: #cfd5de !important;
  color: #1f2937 !important;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.09) !important;
}
div[class*="clarification_cta"] button:hover {
  transform: translateY(-1px) !important;
  border-color: #cbd2dc !important;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.115) !important;
  color: #111827 !important;
}
div[class*="clarification_cta"] button:focus {
  box-shadow: 0 0 0 3px rgba(245, 27, 63, 0.10), 0 10px 25px rgba(15, 23, 42, 0.07) !important;
}
.st-key-root_question_map_panel,
div[class*="st-key-branch_question_map_panel_"] {
  background: #ffffff !important;
  border: 1px solid #eceff4 !important;
  border-radius: 18px !important;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.055) !important;
}
.st-key-root_question_map_content,
div[class*="st-key-branch_question_map_content_"] {
  margin-top: 2px;
  padding: 12px !important;
  border: 1px solid #edf0f4 !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.035) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker) > div {
  background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  [data-testid="stCheckbox"] {
  width: fit-content;
  margin: 0;
  padding: 7px 10px;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  background: #ffffff;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  [data-testid="stRadio"] {
  margin: 0 0 12px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  [data-testid="stRadio"] label input[type="radio"] {
  display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  [data-testid="stRadio"] div[role="radiogroup"] label:not(:has(input:checked)) {
  background: #f7f8fa !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
  border-color: #f51b3f !important;
  background: #f51b3f !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(245, 27, 63, 0.18) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
  color: #ffffff !important;
}
.st-key-root_question_map_content [data-testid="stRadio"] label input[type="radio"],
div[class*="st-key-branch_question_map_content_"] [data-testid="stRadio"] label input[type="radio"] {
  display: none !important;
}
.st-key-root_question_map_content [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked),
div[class*="st-key-branch_question_map_content_"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
  border-color: #f51b3f !important;
  background: #f51b3f !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(245, 27, 63, 0.18) !important;
}
.st-key-root_question_map_content [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p,
div[class*="st-key-branch_question_map_content_"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
  color: #ffffff !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  div.stButton > button {
  margin: 7px 0 !important;
  padding: 14px 15px !important;
  font-size: 14px !important;
  border-color: transparent !important;
  box-shadow: 0 15px 38px rgba(15, 23, 42, 0.10), 0 3px 10px rgba(15, 23, 42, 0.035) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-marker)
  .ini-nc-qmap-marker {
  min-height: 34px;
  margin: 0;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-answer-marker) {
  margin: 8px 0 6px !important;
  padding: 0 !important;
  border: 1px solid rgba(226, 232, 240, 0.28) !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 15px 38px rgba(15, 23, 42, 0.10), 0 3px 10px rgba(15, 23, 42, 0.035) !important;
  transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-answer-marker):hover {
  border-color: rgba(226, 232, 240, 0.38) !important;
  background: #fafbfc !important;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.12), 0 4px 12px rgba(15, 23, 42, 0.04) !important;
}
div[class*="st-key-qmap_answer_card_"] {
  margin: 8px 0 6px !important;
  padding: 0 !important;
  border: 1px solid rgba(226, 232, 240, 0.28) !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 15px 38px rgba(15, 23, 42, 0.10), 0 3px 10px rgba(15, 23, 42, 0.035) !important;
  transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
}
div[class*="st-key-qmap_answer_card_"]:hover {
  border-color: rgba(226, 232, 240, 0.38) !important;
  background: #fafbfc !important;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.12), 0 4px 12px rgba(15, 23, 42, 0.04) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-answer-marker) > div,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-answer-marker) .ini_ai_inner,
div[class*="st-key-qmap_answer_card_"] > div,
div[class*="st-key-qmap_answer_card_"] .ini_ai_inner {
  background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-answer-marker) .ini_ai_inner {
  padding: 16px 18px 14px !important;
}
div[class*="st-key-qmap_answer_card_"] [data-testid="stMarkdownContainer"] {
  padding: 14px 16px !important;
  color: #3f4858 !important;
  font-size: 15px !important;
  line-height: 1.6 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ini-nc-qmap-answer-marker) .ini_ai_inner h4 {
  margin: 0 0 10px !important;
  color: #17211f !important;
  font-size: 13px !important;
  font-weight: 750 !important;
}
div[class*="st-key-qmap_answer_card_"] [data-testid="stMarkdownContainer"] h4 {
  margin: 0 0 8px !important;
  color: #17211f !important;
  font-size: 14px !important;
  font-weight: 650 !important;
}
div[class*="st-key-qmap_answer_card_"] [data-testid="stMarkdownContainer"] p {
  margin: 0 0 10px !important;
}
.ini-nc-qmap-answer-marker {
  display: none !important;
}
.ini_ai_inner {
  background: #ffffff;
  border-radius: 18px;
  padding: 14px 16px 10px;
  animation: fadeIn 0.18s ease;
  line-height: 1.65;
}
.ini_ai_inner ul,
.ini_ai_inner ol {
  padding-left: 22px;
}
.ini_ai_inner li {
  margin-bottom: 6px;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.ini-topic-profile.ini-nc-intro-panel {
  padding-bottom: 52px;
}
.ini-nc-intro-panel .ini-topic-profile__title {
  color: #17211f;
}
.ini-nc-intro-panel .ini-topic-profile__mark {
  display: none;
}
.ini-topic-profile__title,
.ini-nc-section-title {
  gap: 0;
  color: #17211f;
}
.ini-topic-profile__mark,
.ini-nc-section-title__mark {
  display: none;
}
.ini-nc-section-title {
  width: auto;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
div[class*="st-key-nc_intro_more_button_"] {
  position: relative;
  z-index: 1;
  width: fit-content;
  margin: -54px 0 18px 18px;
}
div[class*="st-key-nc_intro_more_button_"] button {
  min-height: 0 !important;
  padding: 2px 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #d91639 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}
div[class*="st-key-nc_intro_more_button_"] button:hover {
  color: #a90f2d !important;
  text-decoration: underline;
}
.ini-nc-map-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0 16px;
}
.ini-nc-map-tab {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 7px 13px;
  border-radius: 999px;
  background: #f4f2f8;
  color: #283041;
  font-size: 12px;
  font-weight: 750;
}
.ini-nc-map-tab:first-child {
  background: linear-gradient(135deg, #f51b3f 0%, #6d35ff 100%);
  color: #ffffff;
  box-shadow: 0 8px 20px rgba(245, 27, 63, 0.2);
}
[data-testid="stRadio"] div[role="radiogroup"] {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
[data-testid="stRadio"] div[role="radiogroup"] label {
  min-height: 34px;
  margin: 0 !important;
  padding: 8px 14px !important;
  border: 1px solid #eceef4;
  border-radius: 999px;
  background: #f7f6fb;
  color: #283041;
  font-size: 12px;
  font-weight: 800;
  transition: background 120ms ease, color 120ms ease, border-color 120ms ease,
    box-shadow 120ms ease;
}
[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
  border-color: transparent;
  background: linear-gradient(135deg, #f51b3f 0%, #6d35ff 100%);
  color: #ffffff;
  box-shadow: 0 8px 20px rgba(245, 27, 63, 0.18);
}
[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {
  display: none !important;
}
[data-testid="stRadio"] div[role="radiogroup"] label p {
  margin: 0 !important;
  font-size: 12px !important;
  font-weight: 800 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stRadio"])
  [data-testid="stToggle"] label {
  gap: 8px !important;
  color: #667085 !important;
  font-size: 12px !important;
  font-weight: 750 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stRadio"])
  [data-testid="stToggle"] p {
  font-size: 12px !important;
  font-weight: 750 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stRadio"])
  [data-testid="stToggle"] button[role="switch"][aria-checked="true"] {
  background: #16a34a !important;
}
a.ini_nc_followup_link {
  display: inline-flex !important;
  align-items: center;
  margin: 6px 7px 6px 0 !important;
  padding: 10px 14px !important;
  border: 1px solid #eceef4 !important;
  border-radius: 999px !important;
  background: #f7f6fb !important;
  color: #172033 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
  text-decoration: none !important;
  box-shadow: 0 7px 18px rgba(15, 23, 42, 0.045) !important;
}
a.ini_nc_followup_link:hover {
  border-color: #ffc8d3 !important;
  background: #fff1f4 !important;
  color: #f51b3f !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stRadio"]) {
  background: linear-gradient(145deg, #ffffff 0%, #fbfcff 70%, #faf8ff 100%) !important;
}
.st-key-root_question_map_panel div.stButton > button,
div[class*="st-key-branch_question_map_panel_"] div.stButton > button {
  padding: 13px 15px !important;
  border-color: transparent !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 15px 38px rgba(15, 23, 42, 0.10), 0 3px 10px rgba(15, 23, 42, 0.035) !important;
}
.st-key-root_question_map_panel div.stButton > button:hover,
div[class*="st-key-branch_question_map_panel_"] div.stButton > button:hover {
  border-color: transparent !important;
  background: #f8fafc !important;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.12), 0 4px 12px rgba(15, 23, 42, 0.04) !important;
}
.st-key-root_question_map_content [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div > div:first-child,
div[class*="st-key-branch_question_map_content_"] [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div > div:first-child {
  display: none !important;
}
.st-key-root_question_map_content [data-testid="stRadio"] label[data-selected="true"],
div[class*="st-key-branch_question_map_content_"] [data-testid="stRadio"] label[data-selected="true"] {
  border-color: #f51b3f !important;
  background: #f51b3f !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(245, 27, 63, 0.18) !important;
}
.st-key-root_question_map_content [data-testid="stRadio"] label[data-selected="true"] p,
div[class*="st-key-branch_question_map_content_"] [data-testid="stRadio"] label[data-selected="true"] p {
  color: #ffffff !important;
}
.st-key-root_question_map_panel [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div > div:first-child,
div[class*="st-key-branch_question_map_panel_"] [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div > div:first-child {
  display: none !important;
}
.st-key-root_question_map_panel [data-testid="stRadio"] label[data-selected="true"],
div[class*="st-key-branch_question_map_panel_"] [data-testid="stRadio"] label[data-selected="true"] {
  border-color: #f51b3f !important;
  background: #f51b3f !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(245, 27, 63, 0.18) !important;
}
.st-key-root_question_map_panel [data-testid="stRadio"] label[data-selected="true"] p,
div[class*="st-key-branch_question_map_panel_"] [data-testid="stRadio"] label[data-selected="true"] p {
  color: #ffffff !important;
}

</style>
"""

init_db()

st.markdown(CSS, unsafe_allow_html=True)

# Load external styles.css (safe addition)
try:
    css_path = Path(__file__).parent / "styles.css"

    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True,
            )
except Exception:
    pass




# =========================
# Helpers
# =========================
def _user_now() -> datetime:
    try:
        timezone_offset = st.context.timezone_offset
    except Exception:
        timezone_offset = None
    return browser_local_now(timezone_offset)


def now_label() -> str:
    return _user_now().strftime("%a, %b %d • %I:%M %p")


def new_msg_id(prefix: str) -> str:
    return f"{prefix}-{time.time_ns()}"


def clock_parts() -> Dict[str, str]:
    now = _user_now()
    t = now.strftime("%I:%M").lstrip("0") or now.strftime("%I:%M")
    return {"time": t, "ampm": now.strftime("%p"), "date": now.strftime("%m/%d"), "dow": now.strftime("%a")}


def normalize_mojibake(s: str) -> str:
    if not s:
        return s
    replacements = {
        "â€”": "—", "â€“": "–", "â€™": "’", "â€œ": "“", "â€": "”", "â€¦": "…",
        "Â·": "·", "Â": "",
        "â": "—", "â": "–", "â": "’", "â": "“", "â": "”", "â¦": "…",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def normalize_whitespace_for_readability(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text or ""
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n[ \t]+\n", "\n\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"(?m)^\s*\d+\.\s*[A-Za-z]?\s*$\n?", "", s)
    return s.strip()


def session_title_for_sidebar(sess: Dict[str, Any]) -> str:
    first = (sess.get("last_prompt") or sess.get("title") or "Session").strip()
    kw = (first.split()[0] if first else "Session").strip().strip(".,:;!?").upper()
    created = sess.get("created") or _user_now().strftime("%b %d.%Y")
    return f"{kw}.{created}"


def needs_continue_flag(msg: Dict[str, Any]) -> bool:
    return bool(msg.get("incomplete"))


def mode_label(mode: str) -> str:
    m = (mode or "").strip().lower()
    if m == "high":
        return "Overview"
    if m == "quiz":
        return "Quiz"
    return "Deep"


def _strip_duplicate_chunk_prefix(chunk: str) -> str:
    if not chunk:
        return chunk

    lines = chunk.splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)

    bad_first_lines = {
        "definition",
        "definition —",
        "definition -",
        "overview",
        "introduction",
        "core mechanism",
        "why rag matters",
        "next steps",
    }

    changed = True
    while changed and lines:
        changed = False
        first = lines[0].strip().strip(":").lower()
        for bad in bad_first_lines:
            if first.startswith(bad):
                lines.pop(0)
                changed = True
                break
        while lines and not lines[0].strip():
            lines.pop(0)

    return "\n".join(lines).strip()


def truncate_session_text(text: str, max_chars: int = 28) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rstrip() + "..."


def _format_short_mmdd(created_at: str) -> str:
    s = (created_at or "").strip()
    if not s:
        return ""

    for fmt in ("%b %d.%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%m/%d")
        except Exception:
            pass

    return ""


def _query_href(**updates: Optional[str]) -> str:
    params: Dict[str, str] = {}
    for key, value in st.query_params.items():
        if isinstance(value, list):
            if value:
                params[key] = str(value[-1])
        elif value is not None:
            params[key] = str(value)

    for key, value in updates.items():
        if value is None or str(value).strip() == "":
            params.pop(key, None)
        else:
            params[key] = str(value)

    return "?" + urlencode(params)


def _private_href(**params: Optional[str]) -> str:
    values: Dict[str, str] = {
        "visitor": st.session_state.visitor_id,
    }
    for key, value in params.items():
        if value is not None and str(value).strip():
            values[key] = str(value)
    return "?" + urlencode(values)


def _reset_query_to_page(page: str) -> None:
    st.query_params.clear()
    st.query_params["visitor"] = st.session_state.visitor_id
    st.query_params["page"] = page


def _chat_popup_href(sid: str) -> str:
    return _query_href(popup_chat_sid=sid)


def _chat_root_href(sid: str) -> str:
    return _private_href(page="chat", chat_sid=sid)

def _chat_root_view_href(sid: str) -> str:
    return _private_href(page="chat", chat_sid=sid, chat_root="1")



def _chat_branch_href(sid: Optional[str], question: str) -> str:
    if sid:
        return _private_href(page="chat", chat_sid=sid, chat_q=question)
    return _private_href(page="chat", chat_q=question)


def _learn_session_href(sid: str) -> str:
    return _private_href(page="learn", learn_sid=sid)


def _learn_branch_href(sid: Optional[str], question: str) -> str:
    if sid:
        return _private_href(page="learn", learn_sid=sid, learn_q=question)
    return _private_href(page="learn", learn_q=question)


def _chat_rename_href(sid: str) -> str:
    return _private_href(
        page="chat",
        session_action="rename",
        session_sid=sid,
    )


def _chat_delete_href(sid: str) -> str:
    return _private_href(
        page="chat",
        session_action="delete",
        session_sid=sid,
    )


def _learn_rename_href(sid: str) -> str:
    return _private_href(
        page="learn",
        session_action="rename",
        session_sid=sid,
    )


def _learn_delete_href(sid: str) -> str:
    return _private_href(
        page="learn",
        session_action="delete",
        session_sid=sid,
    )



def clean_followup_text(text: str) -> str:
    s = (text or "").strip()

    # remove numbering already supplied by backend
    s = re.sub(r"^\(?\d+\)?[.)]?\s*", "", s)
    s = re.sub(r"^[•\-*]\s*", "", s)

    # remove wrapping quotes
    s = s.strip('"').strip("'")

    # collapse duplicate spaces
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def render_followup_links(
    page: str,
    followups: list[str],
    sid: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    cleaned: list[str] = []
    seen = set()

    for fu in followups or []:
        item = clean_followup_text(fu)
        key = re.sub(r"\s+", " ", item.lower()).strip()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)

    if not cleaned:
        return

    if target is None:
        target = "_blank" if page == "chat" else "_self"

    for idx, fu in enumerate(cleaned, start=1):
        if page == "chat":
            href = _chat_branch_href(sid, fu)
        else:
            href = _learn_branch_href(sid, fu)

        st.markdown(
            f'<a class="ini_plain_link" '
            f'href="{href}" '
            f'target="{target}" '
            f'style="display:block; cursor:pointer; color:#2563eb !important; margin:8px 0;">'
            f'{idx}. {fu} ↗'
            f'</a>',
            unsafe_allow_html=True,
        )


def render_followup_links(
    page: str,
    followups: list[str],
    sid: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    cleaned: list[str] = []
    seen = set()

    for fu in followups or []:
        item = clean_followup_text(fu)
        key = re.sub(r"\s+", " ", item.lower()).strip()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)

    if not cleaned:
        return

    if target is None:
        target = "_blank" if page == "chat" else "_self"

    for idx, fu in enumerate(cleaned, start=1):
        href = _chat_branch_href(sid, fu) if page == "chat" else _learn_branch_href(sid, fu)
        link_class = "ini_plain_link ini_nc_followup_link" if page == "chat" else "ini_plain_link"
        link_style = (
            "cursor:pointer;"
            if page == "chat"
            else "display:block; cursor:pointer; color:#2563eb !important; margin:8px 0;"
        )
        st.markdown(
            f'<a class="{link_class}" href="{href}" target="{target}" '
            f'style="{link_style}">{idx}. {fu} &rarr;</a>',
            unsafe_allow_html=True,
        )


def render_followup_text(followups: list[str]) -> None:
    cleaned: list[str] = []
    seen = set()

    for fu in followups or []:
        item = clean_followup_text(fu)
        key = re.sub(r"\s+", " ", item.lower()).strip()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)

    if not cleaned:
        return

    st.markdown(
        "\n".join([f"{idx}. {item}" for idx, item in enumerate(cleaned, start=1)])
    )


# =========================
# Session State
# =========================
if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE

if "page" not in st.session_state:
    st.session_state.page = "New Chat"

# Stage 2 of the First Conversation Experience: session-only display until
# browser persistence is added and tested in the next stage.
if "fce_static_open" not in st.session_state:
    st.session_state.fce_static_open = True

if "fce_pending_action" not in st.session_state:
    st.session_state.fce_pending_action = None

if "fce_force_open" not in st.session_state:
    st.session_state.fce_force_open = False

if "fce_quote" not in st.session_state:
    st.session_state.fce_quote = secrets.choice(FCE_QUOTES)


def _capture_fce_action() -> None:
    """Persist a CCv2 trigger before any Streamlit refresh can replace it."""
    component_state = st.session_state.get("ini_fce")
    action = getattr(component_state, "action", None)
    if action:
        st.session_state.fce_pending_action = action

if "chat" not in st.session_state:
    st.session_state.chat = {"topic": "", "interrogate": None, "illustrate": None}

if "learning_sessions" not in st.session_state:
    st.session_state.learning_sessions: Dict[str, Dict[str, Any]] = {}

if "learning_active_id" not in st.session_state:
    st.session_state.learning_active_id = None

if "_continue_msg_id" not in st.session_state:
    st.session_state._continue_msg_id = None

if "_last_page_param" not in st.session_state:
    st.session_state._last_page_param = None

if "_nc_continue_q" not in st.session_state:
    st.session_state._nc_continue_q = None

if "_nc_continue_loading_q" not in st.session_state:
    st.session_state._nc_continue_loading_q = None

if "_mnl_continue_loading_id" not in st.session_state:
    st.session_state._mnl_continue_loading_id = None

if "chat_direct_answer" not in st.session_state:
    st.session_state.chat_direct_answer = None

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions: Dict[str, Dict[str, Any]] = {}

if "chat_active_id" not in st.session_state:
    st.session_state.chat_active_id = None

if "chat_loaded_sid" not in st.session_state:
    st.session_state.chat_loaded_sid = None

if "chat_branch_history" not in st.session_state:
    st.session_state.chat_branch_history = []

if "chat_popup_sid" not in st.session_state:
    st.session_state.chat_popup_sid = None

if "chat_top_topic_input" not in st.session_state:
    st.session_state.chat_top_topic_input = ""

if "chat_bottom_topic_input" not in st.session_state:
    st.session_state.chat_bottom_topic_input = ""

if "chat_pending_context_clarification" not in st.session_state:
    st.session_state.chat_pending_context_clarification = None
if "chat_pending_qm_confirmation" not in st.session_state:
    st.session_state.chat_pending_qm_confirmation = None
if "chat_pending_discussion_action" not in st.session_state:
    st.session_state.chat_pending_discussion_action = None
if "chat_active_discussion" not in st.session_state:
    st.session_state.chat_active_discussion = None
if "chat_study_mode_established" not in st.session_state:
    st.session_state.chat_study_mode_established = False

if "chat_active_carm_context" not in st.session_state:
    st.session_state.chat_active_carm_context = None
if "chat_user_profile" not in st.session_state:
    st.session_state.chat_user_profile = {}

if "chat_root_topic" not in st.session_state:
    st.session_state.chat_root_topic = ""

if "chat_root_interrogate" not in st.session_state:
    st.session_state.chat_root_interrogate = None

if "chat_root_illustrate" not in st.session_state:
    st.session_state.chat_root_illustrate = None

if "chat_root_intro" not in st.session_state:
    st.session_state.chat_root_intro = ""

if "chat_root_direct_answer" not in st.session_state:
    st.session_state.chat_root_direct_answer = None

if "chat_root_answers" not in st.session_state:
    st.session_state.chat_root_answers = {}

if "chat_root_followups" not in st.session_state:
    st.session_state.chat_root_followups = {}

if "chat_root_open_questions" not in st.session_state:
    st.session_state.chat_root_open_questions = set()

if "chat_root_visited_questions" not in st.session_state:
    st.session_state.chat_root_visited_questions = set()

if "chat_top_enter_submit" not in st.session_state:
    st.session_state.chat_top_enter_submit = False

if "chat_bottom_enter_submit" not in st.session_state:
    st.session_state.chat_bottom_enter_submit = False

if "chat_branch_answers" not in st.session_state:
    st.session_state.chat_branch_answers = []

if "chat_query_log" not in st.session_state:
    st.session_state.chat_query_log = []

# UIB state
if "uib_text" not in st.session_state:
    st.session_state.uib_text = ""
if "uib_mode" not in st.session_state:
    st.session_state.uib_mode = "deep"  # deep|high|quiz

if "_uib_send_requested" not in st.session_state:
    st.session_state._uib_send_requested = False

if "_mnl_send_payload" not in st.session_state:
    st.session_state._mnl_send_payload = None

if "_mnl_composer_revision" not in st.session_state:
    st.session_state._mnl_composer_revision = 0

if "_mnl_pending_request" not in st.session_state:
    st.session_state._mnl_pending_request = None

if "_mnl_generating" not in st.session_state:
    st.session_state._mnl_generating = False

if "_nc_pending_request" not in st.session_state:
    st.session_state._nc_pending_request = None

if "_nc_generating" not in st.session_state:
    st.session_state._nc_generating = False
if "_nc_generating_started_at" not in st.session_state:
    st.session_state._nc_generating_started_at = 0.0

if "_nc_bottom_composer_revision" not in st.session_state:
    st.session_state._nc_bottom_composer_revision = 0

if "_nc_scroll_to_latest_response" not in st.session_state:
    st.session_state._nc_scroll_to_latest_response = False

if "nc_started" not in st.session_state:
    st.session_state.nc_started = False

if "rename_session_sid" not in st.session_state:
    st.session_state.rename_session_sid = None

if "rename_session_page" not in st.session_state:
    st.session_state.rename_session_page = None


def ensure_learning_session() -> str:
    if (
        st.session_state.learning_active_id
        and st.session_state.learning_active_id in st.session_state.learning_sessions
    ):
        return st.session_state.learning_active_id

    sid = f"learn-{secrets.token_urlsafe(12)}"
    st.session_state.learning_sessions[sid] = {
        "created": _user_now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    return sid


def start_new_learning_session() -> str:
    sid = f"learn-{secrets.token_urlsafe(12)}"
    st.session_state.learning_sessions[sid] = {
        "created": _user_now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    return sid


def _persist_learning_session(sid: str, sess: Dict[str, Any]) -> None:
    created = sess.get("created") or _user_now().strftime("%b %d.%Y")

    default_titles = {"", "Learning Session", "Session", "New Session"}

    first_user_prompt = ""
    for m in sess.get("messages", []):
        if m.get("role") == "user":
            t = (m.get("text") or "").strip()
            if t:
                first_user_prompt = t
                break

    current_title = (sess.get("title") or "").strip()

    if not sess.get("_title_set", False):
        if (current_title in default_titles) and first_user_prompt:
            sess["title"] = first_user_prompt
            sess["_title_set"] = True
        elif current_title and (current_title not in default_titles):
            sess["_title_set"] = True

    title_to_save = (sess.get("title") or "Learning Session").strip()

    save_session(
        visitor_id=st.session_state.visitor_id,
        session_id=sid,
        title=title_to_save,
        created_at=created,
        messages=sess.get("messages", []),
    )


def _empty_new_chat_state() -> Dict[str, Any]:
    return {
        "topic": "",
        "interrogate": None,
        "illustrate": None,
        "chat_intro": "",
        "chat_answers": {},
        "chat_followups": {},
        "chat_open_questions": [],
        "chat_visited_questions": [],
        "chat_direct_answer": None,
        "chat_seed_done": "",
        "chat_branch_history": [],
        "chat_branch_answers": [],
        "chat_query_log": [],
        "chat_active_discussion": None,
        "chat_study_mode_established": False,
        "chat_user_profile": {},
    }


def _reset_new_chat_state() -> None:
    st.session_state.chat = {"topic": "", "interrogate": None, "illustrate": None}
    st.session_state.chat_intro = ""
    st.session_state.chat_answers = {}
    st.session_state.chat_followups = {}
    st.session_state.chat_open_questions = set()
    st.session_state.chat_visited_questions = set()
    st.session_state.chat_direct_answer = None
    st.session_state.chat_seed_done = ""
    st.session_state.chat_branch_history = []
    st.session_state.chat_branch_answers = []
    st.session_state.chat_query_log = []
    st.session_state.chat_pending_discussion_action = None
    st.session_state.chat_active_discussion = None
    st.session_state.chat_study_mode_established = False
    st.session_state.chat_user_profile = {}
    st.session_state.chat_top_topic_input = ""
    st.session_state.chat_bottom_topic_input = ""

    st.session_state.chat_root_topic = ""
    st.session_state.chat_root_interrogate = None
    st.session_state.chat_root_illustrate = None
    st.session_state.chat_root_intro = ""
    st.session_state.chat_root_direct_answer = None
    st.session_state.chat_root_answers = {}
    st.session_state.chat_root_followups = {}
    st.session_state.chat_root_open_questions = set()
    st.session_state.chat_root_visited_questions = set()
    st.session_state._nc_pending_request = None
    st.session_state._nc_generating = False
    st.session_state._nc_generating_started_at = 0.0
    st.session_state._nc_bottom_composer_revision += 1
    st.session_state._nc_scroll_to_latest_response = False
    st.session_state.chat_top_enter_submit = False
    st.session_state.chat_bottom_enter_submit = False
    st.session_state.nc_started = False

def _current_new_chat_payload() -> Dict[str, Any]:
    return {
        "topic": (st.session_state.chat.get("topic") or "").strip(),
        "interrogate": st.session_state.chat.get("interrogate"),
        "illustrate": st.session_state.chat.get("illustrate"),
        "chat_intro": st.session_state.chat_intro,
        "chat_answers": st.session_state.chat_answers,
        "chat_followups": st.session_state.chat_followups,
        "chat_open_questions": sorted(list(st.session_state.chat_open_questions)),
        "chat_visited_questions": sorted(list(st.session_state.chat_visited_questions)),
        "chat_direct_answer": st.session_state.chat_direct_answer,
        "chat_seed_done": st.session_state.chat_seed_done,
        "chat_branch_history": st.session_state.chat_branch_history,
        "chat_branch_answers": st.session_state.chat_branch_answers,
        "chat_query_log": st.session_state.chat_query_log,
        "chat_active_discussion": st.session_state.chat_active_discussion,
        "chat_study_mode_established": st.session_state.chat_study_mode_established,
        "chat_user_profile": st.session_state.chat_user_profile,

        "chat_root_topic": st.session_state.chat_root_topic,
        "chat_root_interrogate": st.session_state.chat_root_interrogate,
        "chat_root_illustrate": st.session_state.chat_root_illustrate,
        "chat_root_intro": st.session_state.chat_root_intro,
        "chat_root_direct_answer": st.session_state.chat_root_direct_answer,
        "chat_root_answers": st.session_state.chat_root_answers,
        "chat_root_followups": st.session_state.chat_root_followups,
        "chat_root_open_questions": sorted(list(st.session_state.chat_root_open_questions)),
        "chat_root_visited_questions": sorted(list(st.session_state.chat_root_visited_questions)),
    }


def _new_chat_title_from_payload(payload: Dict[str, Any]) -> str:
    root_topic = (payload.get("chat_root_topic") or "").strip()
    if root_topic:
        return root_topic

    topic = (payload.get("topic") or "").strip()
    if topic:
        return topic

    direct = payload.get("chat_direct_answer") or {}
    prompt = (direct.get("prompt") or "").strip() if isinstance(direct, dict) else ""
    if prompt:
        return prompt

    visited = payload.get("chat_visited_questions") or []
    if visited:
        return str(visited[0]).strip()

    query_log = payload.get("chat_query_log") or []
    if query_log and isinstance(query_log[0], dict):
        logged_text = (query_log[0].get("text") or "").strip()
        if logged_text:
            return logged_text

    return "New Chat Session"


def _persist_new_chat_session(sid: Optional[str] = None) -> str:
    payload = _current_new_chat_payload()

    has_meaningful_content = any([
        payload.get("topic"),
        payload.get("interrogate"),
        payload.get("illustrate"),
        payload.get("chat_intro"),
        payload.get("chat_answers"),
        payload.get("chat_direct_answer"),
        payload.get("chat_query_log"),
    ])

    if not has_meaningful_content:
        return st.session_state.chat_active_id or st.session_state.chat_loaded_sid or ""

    if not sid:
        sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

    if not sid:
        sid = f"chat-{secrets.token_urlsafe(12)}"

    st.session_state.chat_active_id = sid
    st.session_state.chat_loaded_sid = sid

    created = _user_now().strftime("%b %d.%Y")
    existing = st.session_state.chat_sessions.get(sid, {})
    if existing.get("created"):
        created = existing["created"]

    title = _new_chat_title_from_payload(payload)

    st.session_state.chat_sessions[sid] = {
        "created": created,
        "title": title,
        "payload": payload,
    }

    save_session(
        visitor_id=st.session_state.visitor_id,
        session_id=sid,
        title=title,
        created_at=created,
        messages=payload,
    )
    return sid


def _record_chat_query(text: str, action: str) -> None:
    """Persist every user submission verbatim, including repeated casual turns."""
    exact_text = text or ""
    if not exact_text.strip():
        return

    st.session_state.chat_query_log.append(
        {
            "id": f"query-{secrets.token_urlsafe(8)}",
            "text": exact_text,
            "action": (action or "interrogate").strip().lower(),
            "ts": now_label(),
        }
    )


def _load_new_chat_session(sid: str) -> bool:
    loaded = load_session(st.session_state.visitor_id, sid)
    if not loaded:
        return False

    payload = loaded.get("messages") or {}
    if not isinstance(payload, dict):
        return False

    st.session_state.chat_active_id = sid
    st.session_state.chat_loaded_sid = sid
    st.session_state.chat_sessions[sid] = {
        "created": loaded.get("created") or _user_now().strftime("%b %d.%Y"),
        "title": (loaded.get("title") or "New Chat Session"),
        "payload": payload,
    }

    st.session_state.chat = {
        "topic": payload.get("topic") or "",
        "interrogate": payload.get("interrogate"),
        "illustrate": payload.get("illustrate"),
    }
    st.session_state.chat_intro = payload.get("chat_intro") or ""
    st.session_state.chat_answers = payload.get("chat_answers") or {}
    st.session_state.chat_followups = payload.get("chat_followups") or {}
    st.session_state.chat_open_questions = set(payload.get("chat_open_questions") or [])
    st.session_state.chat_visited_questions = set(payload.get("chat_visited_questions") or [])
    st.session_state.chat_direct_answer = payload.get("chat_direct_answer")
    st.session_state.chat_seed_done = payload.get("chat_seed_done") or ""
    st.session_state.chat_branch_history = payload.get("chat_branch_history") or []
    st.session_state.chat_branch_answers = payload.get("chat_branch_answers") or []
    st.session_state.chat_query_log = payload.get("chat_query_log") or []
    st.session_state.chat_active_discussion = payload.get("chat_active_discussion")
    st.session_state.chat_study_mode_established = bool(
        payload.get("chat_study_mode_established", False)
    )
    st.session_state.chat_user_profile = payload.get("chat_user_profile") or {}
    st.session_state.chat_pending_discussion_action = None
    st.session_state.chat_top_topic_input = payload.get("topic") or ""
    st.session_state.chat_bottom_topic_input = ""
    st.session_state.chat_root_topic = payload.get("chat_root_topic") or payload.get("topic") or ""
    st.session_state.chat_root_interrogate = payload.get("chat_root_interrogate")
    st.session_state.chat_root_illustrate = payload.get("chat_root_illustrate")
    st.session_state.chat_root_intro = payload.get("chat_root_intro") or ""
    st.session_state.chat_root_direct_answer = payload.get("chat_root_direct_answer")
    st.session_state.chat_root_answers = payload.get("chat_root_answers") or {}
    st.session_state.chat_root_followups = payload.get("chat_root_followups") or {}
    st.session_state.chat_root_open_questions = set(payload.get("chat_root_open_questions") or [])
    st.session_state.chat_root_visited_questions = set(payload.get("chat_root_visited_questions") or [])

    st.session_state.nc_started = True
    return True


def _activate_root_view_from_loaded_session() -> None:
    st.session_state.chat["interrogate"] = st.session_state.chat_root_interrogate
    st.session_state.chat["illustrate"] = st.session_state.chat_root_illustrate
    st.session_state.chat_intro = st.session_state.chat_root_intro or ""
    st.session_state.chat_answers = dict(st.session_state.chat_root_answers or {})
    st.session_state.chat_followups = dict(st.session_state.chat_root_followups or {})
    st.session_state.chat_open_questions = set(st.session_state.chat_root_open_questions or [])
    st.session_state.chat_visited_questions = set(st.session_state.chat_root_visited_questions or [])
    st.session_state.chat_direct_answer = st.session_state.chat_root_direct_answer
    st.session_state.chat_seed_done = ""

def _sync_chat_root_snapshot() -> None:
    existing_root_interrogate = (
        st.session_state.chat_root_interrogate
        if isinstance(st.session_state.chat_root_interrogate, dict)
        else {}
    )
    existing_root_illustrate = (
        st.session_state.chat_root_illustrate
        if isinstance(st.session_state.chat_root_illustrate, dict)
        else {}
    )

    current_interrogate = st.session_state.chat.get("interrogate")
    current_illustrate = st.session_state.chat.get("illustrate")

    if isinstance(current_interrogate, dict):
        st.session_state.chat_root_interrogate = {
            **current_interrogate,
            "ts": existing_root_interrogate.get("ts") or now_label(),
        }
    else:
        st.session_state.chat_root_interrogate = current_interrogate

    if isinstance(current_illustrate, dict):
        st.session_state.chat_root_illustrate = {
            **current_illustrate,
            "ts": existing_root_illustrate.get("ts") or now_label(),
        }
    else:
        st.session_state.chat_root_illustrate = current_illustrate

    st.session_state.chat_root_intro = st.session_state.chat_intro or ""
    st.session_state.chat_root_direct_answer = st.session_state.chat_direct_answer
    st.session_state.chat_root_answers = dict(st.session_state.chat_answers or {})
    st.session_state.chat_root_followups = dict(st.session_state.chat_followups or {})
    st.session_state.chat_root_open_questions = set(st.session_state.chat_open_questions or [])
    st.session_state.chat_root_visited_questions = set(st.session_state.chat_visited_questions or [])



def _append_chat_branch(prompt: str, kind: str) -> None:
    p = (prompt or "").strip()
    k = (kind or "").strip().lower()

    # Only explicit CTA/FUQ-derived prompts should be stored in popup history.
    # Ordinary typed follow-up topics should not appear there.
    if not p or k not in {"fuq", "cta"}:
        return

    existing = st.session_state.chat_branch_history or []
    key = (p.lower(), k)
    seen = {
        (str(x.get("prompt", "")).strip().lower(), str(x.get("kind", "")).strip().lower())
        for x in existing
        if isinstance(x, dict)
    }

    if key not in seen:
        existing.append({"prompt": p, "kind": k})
        st.session_state.chat_branch_history = existing


def _collect_chat_popup_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    root_topic = (
        (payload.get("chat_root_topic") or "").strip()
        or (payload.get("topic") or "").strip()
        or "Root Topic"
    )

    history = payload.get("chat_branch_history") or []

    fuqs: list[str] = []
    ctas: list[str] = []

    for item in history:
        if not isinstance(item, dict):
            continue
        prompt = (item.get("prompt") or "").strip()
        kind = (item.get("kind") or "").strip().lower()
        if not prompt:
            continue
        if kind == "cta":
            ctas.append(prompt)
        elif kind == "fuq":
            fuqs.append(prompt)

    def _dedupe(seq: list[str]) -> list[str]:
        out = []
        seen = set()
        for x in seq:
            k = x.strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(x)
        return out

    return {
        "root_topic": root_topic,
        "fuqs": _dedupe(fuqs),
        "ctas": _dedupe(ctas),
    }


@st.dialog("Session Branches")
def _render_chat_session_popup() -> None:
    sid = st.session_state.chat_popup_sid
    if not sid:
        return

    loaded = load_session(st.session_state.visitor_id, sid)
    if not loaded:
        st.warning("Session could not be loaded.")
        return

    payload = loaded.get("messages") or {}
    if not isinstance(payload, dict):
        st.warning("Session payload is invalid.")
        return

    data = _collect_chat_popup_data(payload)
    root_topic = data["root_topic"]
    fuqs = data["fuqs"]
    ctas = data["ctas"]

    has_visible_bg = any([
        (st.session_state.get("chat") or {}).get("interrogate"),
        (st.session_state.get("chat") or {}).get("illustrate"),
        st.session_state.get("chat_direct_answer"),
        bool(st.session_state.get("chat_answers", {})),
    ])

    fuq_target = "_blank" if has_visible_bg else "_self"

    st.markdown(
        f'<a class="ini_plain_link" href="{_chat_root_view_href(sid)}" target="_self"><b>↠ {root_topic}</b></a>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("#### FUQs")
    if fuqs:
        html = ['<div class="ini_popup_section">']
        for item in fuqs:
            href = _chat_branch_href(sid, item)
            html.append(f'<a class="ini_plain_link" href="{href}" target="{fuq_target}">{item}</a>')
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.caption("No FUQs saved yet.")

    st.markdown("#### CTAs")
    if ctas:
        html = ['<div class="ini_popup_section">']
        for item in ctas:
            href = _chat_branch_href(sid, item)
            html.append(f'<a class="ini_plain_link" href="{href}" target="_blank">{item}</a>')
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.caption("No CTAs saved yet.")

# =========================
# API calls
# =========================
def post_json(path: str, payload: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
    url = f"{st.session_state.api_base}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_study(
    topic: str,
    mode: str = "deep",
    continue_mode: bool = False,
    previous_answer: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"topic": topic, "mode": mode}

    if continue_mode and previous_answer:
        payload["continue_mode"] = True
        payload["previous_answer"] = previous_answer

    return post_json("/study/ai", payload, timeout=180)


def fetch_interrogate(topic: str) -> Dict[str, Any]:
    return post_json("/interrogate", {"topic": topic}, timeout=240)


def fetch_illustrate(topic: str) -> Dict[str, Any]:
    return post_json("/illustrate", {"topic": topic}, timeout=240)


def fetch_study_full(topic: str, mode: str = "deep", max_rounds: int = 4) -> Dict[str, Any]:
    resp = fetch_study(topic, mode=mode)
    answer = normalize_whitespace_for_readability(
        normalize_mojibake(resp.get("answer", "") or "")
    )

    rounds = 0
    while rounds < max_rounds and (
        resp.get("incomplete") is True
        or (resp.get("stop_reason") or "").strip().lower() == "max_output_tokens"
    ):
        resp = fetch_study(
            topic,
            mode=mode,
            continue_mode=True,
            previous_answer=answer,
        )
        chunk = normalize_whitespace_for_readability(
            normalize_mojibake(resp.get("answer", "") or "")
        ).strip()

        if not chunk:
            break

        answer = (answer.rstrip() + "\n\n" + chunk).strip()
        rounds += 1

    return {
        "answer": answer,
        "incomplete": resp.get("incomplete"),
        "stop_reason": resp.get("stop_reason"),
        "followups": resp.get("followups") or [],
    }


def split_answer_and_embedded_followups(text: str) -> tuple[str, list[str]]:
    if not text:
        return "", []

    lines = text.splitlines()

    marker_patterns = [
        r"^suggested follow-ups?:?$",
        r"^suggested follow-up questions:?$",
    ]

    cta_header_patterns = [
        r"^if you want,?\s+i can\b.*:?\s*$",
        r"^if you'd like,?\s+i can\b.*:?\s*$",
        r"^next i can\b.*:?\s*$",
        r"^would you like\b.*:?\s*$",
        r"^do you want me to\b.*:?\s*$",
        r"^which part should i expand on\b.*:?\s*$",
        r"^should i\b.*:?\s*$",
    ]

    def _clean_fu_line(s: str) -> str:
        s = re.sub(r"^\(?\d+\)?[.)]?\s*", "", s)
        s = re.sub(r"^[-•*o]\s*", "", s)
        return s.strip()

    marker_idx = None
    for i, ln in enumerate(lines):
        s = re.sub(r"[*_`]+", "", (ln or "").strip()).lower()
        if any(re.match(p, s) for p in marker_patterns):
            marker_idx = i
            break

    followups: list[str] = []
    body_lines: list[str] = []

    if marker_idx is not None:
        body_lines = lines[:marker_idx]
        fu_lines = lines[marker_idx + 1:]

        for ln in fu_lines:
            s = _clean_fu_line((ln or "").strip())
            if s:
                followups.append(s)

        return "\n".join(body_lines).strip(), followups

    i = 0
    while i < len(lines):
        raw = lines[i]
        s = (raw or "").strip()
        low = s.lower()

        if any(re.match(p, low) for p in cta_header_patterns):
            body_lines.append("")
            i += 1

            while i < len(lines):
                next_raw = lines[i]
                next_s = (next_raw or "").strip()

                if not next_s:
                    break

                cleaned = _clean_fu_line(next_s)

                if any(re.match(p, cleaned.lower()) for p in cta_header_patterns):
                    i += 1
                    continue

                if cleaned and len(cleaned) >= 8 and not cleaned.endswith(":"):
                    followups.append(cleaned)

                i += 1

            while i < len(lines) and not (lines[i] or "").strip():
                i += 1
            continue

        body_lines.append(raw)
        i += 1

    seen = set()
    deduped = []
    for fu in followups:
        key = fu.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(fu)

    return "\n".join(body_lines).strip(), deduped


def render_topic_profile(rows: list[tuple[str, str]], compact: bool = False) -> None:
    if not rows:
        return

    items = "".join(
        (
            '<div class="ini-topic-profile__item">'
            f'<div class="ini-topic-profile__label">{escape(label)}</div>'
            f'<div class="ini-topic-profile__value">{escape(value)}</div>'
            "</div>"
        )
        for label, value in rows
    )
    profile_classes = "ini-topic-profile"
    if compact:
        profile_classes += " ini-conversation-profile"
    st.markdown(
        (
            f'<div class="{profile_classes}">'
            '<div class="ini-topic-profile__title">'
            '<span class="ini-topic-profile__mark"></span>'
            "<span>Topic Profile</span>"
            "</div>"
            f'<div class="ini-topic-profile__grid">{items}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_nc_prerequisites(prerequisites: str) -> None:
    text = re.sub(r"\s+", " ", (prerequisites or "")).strip()
    if not text:
        return

    prerequisite_items = split_prerequisite_items(text)
    items_markup = "".join(
        f"<li>{escape(item)}</li>" for item in prerequisite_items
    )

    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-prerequisites-panel">'
            '<div class="ini-topic-profile__title">'
            '<span>Prerequisites</span>'
            '</div>'
            '<div class="ini-nc-prerequisites-panel__content">'
            f'<ul class="ini-nc-prerequisites-list">{items_markup}</ul>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_nc_followup_panel(
    followups: list[str],
    sid: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    cleaned: list[str] = []
    seen = set()

    for followup in followups or []:
        item = clean_followup_text(followup)
        dedupe_key = re.sub(r"\s+", " ", item.lower()).strip()
        if item and dedupe_key not in seen:
            seen.add(dedupe_key)
            cleaned.append(item)

    if not cleaned:
        return

    if target is None:
        target = "_blank"

    cards = "".join(
        (
            f'<a class="ini-nc-followup-panel__item" href="{_chat_branch_href(sid, followup)}" '
            f'target="{target}">'
            f'<span>{index}. {escape(followup)}</span>'
            '<span class="ini-nc-followup-panel__arrow">&rarr;</span>'
            '</a>'
        )
        for index, followup in enumerate(cleaned, start=1)
    )
    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-followup-panel">'
            '<div class="ini-topic-profile__title">'
            '<span>Suggested Follow-ups</span>'
            '</div>'
            f'<div class="ini-topic-profile__grid">{cards}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_nc_learning_paths(
    learning_paths: list[tuple[str, list[str]]],
) -> None:
    if not learning_paths:
        return

    groups_markup = "".join(
        (
            '<section class="ini-nc-learning-paths__group">'
            f'<div class="ini-nc-learning-paths__heading">{escape(label)}</div>'
            '<ul class="ini-nc-learning-paths__list">'
            + "".join(f"<li>{escape(question)}</li>" for question in questions)
            + "</ul></section>"
        )
        for label, questions in learning_paths
    )
    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-learning-paths">'
            '<div class="ini-topic-profile__title">'
            '<span>Related Learning Paths</span>'
            '</div>'
            f'<div class="ini-nc-learning-paths__grid">{groups_markup}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_nc_your_question(question_context: dict[str, str]) -> None:
    question = (question_context or {}).get("Question", "").strip()
    intent = (question_context or {}).get("Intent", "").strip()
    learning_goal = (question_context or {}).get("Learning goal", "").strip()
    if not question:
        return

    insights = []
    if intent:
        insights.append(
            '<div><div class="ini-nc-your-question__label">What you are asking</div>'
            f'<div class="ini-nc-your-question__value">{escape(intent)}</div></div>'
        )
    if learning_goal:
        insights.append(
            '<div><div class="ini-nc-your-question__label">What clarity looks like</div>'
            f'<div class="ini-nc-your-question__value">{escape(learning_goal)}</div></div>'
        )

    insight_markup = (
        f'<div class="ini-nc-your-question__insight">{"".join(insights)}</div>'
        if insights
        else ""
    )
    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-your-question">'
            '<div class="ini-topic-profile__title"><span>Your Question</span></div>'
            f'<div class="ini-nc-your-question__prompt">{escape(question)}</div>'
            f'{insight_markup}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_nc_core_explanation(explanation: dict[str, Any]) -> None:
    title = str((explanation or {}).get("Title") or "").strip()
    overview = str((explanation or {}).get("Overview") or "").strip()
    update_rule = str((explanation or {}).get("Update rule") or "").strip()
    key_insight = str((explanation or {}).get("Key insight") or "").strip()
    worked_example = str((explanation or {}).get("Worked example") or "").strip()
    variables = (explanation or {}).get("Variables") or []
    steps = (explanation or {}).get("Steps") or []
    if not title or not overview:
        return

    control_id = abs(hash(repr(explanation)))
    open_key = f"nc_core_explanation_open_{control_id}"
    button_key = f"nc_core_explanation_more_{control_id}"
    expanded = bool(st.session_state.get(open_key, False))
    is_long = len(steps) > 3 or bool(worked_example)
    visible_steps = steps if expanded or not is_long else steps[:3]

    variable_markup = "".join(
        '<div class="ini-nc-core-explanation__variable">'
        f'<strong>{escape(str(symbol))}</strong> — {escape(str(meaning))}'
        '</div>'
        for symbol, meaning in variables
    )
    steps_markup = "".join(
        '<div class="ini-nc-core-explanation__step">'
        f'<strong>{escape(str(step.get("Heading") or ""))}</strong><br>'
        f'{escape(str(step.get("Explanation") or ""))}'
        '</div>'
        for step in visible_steps
        if isinstance(step, dict)
    )
    example_markup = (
        '<div class="ini-nc-core-explanation__example">'
        f'<strong>Worked example</strong><br>{escape(worked_example)}</div>'
        if worked_example and (expanded or not is_long)
        else ""
    )
    insight_markup = (
        '<div class="ini-nc-core-explanation__insight">'
        f'<strong>Key insight:</strong> {escape(key_insight)}</div>'
        if key_insight
        else ""
    )

    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-core-explanation">'
            f'<div class="ini-topic-profile__title"><span>{escape(title)}</span></div>'
            f'<div class="ini-nc-core-explanation__overview">{escape(overview)}</div>'
            + (
                f'<div class="ini-nc-core-explanation__rule">{escape(update_rule)}</div>'
                if update_rule
                else ""
            )
            + (
                f'<div class="ini-nc-core-explanation__variables">{variable_markup}</div>'
                if variable_markup
                else ""
            )
            + f'<div class="ini-nc-core-explanation__steps">{steps_markup}</div>'
            + insight_markup
            + example_markup
            + '</div>'
        ),
        unsafe_allow_html=True,
    )
    if is_long and st.button(
        "Show less" if expanded else "More",
        key=button_key,
        type="tertiary",
    ):
        st.session_state[open_key] = not expanded
        st.rerun()


def render_nc_learning_loop(learning_loop: dict[str, Any]) -> None:
    stages = (learning_loop or {}).get("Stages") or []
    outcome = str((learning_loop or {}).get("Outcome") or "").strip()
    if not stages:
        return

    stages_markup = "".join(
        (
            '<div class="ini-nc-learning-loop__stage">'
            f'<span class="ini-nc-learning-loop__number">{index}</span>'
            '<div>'
            f'<div class="ini-nc-learning-loop__heading">{escape(re.sub(r"^\s*\d+\s*[.)-]\s*", "", str(stage.get("Heading") or "")))}</div>'
            f'<div class="ini-nc-learning-loop__copy">{escape(str(stage.get("Explanation") or ""))}</div>'
            '</div></div>'
        )
        for index, stage in enumerate(stages, start=1)
        if isinstance(stage, dict)
    )
    outcome_markup = (
        '<div class="ini-nc-learning-loop__outcome">'
        f'<strong>What the loop achieves:</strong> {escape(outcome)}</div>'
        if outcome
        else ""
    )
    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-learning-loop">'
            '<div class="ini-topic-profile__title"><span>The Complete Learning Loop</span></div>'
            f'<div class="ini-nc-learning-loop__track">{stages_markup}</div>'
            f'{outcome_markup}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_nc_continue_journey(journey: dict[str, Any]) -> None:
    directions = (journey or {}).get("Directions") or []
    destination = str((journey or {}).get("Destination") or "").strip()
    if not directions:
        return

    directions_markup = "".join(
        (
            '<div class="ini-nc-continue-journey__direction">'
            f'<span class="ini-nc-continue-journey__number">0{index}</span>'
            f'<div class="ini-nc-continue-journey__heading">{escape(str(direction.get("Heading") or ""))}</div>'
            f'<div class="ini-nc-continue-journey__copy">{escape(str(direction.get("Explanation") or ""))}</div>'
            '</div>'
        )
        for index, direction in enumerate(directions, start=1)
        if isinstance(direction, dict)
    )
    destination_markup = (
        '<div class="ini-nc-continue-journey__destination">'
        f'<strong>Your next milestone:</strong> {escape(destination)}</div>'
        if destination
        else ""
    )
    st.markdown(
        (
            '<div class="ini-topic-profile ini-nc-continue-journey">'
            '<div class="ini-topic-profile__title"><span>Continue Your Journey</span></div>'
            f'<div class="ini-nc-continue-journey__path">{directions_markup}</div>'
            f'{destination_markup}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_nc_section_title(
    title: str,
    subtitle: str = "",
    card_class: str = "",
) -> None:
    class_name = "ini-nc-section-title"
    if card_class:
        class_name = f"{class_name} {card_class}"
    st.markdown(
        (
            f'<div class="{class_name}">'
            '<span class="ini-nc-section-title__mark"></span>'
            f"<span>{escape(title)}</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f'<div class="ini-nc-section-subtitle">{escape(subtitle)}</div>',
            unsafe_allow_html=True,
        )


def render_nc_intro_preview(body: str) -> None:
    text = (body or "").strip()
    if not text:
        return

    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    def intro_html(items: list[str]) -> str:
        html_parts = []
        for item in items:
            safe_item = escape(item).replace("\n", "<br>")
            html_parts.append(f"<p>{safe_item}</p>")
        return (
            '<div class="ini-topic-profile ini-nc-intro-panel">'
            '<div class="ini-topic-profile__title">'
            '<span class="ini-topic-profile__mark"></span>'
            '<span>Introduction</span>'
            '</div>'
            f'<div class="ini-topic-profile__item ini-nc-intro-copy">{"".join(html_parts)}</div>'
            '</div>'
        )

    if len(parts) <= 1:
        st.markdown(intro_html(parts), unsafe_allow_html=True)
        return

    # The reading surface stays singular. More expands this same card rather
    # than adding a second content box beneath the preview.
    control_id = abs(hash(text))
    open_key = f"nc_intro_more_open_{control_id}"
    button_key = f"nc_intro_more_button_{control_id}"
    visible_parts = parts if st.session_state.get(open_key) else parts[:1]
    st.markdown(intro_html(visible_parts), unsafe_allow_html=True)
    if st.button(
        "Show less" if st.session_state.get(open_key) else "More",
        key=button_key,
        type="tertiary",
    ):
        st.session_state[open_key] = not st.session_state.get(open_key, False)
        st.rerun()


def render_nc_question_map_tabs() -> None:
    labels = [
        "Orientation",
        "Foundations",
        "Mechanisms",
        "Methods & Tools",
        "Applications",
        "Pitfalls",
        "Advanced / Future",
    ]
    tabs = "".join(f'<span class="ini-nc-map-tab">{escape(label)}</span>' for label in labels)
    st.markdown(f'<div class="ini-nc-map-tabs">{tabs}</div>', unsafe_allow_html=True)


def normalize_clicked_followup_prompt(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return s

    lowered = s.lower()

    patterns = [
        r"^would you like\s+",
        r"^do you want\s+",
        r"^want\s+",
        r"^interested in\s+",
    ]

    for p in patterns:
        if re.match(p, lowered):
            s = re.sub(p, "", s, flags=re.IGNORECASE).strip()
            break

    replacements = [
        ("a short checklist", "Give me a short checklist"),
        ("a concise comparison", "Give me a concise comparison"),
        ("a compact example", "Give me a compact example"),
        ("a practical checklist", "Give me a practical checklist"),
        ("a short plan", "Give me a short plan"),
    ]

    low2 = s.lower()
    for old, new in replacements:
        if low2.startswith(old):
            s = new + s[len(old):]
            break

    s = s.rstrip(" ?")
    return s      




# =========================
# URL / Query routing
# =========================
qp = st.query_params
page_param = (qp.get("page") or "home").lower()
learn_sid = (qp.get("learn_sid") or "").strip()
chat_sid = (qp.get("chat_sid") or "").strip()
popup_chat_sid = (qp.get("popup_chat_sid") or "").strip()
chat_root = (qp.get("chat_root") or "").strip()
chat_q = (qp.get("chat_q") or "").strip()
learn_q = (qp.get("learn_q") or "").strip()
session_action = (qp.get("session_action") or "").strip().lower()
session_sid = (qp.get("session_sid") or "").strip()

param_to_page = {
    "home": "Home",
    "chat": "New Chat",
    "learn": "My New Learning",
    "proj": "New Project",
}

if page_param in param_to_page:
    new_page = param_to_page[page_param]
    st.session_state.page = new_page


previous_page_param = st.session_state.get("_last_page_param")

if (
    page_param == "chat"
    and not chat_sid
    and not chat_q
    and not popup_chat_sid
    and previous_page_param != "chat"
):
    _reset_new_chat_state()
    st.session_state.chat_active_id = None
    st.session_state.chat_loaded_sid = None

st.session_state._last_page_param = page_param

if popup_chat_sid:
    st.session_state.chat_popup_sid = popup_chat_sid
else:
    st.session_state.chat_popup_sid = None

if learn_sid:
    loaded = load_session(st.session_state.visitor_id, learn_sid)
    if loaded:
        st.session_state.learning_active_id = learn_sid
        st.session_state.learning_sessions[learn_sid] = {
            "created": loaded.get("created") or _user_now().strftime("%b %d.%Y"),
            "messages": loaded.get("messages") or [],
            "title": (loaded.get("title") or "Learning Session"),
            "last_prompt": "",
            "_title_set": (loaded.get("title") or "").strip() not in {"", "Learning Session", "Session", "New Session"},
        }

if chat_sid:
    if st.session_state.chat_loaded_sid != chat_sid:
        _load_new_chat_session(chat_sid)
    elif not st.session_state.chat.get("topic"):
        _load_new_chat_session(chat_sid)

if chat_sid and chat_root == "1":
    if st.session_state.chat_loaded_sid != chat_sid or (
        not st.session_state.chat_root_interrogate
        and not st.session_state.chat_root_illustrate
        and not st.session_state.chat_root_intro
        and not st.session_state.chat_root_answers
    ):
        _load_new_chat_session(chat_sid)
    _activate_root_view_from_loaded_session()

if session_action and session_sid:
    if session_action == "delete":
        delete_session(st.session_state.visitor_id, session_sid)

        if st.session_state.chat_active_id == session_sid:
            st.session_state.chat_active_id = None
            st.session_state.chat_loaded_sid = None

        if st.session_state.learning_active_id == session_sid:
            st.session_state.learning_active_id = None

        _reset_query_to_page(page_param)
        st.rerun()

    elif session_action == "rename":
        st.session_state.rename_session_sid = session_sid
        st.session_state.rename_session_page = page_param
        _reset_query_to_page(page_param)






# =========================
# Sidebar
# =========================
with st.sidebar:
    sidebar_logo_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
    sidebar_logo_data = base64.b64encode(sidebar_logo_path.read_bytes()).decode("ascii")
    st.markdown(
        f'''<div style="display:flex; align-items:center; justify-content:center; margin:3px 0 18px; padding:2px 0;">
              <img src="data:image/png;base64,{sidebar_logo_data}" alt="" style="display:block; width:43px; height:70px; object-fit:contain; margin-right:2px; filter:drop-shadow(0 3px 6px rgba(245,27,63,.12));">
              <div style="display:flex; flex-direction:column; align-items:flex-start; justify-content:center; margin-left:2px;">
                <span style="font-size:35px; font-weight:700; line-height:1; letter-spacing:-1.3px; color:#0f172a;">InI<span style="color:#f51b3f;">.ai</span></span>
                <span style="margin-top:5px; font-size:10px; font-weight:500; line-height:1.15; letter-spacing:.12px; color:#667085;">First Question Engine</span>
              </div>
            </div>''',
        unsafe_allow_html=True,
    )

    def _render_clock_tile():
        cp = clock_parts()
        st.markdown(
            f'''
            <div class="clock_tile">
              <div class="clock_center">
                <div class="clock_time">{cp["time"]}</div>
                <div class="clock_ampm">{cp["ampm"]}</div>
              </div>
              <div class="clock_row_bottom">
                <div class="clock_box">{cp["date"]}</div>
                <div class="clock_box">{cp["dow"]}</div>
              </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    if hasattr(st, "fragment"):
        @st.fragment(run_every="1s")  # type: ignore[arg-type]
        def _clock_fragment():
            _render_clock_tile()
        _clock_fragment()
    elif st_autorefresh is not None:
        st_autorefresh(interval=1000, key="ini_clock_tick")
        _render_clock_tile()
    else:
        _render_clock_tile()
        st.caption("Tip: install 'streamlit-autorefresh' to enable a live-updating clock.")

    st.markdown('<span class="badge" style="margin-left:11px;">v0.1.4 &middot; Question Intelligence</span>', unsafe_allow_html=True)

    st.markdown('<div class="small" style="color:var(--muted); font-weight:750; margin-top:10px;">Navigation</div>', unsafe_allow_html=True)
    intro_nav_href = _private_href(page="home")
    chat_nav_href = _private_href(page="chat")
    learn_nav_href = _private_href(page="learn")
    project_nav_href = _private_href(page="proj")
    st.markdown(
        f"""
        <div class="ini-sidebar-nav">
          <a class="ini-sidebar-nav-card {'is-active' if page_param == 'home' else ''}"
             href="{intro_nav_href}" target="_self">🏠&nbsp;&nbsp;Introduction</a>
          <a class="ini-sidebar-nav-card {'is-active' if page_param == 'chat' else ''}"
             href="{chat_nav_href}" target="_self">💬&nbsp;&nbsp;New Chat</a>
          <a class="ini-sidebar-nav-card {'is-active' if page_param == 'learn' else ''}"
             href="{learn_nav_href}" target="_self">📚&nbsp;&nbsp;My New Learning</a>
          <a class="ini-sidebar-nav-card {'is-active' if page_param == 'proj' else ''}"
             href="{project_nav_href}" target="_self">🧩&nbsp;&nbsp;New Project</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if DEV_MODE:
        st.markdown("<hr/>", unsafe_allow_html=True)
        with st.expander("API Settings (dev)", expanded=False):
            st.session_state.api_base = st.text_input("API base", st.session_state.api_base)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Chat</div>', unsafe_allow_html=True)

    chat_rows = [
        row
        for row in list_sessions(st.session_state.visitor_id, limit=30)
        if str(row[0]).startswith("chat-")
    ]
    if chat_rows:
        html = []
        for sid, title, created_at, updated_at in chat_rows:
            label = truncate_session_text((title or "New Chat Session").strip(), max_chars=28)
            mmdd = _format_short_mmdd(created_at or "")
            display = f"{label} {mmdd}".strip()

            html.append(f"""
            <div class="ini_session_row">
              <a class="ini_sidebar_link" href="{_chat_popup_href(sid)}" target="_self">{display}</a>
              <div class="ini_session_menu">
                <details>
                  <summary>⋯</summary>
                  <div class="ini_session_dropdown">
                    <a href="{_chat_rename_href(sid)}" target="_self">Rename</a>
                    <a href="{_chat_delete_href(sid)}" target="_self">Delete</a>
                  </div>
                </details>
              </div>
            </div>
            """)

        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.markdown('<div class="small" style="color:var(--muted);">No chat sessions yet.</div>', unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Learning</div>', unsafe_allow_html=True)


    rows = [
        row
        for row in list_sessions(st.session_state.visitor_id, limit=30)
        if str(row[0]).startswith("learn-")
    ]
    if rows:
        html = []
        for sid, title, created_at, updated_at in rows:
            label = truncate_session_text((title or "Learning Session").strip(), max_chars=28)
            mmdd = _format_short_mmdd(created_at or "")
            display = f"{label} {mmdd}".strip()

            html.append(f"""
            <div class="ini_session_row">
            <a class="ini_sidebar_link" href="{_learn_session_href(sid)}" target="_self">{display}</a>
            <div class="ini_session_menu">
                <details>
                <summary>⋯</summary>
                <div class="ini_session_dropdown">
                    <a href="{_learn_rename_href(sid)}" target="_self">Rename</a>
                    <a href="{_learn_delete_href(sid)}" target="_self">Delete</a>
                </div>
                </details>
            </div>
            </div>
            """)

        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.markdown('<div class="small" style="color:var(--muted);">No learning sessions yet.</div>', unsafe_allow_html=True)

# On phones, begin with navigation collapsed. The document-level marker keeps
# Streamlit reruns from closing the drawer again after the user opens it.
st.iframe(
    """
    <script>
    (() => {
      try {
        const doc = window.parent.document;
        const win = window.parent;
        const root = doc.documentElement;

        if (!win.matchMedia('(max-width: 720px)').matches) return;
        if (root.dataset.iniMobileSidebarInitialized === 'true') return;
        root.dataset.iniMobileSidebarInitialized = 'true';

        let attempts = 0;
        const collapseMobileSidebar = () => {
          const sidebar = doc.querySelector('[data-testid="stSidebar"]');
          if (sidebar && sidebar.getAttribute('aria-expanded') !== 'true') return;

          const control = doc.querySelector(
            '[data-testid="stSidebarCollapseButton"]'
          );
          if (sidebar && control) {
            const button = control.matches('button')
              ? control
              : control.querySelector('button');
            (button || control).click();
            return;
          }

          attempts += 1;
          if (attempts < 40) win.setTimeout(collapseMobileSidebar, 50);
        };

        collapseMobileSidebar();
      } catch (err) {}
    })();
    </script>
    """,
    height=1,
    tab_index=-1,
)

@st.dialog("Rename Session")
def _render_rename_session_dialog() -> None:
    sid = st.session_state.rename_session_sid
    if not sid:
        return

    loaded = load_session(st.session_state.visitor_id, sid)
    current_title = ""
    if loaded:
        current_title = (loaded.get("title") or "").strip()

    new_title = st.text_input("Session name", value=current_title, key="rename_session_input")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", key="rename_session_save_btn"):
            rename_session(
                st.session_state.visitor_id,
                sid,
                new_title.strip(),
            )
            st.session_state.rename_session_sid = None
            st.session_state.rename_session_page = None
            st.rerun()
    with c2:
        if st.button("Cancel", key="rename_session_cancel_btn"):
            st.session_state.rename_session_sid = None
            st.session_state.rename_session_page = None
            st.rerun()

if st.session_state.chat_popup_sid:
    _render_chat_session_popup()

if st.session_state.rename_session_sid:
    _render_rename_session_dialog()







# =========================
# Pages
# =========================

def page_home():
    st.markdown(
        """
        <style>
        @keyframes iniIntroCardArrival {
            0% {
                opacity: 0;
                transform: translateY(32px) scale(0.985);
                filter: blur(3px);
            }
            62% {
                opacity: 1;
                filter: blur(0);
            }
            82% {
                opacity: 1;
                transform: translateY(-2px) scale(1);
                filter: blur(0);
            }
            100% {
                opacity: 1;
                transform: translateY(0) scale(1);
                filter: blur(0);
            }
        }

        .st-key-intro_welcome_card,
        .st-key-intro_new_chat_card,
        .st-key-intro_release_history_card,
        .st-key-intro_release_card,
        .st-key-intro_learning_card {
            animation: iniIntroCardArrival 720ms cubic-bezier(0.16, 1, 0.3, 1) both;
            will-change: opacity, transform, filter;
        }

        .st-key-intro_welcome_card {
            animation-delay: 70ms;
        }

        .st-key-intro_new_chat_card {
            animation-delay: 210ms;
        }

        .st-key-intro_release_history_card,
        .st-key-intro_release_card {
            animation-delay: 350ms;
        }

        .st-key-intro_learning_card {
            animation-delay: 490ms;
        }

        @media (prefers-reduced-motion: reduce) {
            .st-key-intro_welcome_card,
            .st-key-intro_new_chat_card,
            .st-key-intro_release_history_card,
            .st-key-intro_release_card,
            .st-key-intro_learning_card {
                animation: none !important;
                transform: none !important;
                filter: none !important;
            }
        }

        .st-key-intro_welcome_card,
        .st-key-intro_new_chat_card,
        .st-key-intro_guide_card,
        .st-key-intro_release_card,
        .st-key-intro_release_history_card,
        .st-key-intro_learning_card {
            position: relative;
            isolation: isolate;
            overflow: hidden;
            margin-bottom: 18px;
            padding: 24px 26px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%,
                rgba(249, 250, 252, 0.96) 100%);
            box-shadow:
                0 18px 46px rgba(15, 23, 42, 0.065),
                0 4px 13px rgba(15, 23, 42, 0.035),
                inset 0 1px 0 rgba(255, 255, 255, 1);
        }

        .st-key-intro_welcome_card::before,
        .st-key-intro_new_chat_card::before,
        .st-key-intro_guide_card::before,
        .st-key-intro_release_card::before,
        .st-key-intro_release_history_card::before,
        .st-key-intro_learning_card::before {
            position: absolute;
            z-index: -1;
            top: 0;
            left: 7%;
            width: 86%;
            height: 1px;
            content: "";
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 1) 22%,
                rgba(255, 255, 255, 1) 78%,
                transparent
            );
        }

        .st-key-intro_welcome_card {
            min-height: 230px;
            padding: 34px 34px 30px;
            background:
                radial-gradient(circle at 92% 18%, rgba(245, 27, 63, 0.07), transparent 29%),
                linear-gradient(145deg, #ffffff 0%, #fbfcfd 70%, #fff8f9 100%);
        }

        .st-key-intro_welcome_card::after {
            position: absolute;
            z-index: -1;
            right: -54px;
            bottom: -88px;
            width: 240px;
            height: 240px;
            border: 1px solid rgba(245, 27, 63, 0.09);
            border-radius: 50%;
            content: "";
            box-shadow:
                0 0 0 34px rgba(245, 27, 63, 0.022),
                0 0 0 68px rgba(245, 27, 63, 0.012);
        }

        .st-key-intro_welcome_card .st-key-replay_fce_welcome {
            position: absolute;
            z-index: 3;
            top: 22px;
            right: 24px;
        }

        .st-key-intro_welcome_card .st-key-replay_fce_welcome button {
            min-width: 0 !important;
            min-height: 38px !important;
            padding: 0 15px !important;
            border: 1px solid rgba(148, 163, 184, 0.22) !important;
            border-radius: 11px !important;
            color: #374151 !important;
            background: rgba(255, 255, 255, 0.78) !important;
            box-shadow: 0 5px 14px rgba(15, 23, 42, 0.045) !important;
        }

        .intro-eyebrow {
            margin-bottom: 14px;
            color: #f51b3f;
            font-size: 12px;
            font-weight: 720;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .intro-hero-title {
            max-width: 720px;
            margin: 0 0 12px;
            color: #0f172a;
            font-size: clamp(34px, 4.1vw, 54px);
            font-weight: 760;
            letter-spacing: -0.035em;
            line-height: 1.04;
        }

        .intro-hero-subtitle {
            margin: 0 0 18px;
            color: #1f2937;
            font-size: 21px;
            font-weight: 680;
            letter-spacing: -0.015em;
        }

        .intro-hero-copy {
            max-width: 760px;
            margin: 0 0 9px;
            color: #4b5563;
            font-size: 15.5px;
            line-height: 1.65;
        }

        .intro-card-heading {
            display: flex;
            align-items: center;
            gap: 11px;
            margin-bottom: 17px;
            color: #111827;
            font-size: 19px;
            font-weight: 720;
            letter-spacing: -0.015em;
        }

        .intro-icon {
            display: inline-flex;
            width: 31px;
            height: 31px;
            align-items: center;
            justify-content: center;
            flex: 0 0 31px;
            border: 1px solid rgba(245, 27, 63, 0.17);
            border-radius: 10px;
            color: #f51b3f;
            background: rgba(255, 246, 248, 0.82);
            font-size: 15px;
            font-weight: 800;
        }

        .intro-mode-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
        }

        .intro-mode-card {
            min-height: 136px;
            padding: 19px 20px;
            border: 1px solid rgba(148, 163, 184, 0.17);
            border-radius: 15px;
            background: rgba(255, 255, 255, 0.78);
            box-shadow:
                0 9px 22px rgba(15, 23, 42, 0.04),
                inset 0 1px 0 rgba(255, 255, 255, 1);
        }

        .intro-mode-title {
            margin: 0 0 8px;
            color: #111827;
            font-size: 17px;
            font-weight: 700;
        }

        .intro-mode-copy,
        .intro-step-copy,
        .intro-learning-copy {
            color: #596273;
            font-size: 13.5px;
            line-height: 1.55;
        }

        .intro-topic-row {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin-top: 13px;
        }

        .intro-topic-chip,
        .intro-mode-chip,
        .intro-release-badge,
        .intro-status-badge {
            display: inline-flex;
            align-items: center;
            border: 1px solid rgba(148, 163, 184, 0.17);
            border-radius: 999px;
            background: rgba(248, 250, 252, 0.82);
            color: #596273;
            font-size: 11.5px;
            font-weight: 620;
        }

        .intro-topic-chip {
            padding: 5px 9px;
        }

        .intro-guide-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 24px;
        }

        .intro-guide-section {
            margin-top: 34px;
            padding-top: 30px;
            border-top: 1px solid rgba(148, 163, 184, 0.2);
        }

        .intro-step {
            position: relative;
            padding-left: 48px;
        }

        .intro-step:not(:last-child)::after {
            position: absolute;
            top: 18px;
            right: -16px;
            width: 24px;
            height: 1px;
            content: "";
            background: rgba(148, 163, 184, 0.42);
        }

        .intro-step-number {
            position: absolute;
            top: 0;
            left: 0;
            display: flex;
            width: 35px;
            height: 35px;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(245, 27, 63, 0.36);
            border-radius: 50%;
            color: #f51b3f;
            background: #ffffff;
            font-size: 13px;
            font-weight: 750;
            box-shadow: 0 5px 12px rgba(15, 23, 42, 0.04);
        }

        .intro-step-title {
            margin: 1px 0 5px;
            color: #111827;
            font-size: 15px;
            font-weight: 700;
        }

        .intro-release-header,
        .intro-learning-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 17px;
        }

        .intro-release-header .intro-card-heading,
        .intro-learning-header .intro-card-heading {
            margin-bottom: 0;
        }

        .intro-release-badge,
        .intro-status-badge {
            padding: 6px 10px;
            white-space: nowrap;
        }

        .intro-status-badge {
            border-color: rgba(245, 27, 63, 0.13);
            color: #d91d3f;
            background: rgba(255, 241, 244, 0.88);
        }

        .intro-release-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            border-top: 1px solid rgba(148, 163, 184, 0.14);
            border-left: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 12px;
            overflow: hidden;
        }

        .intro-release-item {
            padding: 13px 14px;
            border-right: 1px solid rgba(148, 163, 184, 0.14);
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            background: rgba(255, 255, 255, 0.42);
            color: #374151;
            font-size: 12.5px;
            line-height: 1.45;
        }

        .intro-release-item strong {
            display: block;
            margin-bottom: 3px;
            color: #111827;
            font-size: 13px;
        }

        .intro-release-note {
            margin: 15px 2px 0;
            color: #667085;
            font-size: 12.5px;
            line-height: 1.55;
        }

        .st-key-intro_release_card,
        .st-key-intro_release_history_card {
            height: 520px;
            margin-bottom: 18px;
        }

        .st-key-intro_release_history_card {
            padding: 24px 20px;
        }

        .intro-history-heading {
            margin-bottom: 5px;
            color: #111827;
            font-size: 16px;
            font-weight: 720;
            letter-spacing: -0.012em;
        }

        .intro-history-copy {
            margin-bottom: 15px;
            color: #7a8494;
            font-size: 11.5px;
            line-height: 1.45;
        }

        .st-key-intro_release_history_card [class*="st-key-intro_release_"] {
            margin-top: 5px;
        }

        .st-key-intro_release_history_card div.stButton > button {
            min-height: 38px !important;
            height: 38px !important;
            justify-content: flex-start !important;
            padding: 7px 5px !important;
            margin: 0 !important;
            border: 0 !important;
            border-radius: 8px !important;
            color: #596273 !important;
            background: transparent !important;
            box-shadow: none !important;
            white-space: nowrap !important;
            font-size: 10.5px !important;
            font-weight: 620 !important;
        }

        .st-key-intro_release_history_card div.stButton > button p {
            width: 100%;
            overflow: hidden;
            white-space: nowrap !important;
            text-overflow: clip;
        }

        .st-key-intro_release_history_card div.stButton > button:hover {
            color: #111827 !important;
            background: rgba(148, 163, 184, 0.07) !important;
        }

        .st-key-intro_release_history_card div.stButton > button[kind="primary"] {
            color: #d91d3f !important;
            background: linear-gradient(
                90deg,
                rgba(245, 27, 63, 0.075),
                rgba(245, 27, 63, 0.012)
            ) !important;
            box-shadow: inset 2px 0 0 #f51b3f !important;
            font-weight: 700 !important;
        }

        .st-key-intro_release_history_card div.stButton > button:disabled {
            color: #a7afbd !important;
            background: transparent !important;
            box-shadow: none !important;
            cursor: default !important;
            opacity: 0.72 !important;
        }

        .st-key-intro_release_history_card div.stButton > button:disabled:hover {
            color: #a7afbd !important;
            background: transparent !important;
        }

        .intro-release-scroll {
            max-height: 402px;
            overflow-y: auto;
            padding-right: 7px;
            scrollbar-color: rgba(148, 163, 184, 0.38) transparent;
            scrollbar-width: thin;
        }

        .intro-release-scroll::-webkit-scrollbar {
            width: 5px;
        }

        .intro-release-scroll::-webkit-scrollbar-track {
            background: transparent;
        }

        .intro-release-scroll::-webkit-scrollbar-thumb {
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.35);
        }

        .intro-release-end {
            width: 42px;
            height: 1px;
            margin: 17px 2px 5px;
            border-radius: 999px;
            background: linear-gradient(
                90deg,
                rgba(245, 27, 63, 0.42),
                rgba(245, 27, 63, 0.04)
            );
        }

        .intro-learning-modes {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
        }

        .intro-mode-chip {
            min-width: 78px;
            justify-content: center;
            padding: 8px 13px;
            color: #344054;
            background: rgba(255, 255, 255, 0.76);
            box-shadow: 0 5px 13px rgba(15, 23, 42, 0.035);
        }

        @media (max-width: 760px) {
            .st-key-intro_welcome_card,
            .st-key-intro_new_chat_card,
            .st-key-intro_guide_card,
            .st-key-intro_release_card,
            .st-key-intro_release_history_card,
            .st-key-intro_learning_card {
                padding: 20px 18px;
                border-radius: 16px;
            }

            .st-key-intro_welcome_card {
                min-height: 0;
                padding-top: 74px;
            }

            .st-key-intro_welcome_card .st-key-replay_fce_welcome {
                top: 18px;
                right: 18px;
            }

            .intro-mode-grid,
            .intro-guide-grid,
            .intro-release-grid {
                grid-template-columns: 1fr;
            }

            .intro-step:not(:last-child)::after {
                display: none;
            }

            .intro-release-header,
            .intro-learning-header {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="intro_welcome_card"):
        if st.button("Replay Welcome", key="replay_fce_welcome"):
            st.session_state.fce_static_open = True
            st.session_state.fce_force_open = True
            st.rerun()

        st.markdown(
            """
            <div class="intro-eyebrow">Question Intelligence</div>
            <h1 class="intro-hero-title">Welcome to InI.ai</h1>
            <div class="intro-hero-subtitle">Interrogate n Illustrate</div>
            <p class="intro-hero-copy">
              InI.ai is a Question Engine designed to help users learn through
              structured exploration rather than isolated answers.
            </p>
            <p class="intro-hero-copy">
              The platform is actively being improved and updated on a regular basis.
            </p>
            """,
            unsafe_allow_html=True,
        )

    with st.container(key="intro_new_chat_card"):
        st.markdown(
            """
            <div class="intro-card-heading">
              <span class="intro-icon">↗</span>
              <span>Begin with New Chat</span>
            </div>
            <div class="intro-mode-grid">
              <div class="intro-mode-card">
                <div class="intro-mode-title">Interrogate</div>
                <div class="intro-mode-copy">
                  Generates an Introduction, creates a structured Question Map,
                  and organizes learning from Foundations to Advanced topics.
                </div>
                <div class="intro-topic-row">
                  <span class="intro-topic-chip">Artificial Intelligence</span>
                  <span class="intro-topic-chip">Machine Learning</span>
                  <span class="intro-topic-chip">Data Science</span>
                </div>
              </div>
              <div class="intro-mode-card">
                <div class="intro-mode-title">Illustrate</div>
                <div class="intro-mode-copy">
                  Provides examples and applications for a topic and helps reveal
                  where a concept is used in the real world.
                </div>
                <div class="intro-topic-row">
                  <span class="intro-topic-chip">Neural Networks</span>
                  <span class="intro-topic-chip">Transformers</span>
                  <span class="intro-topic-chip">Reinforcement Learning</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="intro-guide-section">
              <div class="intro-card-heading">
                <span class="intro-icon">◇</span>
                <span>How InI guides you</span>
              </div>
              <div class="intro-guide-grid">
                <div class="intro-step">
                  <span class="intro-step-number">1</span>
                  <div class="intro-step-title">Ask</div>
                  <div class="intro-step-copy">
                    Start with a topic, question, or idea. InI listens and clarifies.
                  </div>
                </div>
                <div class="intro-step">
                  <span class="intro-step-number">2</span>
                  <div class="intro-step-title">Map</div>
                  <div class="intro-step-copy">
                    See the foundations, mechanisms, applications, and connected questions.
                  </div>
                </div>
                <div class="intro-step">
                  <span class="intro-step-number">3</span>
                  <div class="intro-step-title">Understand</div>
                  <div class="intro-step-copy">
                    Explore deeply with context, examples, and a clear learning path.
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    intro_releases = {
        "v0.1.4": {
            "date": "July 17, 2026",
            "items": (
                ("Conversational intelligence", "Greetings, clarifying replies, practical requests, and natural follow-ups."),
                ("Smoother context switching", "Move between casual conversation and learning topics while retaining context."),
                ("Discussion mode", "Explore guided discussion directions before building a Question Map."),
                ("Refined response design", "Cleaner response surfaces, quieter cards, and improved typography and spacing."),
                ("Persistent query history", "Every submitted query remains recorded and easy to revisit."),
                ("Thinking & generation states", "Context-aware indicators keep the active input experience stable."),
                ("First Conversation Experience", "A cinematic welcome flow with replay, smoother pacing, and verified quotations."),
                ("Brand and navigation polish", "A refined InI identity, sidebar, version presentation, and floating controls."),
            ),
            "note": (
                "These changes move InI beyond a static question generator toward a "
                "more natural Question Engine that can clarify intent, hold context, "
                "and guide learning without losing the user."
            ),
        },
        "v0.1.3": {
            "date": "July 10, 2026",
            "items": (
                ("Refined New Chat flow", "A clearer path from a submitted topic to its structured learning response."),
                ("Adaptive topic profiles", "Richer profiles that adjust their fields to the subject being explored."),
                ("Question Map interactions", "More deliberate question selection and smoother introduction controls."),
                ("Visitor privacy isolation", "Conversation records are separated by visitor instead of being shared."),
                ("Local dates and timestamps", "Chat activity reflects each visitor's own local time."),
                ("My New Learning refinements", "Improved learning modes, response cards, and query-to-response transitions."),
            ),
            "note": (
                "v0.1.3 established a more dependable learning flow and strengthened "
                "the foundations for private, structured, visitor-specific exploration."
            ),
        },
        "v0.1.2": {
            "date": "June 28, 2026",
            "items": (
                ("Expanded technical coverage", "Broader Question Maps for computer science, hardware, cloud, machine learning, and statistics."),
                ("Stronger topic recognition", "Short technical queries are interpreted more accurately and routed with greater consistency."),
                ("Specific AI subjects preserved", "Topics such as Spatial AI and Constitutional AI retain their precise meaning."),
                ("Ambiguity correction", "Resolved conflicting interpretations such as AMD the company versus the medical condition."),
                ("Interface clarity", "More prominent Interrogate and Illustrate actions and a clearer Introduction experience."),
                ("Visible release identity", "Updated the application label and added a dedicated What's New section."),
            ),
            "note": (
                "v0.1.2 expanded InI's technical vocabulary while improving the "
                "accuracy and consistency of its subject understanding."
            ),
        },
        "v0.1.1": {
            "date": "June 25, 2026",
            "items": (
                ("Stable public deployment", "Aligned the local and live environments around a dependable public release."),
                ("Structured learning workflow", "Established the Topic → Introduction → Question Map → Answer learning journey."),
                ("Improved Question Maps", "Strengthened AI-generated question structure and generation stability."),
                ("Follow-up questions", "Added follow-up generation to continue exploration beyond the initial map."),
                ("Answer continuation", "Supported AI-generated answers with a path for continuing the response."),
                ("Session persistence", "Preserved learning activity across the user's session."),
            ),
            "note": (
                "v0.1.1 established InI's stable foundation as an AI Tutor and "
                "Question Engine built around structured inquiry."
            ),
        },
    }
    if st.session_state.get("intro_selected_release") not in intro_releases:
        st.session_state.intro_selected_release = "v0.1.4"

    selected_release = st.session_state.intro_selected_release
    release = intro_releases[selected_release]
    release_items_html = "".join(
        (
            '<div class="intro-release-item">'
            f"<strong>{heading}</strong>{description}"
            "</div>"
        )
        for heading, description in release["items"]
    )

    release_history_col, release_details_col = st.columns([1, 3.2], gap="medium")
    release_slots = (
        "v0.1.8",
        "v0.1.7",
        "v0.1.6",
        "v0.1.5",
        "v0.1.4",
        "v0.1.3",
        "v0.1.2",
        "v0.1.1",
    )

    with release_history_col:
        with st.container(key="intro_release_history_card", height="stretch"):
            st.markdown(
                """
                <div class="intro-history-heading">Release History</div>
                <div class="intro-history-copy">Select a version to view its release details.</div>
                """,
                unsafe_allow_html=True,
            )
            for version in release_slots:
                is_released = version in intro_releases
                if version == "v0.1.4":
                    button_label = f"{version}  ·  Current"
                elif not is_released:
                    button_label = f"{version}  ·  Unreleased"
                else:
                    button_label = version
                if st.button(
                    button_label,
                    key=f"intro_release_{version.replace('.', '_')}",
                    type="primary" if version == selected_release else "secondary",
                    width="stretch",
                    disabled=not is_released,
                ):
                    st.session_state.intro_selected_release = version
                    st.rerun()

    with release_details_col:
        with st.container(key="intro_release_card", height="stretch"):
            st.markdown(
                f"""
                <div class="intro-release-header">
                  <div class="intro-card-heading">
                    <span class="intro-icon">✦</span>
                    <span>What's New in {selected_release}</span>
                  </div>
                  <span class="intro-release-badge">Released {release["date"]}</span>
                </div>
                <div class="intro-release-scroll">
                  <div class="intro-release-grid">
                    {release_items_html}
                  </div>
                  <p class="intro-release-note">{release["note"]}</p>
                  <div class="intro-release-end" aria-hidden="true"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.container(key="intro_learning_card"):
        st.markdown(
            """
            <div class="intro-learning-header">
              <div class="intro-card-heading">
                <span class="intro-icon">◫</span>
                <span>My New Learning</span>
              </div>
              <span class="intro-status-badge">In active development</span>
            </div>
            <div class="intro-learning-copy">
              This learning workspace is being refined. Its research modes,
              session continuity, and overall learning experience will continue
              to improve in upcoming releases.
            </div>
            <div class="intro-learning-modes">
              <span class="intro-mode-chip">Deep</span>
              <span class="intro-mode-chip">Overview</span>
              <span class="intro-mode-chip">Quiz</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

def page_new_chat() -> None:
    if "chat_answers" not in st.session_state:
        st.session_state.chat_answers = {}
    if "chat_open_questions" not in st.session_state:
        st.session_state.chat_open_questions = set()
    if "chat_visited_questions" not in st.session_state:
        st.session_state.chat_visited_questions = set()
    if "chat_intro" not in st.session_state:
        st.session_state.chat_intro = ""
    if "chat_followups" not in st.session_state:
        st.session_state.chat_followups = {}
    if "chat_seed_done" not in st.session_state:
        st.session_state.chat_seed_done = ""

    if "chat_branch_answers" not in st.session_state:
        st.session_state.chat_branch_answers = []

    def _session_has_existing_root() -> bool:
        return any([
            st.session_state.chat_root_topic,
            st.session_state.chat_root_interrogate,
            st.session_state.chat_root_illustrate,
            st.session_state.chat_root_intro,
            st.session_state.chat_root_direct_answer,
            st.session_state.chat_root_answers,
        ])

    def _latest_response_mode() -> str:
        branches = st.session_state.chat_branch_answers or []
        if branches:
            item = branches[-1]
            if isinstance(item, dict):
                if item.get("kind") != "direct":
                    return str(item.get("kind") or "question_map").strip().lower()
                payload = item.get("direct_answer") or {}
                if isinstance(payload, dict):
                    return str(payload.get("response_mode") or "").strip().lower()
        payload = st.session_state.chat_direct_answer
        if isinstance(payload, dict):
            return str(payload.get("response_mode") or "").strip().lower()
        return ""

    def _append_interrogate_branch(topic_text: str, data: Dict[str, Any], intro: str) -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": "interrogate",
                "topic": topic_text,
                "interrogate": data,
                "intro": intro,
                "answers": {},
                "followups": {},
                "open_questions": [],
                "visited_questions": [],
                "ts": now_label(),
            }
        )
        st.session_state._nc_scroll_to_latest_response = True
        # typed ordinary follow-up topic: keep in chat timeline only, not popup FUQ list
        pass

    def _append_illustrate_branch(topic_text: str, data: Dict[str, Any]) -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": "illustrate",
                "topic": topic_text,
                "illustrate": data,
                "ts": now_label(),
            }
        )
        st.session_state._nc_scroll_to_latest_response = True
        # typed ordinary follow-up topic: keep in chat timeline only, not popup FUQ list
        pass
    
    def _append_direct_branch(topic_text: str, answer_payload: Dict[str, Any], kind: str = "fuq") -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": "direct",
                "topic": topic_text,
                "direct_answer": answer_payload,
                "ts": now_label(),
            }
        )
        st.session_state._nc_scroll_to_latest_response = True
        # typed ordinary follow-up topic: keep in chat timeline only, not popup CTA/FUQ list
        pass


    def _append_nc_message(topic_text: str, answer_payload: Dict[str, Any], kind: str = "direct") -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": kind,
                "topic": (topic_text or "").strip(),
                "direct_answer": answer_payload,
                "ts": now_label(),
            }
        )
        st.session_state._nc_scroll_to_latest_response = True

    




    def _run_new_chat_direct_followup(topic_text: str) -> None:
        if not topic_text.strip():
            return
        capability_boundary = assess_capability(topic_text)
        if capability_boundary:
            _run_new_chat_interrogate(topic_text, show_spinner=False)
            return
        try:
            current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid
            with st.spinner("Generating details... please wait."):
                resp = fetch_study(topic_text.strip(), mode="focused")
                answer = normalize_whitespace_for_readability(
                    normalize_mojibake(resp.get("answer", "") or "")
                ).strip() or "No answer generated."
                followups = resp.get("followups") or []

                st.session_state.chat_direct_answer = {
                    "prompt": topic_text.strip(),
                    "text": answer,
                    "incomplete": bool(resp.get("incomplete")),
                    "stop_reason": resp.get("stop_reason") or None,
                    "mode": "focused",
                    "followups": followups,
                    "ts": now_label()
                }
                _append_chat_branch(topic_text.strip(), "cta")
                _persist_new_chat_session(current_sid)
            st.rerun()
        except Exception as e:
            st.error(f"Error calling /study/ai: {e}")

    def _run_new_chat_branch_interrogate(topic_text: str) -> None:
        if not topic_text.strip():
            return

        current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

        with st.spinner("Generating question map... may take some time."):
            data = fetch_interrogate(topic_text.strip())
            intro_resp = fetch_study_full(topic_text.strip(), mode="intro", max_rounds=0)
            intro = intro_resp.get("answer", "").strip()
            _append_interrogate_branch(topic_text.strip(), data, intro)
            _persist_new_chat_session(current_sid)

    def _run_new_chat_branch_illustrate(topic_text: str) -> None:
        if not topic_text.strip():
            return

        current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

        with st.spinner("Generating illustrations... please wait."):
            data = fetch_illustrate(topic_text.strip())
            _append_illustrate_branch(topic_text.strip(), data)
            _persist_new_chat_session(current_sid)

    def _profile_for_response(
        prompt: str,
        payload: Optional[Dict[str, Any]] = None,
        mode_override: str = "",
    ) -> list[tuple[str, str]]:
        info = payload if isinstance(payload, dict) else {}
        return build_response_profile(
            info.get("profile_prompt") or prompt,
            intent=info.get("intent") or "",
            response_mode=mode_override or info.get("response_mode") or "",
            context_intent=info.get("context_intent") or "",
        )

    def _render_simple_response(
        response_card_key: str,
        text: str,
        ts: str,
        followups: Optional[List[str]] = None,
        clarification_ctas: bool = False,
        stream_response: bool = False,
        topic_profile: Optional[List[tuple[str, str]]] = None,
        compact_profile: bool = False,
        clarification_title: str = "",
        response_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        response_icon_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
        response_icon_data = base64.b64encode(
            response_icon_path.read_bytes()
        ).decode("ascii")

        with st.container(
            horizontal=True,
            vertical_alignment="top",
            gap="small",
            key=f"{response_card_key}_row",
        ):
            st.markdown(
                f'<img class="ini-response-avatar" '
                f'src="data:image/png;base64,{response_icon_data}" '
                f'alt="InI">',
                unsafe_allow_html=True,
            )

            with st.container(border=False, key=response_card_key):
                if clarification_ctas or stream_response:
                    st.markdown('<span class="ini-carm-response-surface"></span>', unsafe_allow_html=True)

                def _render_response_copy() -> None:
                    if clarification_ctas:
                        st.markdown(text)
                    elif stream_response:
                        stream_text = re.sub(
                            r"(?m)^(Immediate intent|Start here|Explore next)\s*",
                            r"### \1\n\n",
                            text,
                        )
                        streamed_keys = st.session_state.setdefault("_carm_streamed_responses", set())
                        stream_key = f"{response_card_key}:{ts}:{len(stream_text)}"
                        if stream_key not in streamed_keys:
                            def _carm_text_stream():
                                for offset in range(0, len(stream_text), 3):
                                    yield stream_text[offset:offset + 3]
                                    time.sleep(0.004)

                            st.write_stream(_carm_text_stream())
                            streamed_keys.add(stream_key)
                        else:
                            st.markdown(stream_text)
                    else:
                        st.markdown(text)

                if topic_profile and compact_profile:
                    reply_col, profile_col = st.columns(
                        [1.55, 1],
                        gap="medium",
                        vertical_alignment="top",
                    )
                    with reply_col:
                        st.markdown(
                            '<span class="ini-casual-response-copy"></span>',
                            unsafe_allow_html=True,
                        )
                        _render_response_copy()
                    with profile_col:
                        render_topic_profile(topic_profile, compact=True)
                else:
                    if topic_profile:
                        render_topic_profile(topic_profile)
                    _render_response_copy()

                if (
                    isinstance(response_payload, dict)
                    and response_payload.get("intent") == "continue_discussion"
                ):
                    state = st.session_state.get("chat_active_discussion")
                    questions = (
                        list(state.get("questions") or [])[:3]
                        if isinstance(state, dict)
                        else []
                    )
                    for index, question in enumerate(questions):
                        if st.button(
                            f"{index + 1}. {question}",
                            key=f"discussion_question_{state.get('set_number', 1)}_{index}",
                            width="stretch",
                        ):
                            _queue_new_chat_request(str(index + 1), "interrogate")

                if followups:
                    if clarification_ctas:
                        if not (
                            isinstance(response_payload, dict)
                            and response_payload.get("hide_clarification_title")
                        ):
                            render_nc_section_title(
                                clarification_title or "Choose the application"
                            )
                        with st.container(horizontal=True, gap="small"):
                            for index, followup in enumerate(followups):
                                label = next(
                                    (
                                        name
                                        for name in ("Codex", "VS Code", "Claude Desktop", "Cursor")
                                        if name in followup
                                    ),
                                    followup,
                                )
                                if st.button(
                                    label,
                                    key=f"{response_card_key}_clarification_cta_{index}",
                                    width="content",
                                ):
                                    _queue_new_chat_request(followup, "interrogate")
                    else:
                        render_nc_section_title("Suggested Follow-ups")
                        render_followup_links(
                            "chat",
                            followups,
                            st.session_state.chat_active_id,
                        )

                st.markdown(
                    f"<div style='margin-top:14px; text-align:right; color:#64748b; font-size:11px;'>{ts or now_label()}</div>",
                    unsafe_allow_html=True,
                )

    def _render_question_map_response_icon() -> None:
        icon_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
        icon_data = base64.b64encode(icon_path.read_bytes()).decode("ascii")
        st.markdown(
            f'<div class="ini-qmap-avatar-anchor">'
            f'<img src="data:image/png;base64,{icon_data}" alt="InI">'
            f'</div>',
            unsafe_allow_html=True,
        )

    def _discussion_questions_for(topic: str, set_number: int = 1) -> List[str]:
        clean_topic = (topic or "this topic").strip()
        plural_topic = clean_topic.lower().endswith("s")
        work_verb = "do" if plural_topic else "does"
        utility_verb = "are" if plural_topic else "is"
        if set_number <= 1:
            return [
                f"Which direction within {clean_topic} should we explore first—core concepts, mechanisms, applications, or limitations?",
                f"How {work_verb} {clean_topic} work in practice, and which processes or methods matter most?",
                f"Where {utility_verb} {clean_topic} most useful, and what trade-offs should someone understand?",
            ]
        return [
            f"What evidence or examples best demonstrate the important ideas in {clean_topic}?",
            f"What common misconceptions or failure modes appear when people work with {clean_topic}?",
            f"What advanced or emerging direction in {clean_topic} would be most valuable to examine next?",
        ]

    def _render_discussion_answer_card(
        response_key: str,
        payload: Dict[str, Any],
    ) -> None:
        meta = payload.get("discussion_answer") or {}
        question = (meta.get("question") or payload.get("prompt") or "").strip()
        answer = (payload.get("text") or "").strip()
        index = int(meta.get("index", 0))
        total = int(meta.get("count", 3))
        expanded_key = f"discussion_expanded_{response_key}"
        expanded = bool(
            st.session_state.get(expanded_key, False)
            or meta.get("expanded_answer", False)
        )
        preview = answer if expanded or len(answer) <= 900 else answer[:900].rsplit(" ", 1)[0] + "…"

        response_icon_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
        response_icon_data = base64.b64encode(response_icon_path.read_bytes()).decode("ascii")
        with st.container(horizontal=True, vertical_alignment="top", gap="small"):
            st.markdown(
                f'<img class="ini-response-avatar" src="data:image/png;base64,{response_icon_data}" alt="InI">',
                unsafe_allow_html=True,
            )
            with st.container(border=False, key=f"discussion_answer_card_{response_key}"):
                st.markdown(
                    f'<div class="ini-discussion-question-inner"><b>{escape(question)}</b></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(preview)
                if len(answer) > 900:
                    if st.button(
                        "Show less" if expanded else "More",
                        key=f"discussion_more_{response_key}",
                        width="content",
                    ):
                        st.session_state[expanded_key] = not expanded
                        st.rerun()

                with st.container(horizontal=True, gap="small"):
                    if st.button("Explain More", key=f"discussion_explain_{response_key}", width="content"):
                        _queue_new_chat_request("Explain more", "interrogate")
                    if index > 0 and st.button(
                        "Previous Question",
                        key=f"discussion_previous_{response_key}",
                        width="content",
                    ):
                        _queue_new_chat_request("Previous Question", "interrogate")
                    if index < total - 1:
                        if st.button(
                            "Next Question",
                            key=f"discussion_next_{response_key}",
                            width="content",
                        ):
                            _queue_new_chat_request("Next Question", "interrogate")
                    elif st.button(
                        "Next Question Set",
                        key=f"discussion_next_set_{response_key}",
                        width="content",
                    ):
                        _queue_new_chat_request("Next Question Set", "interrogate")

                st.markdown(
                    f"<div style='margin-top:14px; text-align:right; color:#64748b; font-size:11px;'>{payload.get('ts') or now_label()}</div>",
                    unsafe_allow_html=True,
                )

    def _render_active_discussion_panel() -> None:
        state = st.session_state.get("chat_active_discussion")
        if not isinstance(state, dict) or not state.get("questions"):
            return
        questions = list(state.get("questions") or [])[:3]
        st.markdown('<div class="ini-discussion-panel"><b>Continue Discussion</b></div>', unsafe_allow_html=True)
        for index, question in enumerate(questions):
            if st.button(
                f"{index + 1}. {question}",
                key=f"discussion_question_{state.get('set_number', 1)}_{index}",
                width="content",
            ):
                _queue_new_chat_request(str(index + 1), "interrogate")
        awaiting = state.get("awaiting_option_index")
        if isinstance(awaiting, int) and 0 <= awaiting < len(questions):
            st.caption(
                "Type the option you want in the input bar below—for example: core concepts, mechanisms, applications, or limitations."
            )

    def _render_branch_simple_response(
        branch_idx: int,
        text: str,
        ts: str,
        followups: Optional[List[str]] = None,
        clarification_ctas: bool = False,
        stream_response: bool = False,
        topic_profile: Optional[List[tuple[str, str]]] = None,
        compact_profile: bool = False,
        clarification_title: str = "",
        response_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        if isinstance(response_payload, dict) and response_payload.get("discussion_answer"):
            _render_discussion_answer_card(
                f"branch_{branch_idx}",
                response_payload,
            )
            return
        _render_simple_response(
            f"branch_response_card_{branch_idx}",
            text,
            ts,
            followups,
            clarification_ctas,
            stream_response,
            topic_profile,
            compact_profile,
            clarification_title,
            response_payload,
        )

    def _render_branch_question_map(branch_idx: int, branch: Dict[str, Any]) -> None:

        
        data = branch.get("interrogate") or {}
        if not isinstance(data, dict) or not data.get("categories"):
            return

        _render_question_map_response_icon()
        with st.container(border=True, key=f"branch_response_card_{branch_idx}"):
            branch_ts = branch.get("ts") or now_label()
            continue_journey: dict[str, Any] = {}

            intro = (branch.get("intro") or "").strip()
            if intro:
                learning_paths, intro_without_paths = extract_learning_paths(intro)
                your_question, intro_without_question = extract_your_question(
                    intro_without_paths
                )
                core_explanation, intro_without_core = extract_core_explanation(
                    intro_without_question
                )
                learning_loop, intro_without_loop = extract_learning_loop(
                    intro_without_core
                )
                continue_journey, intro_without_journey = extract_continue_journey(
                    intro_without_loop
                )
                clean_intro, intro_followups = split_answer_and_embedded_followups(
                    intro_without_journey
                )
                profile_rows, intro_body = extract_topic_profile(clean_intro or intro)
                profile_rows, prerequisites = split_prerequisites(profile_rows)

                render_topic_profile(profile_rows)
                render_nc_prerequisites(prerequisites)
                if intro_body:
                    render_nc_intro_preview(intro_body)
                render_nc_your_question(your_question)
                render_nc_core_explanation(core_explanation)
                render_nc_learning_loop(learning_loop)

                if learning_paths:
                    render_nc_learning_paths(learning_paths)
                elif intro_followups:
                    render_nc_followup_panel(
                        intro_followups,
                        st.session_state.chat_active_id,
                    )

            branch_answers = branch.setdefault("answers", {})
            branch_followups = branch.setdefault("followups", {})
            branch_open_questions = set(branch.get("open_questions") or [])
            branch_visited_questions = set(branch.get("visited_questions") or [])

            cats = data.get("categories") or {}

            ladder = [
                ("Orientation", ["Orientation"]),
                ("Foundations", ["Foundations"]),
                ("Mechanisms", ["Mechanisms"]),
                ("Methods & Tools", ["Methods & Tools"]),
                ("Applications", ["Applications"]),
                ("Pitfalls", ["Pitfalls"]),
                ("Advanced / Future", ["Advanced / Future"]),
            ]

            question_map_panel = st.container(
                border=True,
                key=f"branch_question_map_panel_{branch_idx}",
            )
            with question_map_panel:
                with st.container(
                    horizontal=True,
                    horizontal_alignment="distribute",
                    vertical_alignment="center",
                    gap="small",
                    key=f"branch_qmap_header_{branch_idx}",
                ):
                    render_nc_section_title(
                        "Question Map",
                        card_class="ini-nc-qmap-marker",
                    )
                    hide_answers = st.toggle(
                        "Hide answers",
                        value=False,
                        key=f"branch_hide_answers_{branch_idx}",
                    )

                question_map_content = question_map_panel
                selected_section = st.radio(
                    "Question Map section",
                    [section for section, _ in ladder],
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"branch_{branch_idx}_qm_section",
                )

            for section, cat_keys in ladder:
                qs = []
                for ck in cat_keys:
                    items = cats.get(ck) or []
                    for it in items:
                        q = (it.get("question") or "").strip()
                        if q and q not in qs:
                            qs.append(q)

                if not qs:
                    continue

                open_section = section == selected_section
                if open_section:
                    for q in qs:
                        visited = q in branch_visited_questions
                        is_open = q in branch_open_questions
                        button_label = f"✓ {q}" if visited else q

                        if question_map_content.button(
                            button_label,
                            key=f"branch_{branch_idx}_q_{section}_{q}",
                            type="secondary",
                        ):
                            branch_visited_questions.add(q)

                            if is_open:
                                branch_open_questions.discard(q)
                                branch["open_questions"] = sorted(list(branch_open_questions))
                                branch["visited_questions"] = sorted(list(branch_visited_questions))
                                st.session_state.chat_branch_answers[branch_idx] = branch
                                _persist_new_chat_session()
                                st.rerun()

                            if q in branch_answers:
                                branch_open_questions.add(q)
                                branch["open_questions"] = sorted(list(branch_open_questions))
                                branch["visited_questions"] = sorted(list(branch_visited_questions))
                                st.session_state.chat_branch_answers[branch_idx] = branch
                                _persist_new_chat_session()
                                st.rerun()

                            try:
                                with question_map_content:
                                    with st.spinner("Generating details... please wait."):
                                        resp = fetch_study(q, mode="focused")
                                        answer = normalize_whitespace_for_readability(
                                            normalize_mojibake(resp.get("answer", "") or "")
                                        ).strip() or "No answer generated."

                                        branch_answers[q] = {
                                            "text": answer,
                                            "incomplete": bool(resp.get("incomplete")),
                                            "stop_reason": resp.get("stop_reason") or None,
                                            "prompt": q,
                                            "mode": "deep",
                                        }
                                        branch_followups[q] = resp.get("followups") or []
                                        branch_open_questions.add(q)
                                        branch["answers"] = branch_answers
                                        branch["followups"] = branch_followups
                                        branch["open_questions"] = sorted(list(branch_open_questions))
                                        branch["visited_questions"] = sorted(list(branch_visited_questions))
                                        st.session_state.chat_branch_answers[branch_idx] = branch
                                        _persist_new_chat_session()

                                st.rerun()

                            except Exception as e:
                                question_map_content.error(f"Error calling /study/ai: {e}")

                        if q in branch_open_questions and not hide_answers:
                            answer_obj = branch_answers.get(q, {})
                            raw_answer = (
                                (answer_obj.get("text") or "").strip()
                                if isinstance(answer_obj, dict)
                                else str(answer_obj or "").strip()
                            )

                            if raw_answer:
                                clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

                                followups = embedded_followups or branch_followups.get(q, [])
                                with question_map_content:
                                    _render_nc_ai_bubble(
                                        "##### Answer\n\n" + (clean_answer or raw_answer),
                                        "",
                                        answer_card_key=f"qmap_answer_card_{abs(hash(f'branch:{branch_idx}:{q}'))}",
                                    )
                                    if followups:
                                        render_nc_section_title("Suggested Follow-ups")
                                        render_followup_links(
                                            "chat",
                                            followups,
                                            st.session_state.chat_active_id,
                                            target="_blank",
                                        )

                                is_incomplete = False
                                if isinstance(answer_obj, dict):
                                    is_incomplete = bool(answer_obj.get("incomplete"))

                                if is_incomplete:
                                    branch_continue_key = f"branch::{branch_idx}::{q}"

                                    if st.button("Continue", key=f"branch_{branch_idx}_cont_{section}_{q}"):
                                        st.session_state._nc_continue_loading_q = branch_continue_key
                                        st.rerun()

                                    if st.session_state._nc_continue_loading_q == branch_continue_key:
                                        st.markdown("⏳ **Continuing...**")

                                        previous_text = (answer_obj.get("text") or "").strip()
                                        mode = (answer_obj.get("mode") or "deep").strip()

                                        if previous_text:
                                            try:
                                                resp = fetch_study(
                                                    topic=q,
                                                    mode=mode,
                                                    continue_mode=True,
                                                    previous_answer=previous_text,
                                                )

                                                chunk = normalize_whitespace_for_readability(
                                                    normalize_mojibake(resp.get("answer", "") or "")
                                                ).strip()

                                                combined = (
                                                    previous_text.rstrip() + "\n\n" + chunk
                                                ).strip() if chunk else previous_text

                                                branch_answers[q] = {
                                                    "text": combined,
                                                    "incomplete": bool(resp.get("incomplete")),
                                                    "stop_reason": resp.get("stop_reason") or None,
                                                    "prompt": q,
                                                    "mode": mode,
                                                }

                                                if resp.get("followups"):
                                                    branch_followups[q] = resp.get("followups") or []

                                                branch["answers"] = branch_answers
                                                branch["followups"] = branch_followups
                                                st.session_state.chat_branch_answers[branch_idx] = branch
                                                _persist_new_chat_session()

                                            except Exception as e:
                                                st.error(f"Error continuing answer: {e}")

                                            finally:
                                                st.session_state._nc_continue_loading_q = None

                                            st.rerun()

                                question_map_panel.markdown("---")

            render_nc_continue_journey(continue_journey)
            st.markdown(
                f"<div style='margin-top:14px; text-align:right; color:#64748b; font-size:11px;'>{branch_ts}</div>",
                unsafe_allow_html=True,
            )

    def _render_nc_user_bubble(
        text: str,
        ts: str = "",
        extra_class: str = "",
    ) -> None:
        prompt = (text or "").strip()
        if not prompt:
            return

        class_names = "nc-user-bubble"
        if extra_class:
            class_names += f" {extra_class.strip()}"

        ts_html = ""
        if ts:
            ts_html = f"<div style='margin-top:6px; text-align:right; color:#64748b; font-size:11px;'>{ts}</div>"

        st.markdown(
            f"""
            <div class="{class_names}" style="display:flex; justify-content:flex-end; margin: 10px 0 14px 0;">
            <div class="nc-user-bubble__content" style="
                max-width: 68%;
                background: #f3f4f6;
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 18px;
                padding: 10px 14px;
                line-height: 1.45;
                font-size: 14px;
                box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            ">
                <span class="nc-user-bubble__prompt">{prompt}</span>
                {ts_html}
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )





    def _render_nc_ai_bubble(
        text: str,
        ts: str = "",
        answer_card_key: str = "",
    ) -> None:
        body = (text or "").strip()
        if not body:
            return

        body = re.sub(r"<[^>]+>", "", body)
        # =========================
        # Highlight Engine
        # =========================

        def apply_highlights(s: str) -> str:

            # == highlighted text ==
            s = re.sub(
                r"==(.+?)==",
                r'<span style="background:#fef08a; padding:2px 5px; border-radius:6px; font-weight:600;">\1</span>',
                s,
                flags=re.DOTALL
            )

            # **important**
            s = re.sub(
                r"\*\*(.+?)\*\*",
                r'<span style="color:#111827; font-weight:800;">\1</span>',
                s,
                flags=re.DOTALL
            )

            # `inline code`
            s = re.sub(
                r"`(.+?)`",
                r'<span style="background:#f3f4f6; padding:2px 6px; border-radius:6px; font-family:monospace;">\1</span>',
                s,
                flags=re.DOTALL
            )

            return s

        body = apply_highlights(body)

        answer_container = (
            st.container(border=True, key=answer_card_key)
            if answer_card_key
            else st.container(border=True)
        )
        with answer_container:
            st.markdown(body, unsafe_allow_html=True)

            if ts:
                st.markdown(
                    f"""
                    <div style="
                        margin-top:10px;
                        text-align:right;
                        color:#64748b;
                        font-size:11px;
                    ">
                        {ts}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )






    


    




    def _looks_like_live_local_query(text: str) -> bool:
        s = (text or "").strip().lower()
        phrases = {
            "water rate", "electricity rate", "near me",
        }
        words = set(re.findall(r"[a-z0-9]+", s))
        markers = {
            "today", "current", "latest", "now", "gas", "petrol", "diesel",
            "price", "rate", "cost", "weather", "temperature", "maryland",
            "dc", "usa", "local",
        }
        return bool(words & markers) or any(phrase in s for phrase in phrases)

    def _looks_like_ini_version_query(text: str) -> bool:
        s = re.sub(r"[^a-z0-9. ]+", " ", (text or "").lower()).strip()
        return bool(
            re.search(r"\bv0\.1\.4\b", s)
            or re.search(r"\b(your|ini|yourself)\b.*\b(version|update|release|improved)\b", s)
            or re.search(r"\b(version|update|release)\b.*\b(your|ini|yourself)\b", s)
        )

    def _is_ambiguous_context_followup(text: str) -> bool:
        s = re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()
        continuation = re.sub(
            r"^(?:so|and|okay|ok|well|then)\s+",
            "",
            s,
        ).strip()
        return bool(
            continuation in {
                "what else", "anything else", "tell me more", "what more",
                "go on", "continue",
            }
            or re.match(r"^(more|what|how) (about|on) (it|this|that|the topic)$", s)
        )

    def _latest_meaningful_chat_topic() -> str:
        """Recover the active subject while ignoring ambiguous follow-up branches."""
        for item in reversed(st.session_state.chat_branch_answers or []):
            if not isinstance(item, dict):
                continue
            if item.get("kind") == "direct":
                direct_payload = item.get("direct_answer") or {}
                if (
                    isinstance(direct_payload, dict)
                    and direct_payload.get("intent") in {
                        "context_topic_correction",
                        "context_topic_correction_accepted",
                    }
                ):
                    continue
            interrogate_payload = item.get("interrogate") or {}
            if (
                item.get("kind") == "interrogate"
                and isinstance(interrogate_payload, dict)
                and interrogate_payload.get("intent") == "clarify"
            ):
                # Older builds could persist a full Question Map even though
                # the intent layer had classified the message as clarification.
                continue
            candidate = str(item.get("topic") or "").strip()
            if candidate and not _is_ambiguous_context_followup(candidate):
                return re.sub(
                    r"^(?:please\s+)?(?:generate|create|build|make)\s+(?:me\s+)?(?:a\s+)?(?:question map|qmap)\s+(?:for|on|about)\s+",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                ).strip() or candidate

        for candidate in (
            st.session_state.get("chat_root_topic"),
            (st.session_state.get("chat") or {}).get("topic"),
        ):
            candidate = str(candidate or "").strip()
            if candidate and not _is_ambiguous_context_followup(candidate):
                return candidate
        return ""

    def _latest_structured_chat_topic() -> str:
        """Return the subject that supplied the active structured context."""
        for item in reversed(st.session_state.chat_branch_answers or []):
            if not isinstance(item, dict) or item.get("kind") != "interrogate":
                continue
            candidate = str(item.get("topic") or "").strip()
            if candidate:
                return candidate
        return str(st.session_state.get("chat_root_topic") or "").strip()

    def _active_topic_context_candidates() -> List[str]:
        """Collect short subject names from the latest structured response."""
        candidates: List[str] = []
        structured_items = [
            item
            for item in reversed(st.session_state.chat_branch_answers or [])
            if isinstance(item, dict) and item.get("kind") == "interrogate"
        ]
        if not structured_items and st.session_state.chat_root_intro:
            structured_items = [
                {
                    "topic": st.session_state.chat_root_topic,
                    "intro": st.session_state.chat_root_intro,
                }
            ]

        for item in structured_items[:1]:
            topic = str(item.get("topic") or "").strip()
            if topic:
                candidates.append(topic)

            intro = str(item.get("intro") or "").strip()
            if not intro:
                continue
            profile_rows, _ = extract_topic_profile(intro)
            for label, value in profile_rows:
                normalized_label = re.sub(r"[^a-z]+", " ", label.lower()).strip()
                if normalized_label not in {"subject", "related topics"}:
                    continue
                candidates.extend(
                    part.strip()
                    for part in re.split(r"[;,|]", value or "")
                    if part.strip()
                )

        deduplicated: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = re.sub(r"[^a-z0-9]+", " ", candidate.lower()).strip()
            if key and key not in seen:
                seen.add(key)
                deduplicated.append(candidate)
        return deduplicated

    def _latest_assistant_conversation_reply() -> str:
        """Return the latest conversational answer for short-reply resolution."""
        for item in reversed(st.session_state.chat_branch_answers or []):
            if not isinstance(item, dict) or item.get("kind") != "direct":
                continue
            payload = item.get("direct_answer") or {}
            if not isinstance(payload, dict):
                continue
            if str(payload.get("response_mode") or "").lower() == "conversation":
                text = str(payload.get("text") or "").strip()
                if text:
                    return text

        payload = st.session_state.get("chat_direct_answer")
        if isinstance(payload, dict) and str(payload.get("response_mode") or "").lower() == "conversation":
            return str(payload.get("text") or "").strip()
        return ""

    def _looks_like_answer_to_last_question(text: str, previous_reply: str) -> bool:
        """Resolve natural fragments against InI's immediately preceding question."""
        s = re.sub(r"[^a-z0-9+#. -]+", " ", (text or "").lower()).strip()
        words = re.findall(r"[a-z0-9+#.-]+", s)
        if not previous_reply or "?" not in previous_reply or not (0 < len(words) <= 14):
            return False
        if _is_explicit_qm_prompt(text) or re.match(
            r"^(new topic|teach me|explain|define|compare|generate|create|build|make)\b", s
        ):
            return False

        contextual_starts = (
            "yes", "no", "yeah", "nope", "maybe", "probably", "not really",
            "quite", "very", "really", "pretty", "slightly", "a little",
            "too ", "at ", "in ", "on ", "because ", "mostly ", "just ",
        )
        feeling_words = {
            "comfortable", "uncomfortable", "fine", "good", "bad", "better",
            "worse", "hot", "cold", "tired", "busy", "okay", "ok",
        }
        return s.startswith(contextual_starts) or bool(set(words) & feeling_words) or len(words) == 1

    def _dedupe_followups(items: list[str]) -> list[str]:
        out: list[str] = []
        seen = set()
        for x in items or []:
            item = (x or "").strip()
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def _collect_active_nc_followups() -> list[str]:
        candidates: list[str] = []

        direct_payload = st.session_state.chat_direct_answer
        if isinstance(direct_payload, dict):
            candidates.extend(direct_payload.get("followups") or [])

        intro_text = (st.session_state.chat_intro or "").strip()
        if intro_text:
            _, intro_followups = split_answer_and_embedded_followups(intro_text)
            candidates.extend(intro_followups)

        for vals in (st.session_state.chat_followups or {}).values():
            if isinstance(vals, list):
                candidates.extend(vals)

        for item in st.session_state.chat_branch_answers or []:
            if not isinstance(item, dict):
                continue

            kind = (item.get("kind") or "").strip().lower()

            if kind == "direct":
                direct_payload = item.get("direct_answer") or {}
                if isinstance(direct_payload, dict):
                    candidates.extend(direct_payload.get("followups") or [])

            elif kind == "interrogate":
                intro = (item.get("intro") or "").strip()
                if intro:
                    _, intro_followups = split_answer_and_embedded_followups(intro)
                    candidates.extend(intro_followups)

                for vals in (item.get("followups") or {}).values():
                    if isinstance(vals, list):
                        candidates.extend(vals)

        return _dedupe_followups(candidates)

    def _resolve_typed_followup(prompt_text: str) -> str:
        raw = (prompt_text or "").strip()
        if not raw:
            return raw

        candidates = _collect_active_nc_followups()
        if not candidates:
            return raw

        # Numeric selection: "2" or "2."
        m = re.match(r"^\s*(\d+)\.?\s*$", raw)
        if m:
            idx = int(m.group(1))
            if 1 <= idx <= len(candidates):
                return candidates[idx - 1]

        raw_norm = re.sub(r"\s+", " ", raw.lower()).strip()

        # Partial/full text match
        if len(raw_norm) >= 4:
            for cand in candidates:
                cand_norm = re.sub(r"\s+", " ", cand.lower()).strip()
                if raw_norm == cand_norm or raw_norm in cand_norm or cand_norm in raw_norm:
                    return cand

        return raw

    def _refresh_chat_user_profile(current_text: str = "") -> Dict[str, Any]:
        """Remember a self-declared identity as chat context, never as authentication."""
        profile = dict(st.session_state.get("chat_user_profile") or {})
        history = [
            str(item.get("text") or "")
            for item in (st.session_state.get("chat_query_log") or [])
            if isinstance(item, dict)
        ]
        history.append(current_text or "")
        normalized_turns = [
            re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()
            for value in history
        ]

        latest_normalized = normalized_turns[-1] if normalized_turns else ""
        introduced_name = re.match(
            r"^(?:i am|im|my name is|you can call me|call me)\s+"
            r"([a-z][a-z0-9 -]{0,39})$",
            latest_normalized,
        )
        non_name_words = {
            "only", "just", "checking", "testing", "trying", "ready", "fine",
            "okay", "ok", "here", "back", "done", "tired", "happy", "sad",
            "going", "working", "learning", "asking", "wondering",
        }
        introduced_words = (
            introduced_name.group(1).split() if introduced_name else []
        )
        if (
            introduced_name
            and 1 <= len(introduced_words) <= 4
            and not (set(introduced_words) & non_name_words)
        ):
            display_name = " ".join(
                part.capitalize() for part in introduced_words
            )
            profile["preferred_name"] = display_name
            profile["identity_source"] = "self_reported"

        creator_declared = any(
            re.search(r"\bi am\s+sid\b.*\b(?:your\s+)?creator\b", value)
            for value in normalized_turns
        )
        sudipto_declared = any(value == "sudipto" for value in normalized_turns)
        if creator_declared:
            profile.update(
                {
                    "full_name": "Sudipto",
                    "preferred_name": "Sid",
                    "relationship": "creator",
                    "identity_source": "self_reported",
                }
            )
        elif sudipto_declared and profile.get("preferred_name") == "Sid":
            profile["full_name"] = "Sudipto"

        st.session_state.chat_user_profile = profile
        return profile

    def _chat_identity_answer(
        text: str,
        profile: Dict[str, Any],
    ) -> Optional[str]:
        normalized = re.sub(r"[^a-z0-9 ']+", " ", (text or "").lower()).strip()
        full_name = str(profile.get("full_name") or "").strip()
        preferred_name = str(profile.get("preferred_name") or "").strip()
        if full_name and re.search(
            r"\b(?:do you (?:know|remember)|what(?:'s| is)|tell me)\s+my\s+(?:full\s+)?name\b",
            normalized,
        ):
            preferred_detail = (
                f", and you prefer to be called {preferred_name}" if preferred_name else ""
            )
            return (
                f"You identified yourself to me as {full_name}{preferred_detail}. "
                "I remember that within this conversation."
            )
        if preferred_name and re.search(r"\bi am\s+sid\b.*\bcreator\b", normalized):
            return (
                f"Yes, {preferred_name}. I remember that you identified yourself as my creator, "
                f"{full_name or preferred_name}."
            )
        return None

    def _is_topic_recommendation_request(text: str) -> bool:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()
        return bool(
            re.search(
                r"^(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?"
                r"(?:suggest|recommend)(?:\s+me)?\s+(?:a|one|some)\s+"
                r"(?:topic|subject)(?:\s+to\s+(?:learn|study|explore))?$",
                normalized,
            )
        )

    def _topic_recommendation_copy(topic: str) -> str:
        normalized_topic = (topic or "").strip().casefold()
        if normalized_topic == "kubernetes":
            return (
                "Try **Kubernetes**. It is a practical topic that connects containers, deployment, "
                "scaling, and modern cloud infrastructure, and it is within one of my stronger "
                "learning areas. If it interests you, ask me to generate a Question Map for "
                "Kubernetes."
            )
        if normalized_topic == "spatial artificial intelligence":
            return (
                "Try **spatial artificial intelligence**. It connects perception, mapping, computer "
                "vision, robotics, and reasoning about physical environments. If it interests you, "
                "ask me to generate a Question Map for spatial artificial intelligence."
            )
        if normalized_topic == "quantum computing":
            return (
                "Try **quantum computing**. It offers a structured path through qubits, superposition, "
                "entanglement, algorithms, and hardware limitations. If it interests you, ask me to "
                "generate a Question Map for quantum computing."
            )
        return (
            "Try **gradient descent**. It is a focused starting point that connects calculus, "
            "machine learning, and practical model training, and it is within one of my stronger "
            "learning areas. If it interests you, ask me to generate a Question Map for gradient "
            "descent."
        )

    def _next_topic_recommendation(current_topic: str) -> str:
        sequence = [
            "gradient descent",
            "Kubernetes",
            "spatial artificial intelligence",
            "quantum computing",
        ]
        normalized_current = (current_topic or "").strip().casefold()
        for index, candidate in enumerate(sequence):
            if candidate.casefold() == normalized_current:
                return sequence[(index + 1) % len(sequence)]
        return sequence[0]

    def _local_conversation_answer(
        text: str,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Handle elementary dialogue acts before any remote backend routing."""
        normalized = re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()
        active_profile = profile or {}
        preferred_name = str(active_profile.get("preferred_name") or "").strip()
        address = f", {preferred_name}" if preferred_name else ""

        introduced = re.match(
            r"^(?:i am|im|my name is|you can call me|call me)\s+"
            r"([a-z][a-z0-9 -]{0,39})$",
            normalized,
        )
        non_name_words = {
            "only", "just", "checking", "testing", "trying", "ready", "fine",
            "okay", "ok", "here", "back", "done", "tired", "happy", "sad",
            "going", "working", "learning", "asking", "wondering",
        }
        introduced_words = introduced.group(1).split() if introduced else []
        if (
            introduced
            and 1 <= len(introduced_words) <= 4
            and not (set(introduced_words) & non_name_words)
        ):
            name = " ".join(part.capitalize() for part in introduced_words)
            return f"Nice to meet you, {name}. I’ll remember that in this conversation."

        if normalized in {
            "cool", "nice", "awesome", "wonderful", "perfect", "great",
            "all good", "sounds good", "that works",
        }:
            return f"Glad to hear it{address}."

        if normalized in {
            "whats going on", "what is going on", "so whats going on",
            "so what is going on", "whats up", "what is up", "so whats up",
        }:
            return f"I’m here with you{address}. What’s going on?"

        if _is_topic_recommendation_request(normalized):
            return _topic_recommendation_copy("gradient descent")

        if re.search(
            r"\b(what|which).*(topics?|subjects?|areas?).*(do you know|can you cover|can you help|support)\b",
            normalized,
        ) or re.search(
            r"\b(what all|which).*(do you know|can you cover).*(topics?|subjects?|areas?)\b",
            normalized,
        ):
            return (
                "I am strongest today at structured learning around artificial intelligence, "
                "machine learning, data science, computer science, software and cloud concepts "
                "such as Kubernetes, quantum computing, and cognitive science. I can discuss "
                "other educational topics too, but the depth and reliability may vary. I am still "
                "in active development, so I can occasionally misunderstand a request or produce "
                "an uneven result. I do not claim verified specialist support for medical, legal, "
                "or financial advice. Give me a topic and I will tell you honestly whether I can "
                "explain it or build a reliable Question Map."
            )

        if normalized in {
            "rest for today", "lets rest for today", "let us rest for today",
            "done for today", "thats all for today", "that is all for today",
            "we are done for today", "call it a day",
        }:
            return f"Of course{address}. Rest well—we can pick this up next time."

        return None

    def _run_new_chat_interrogate(
        topic_text: str,
        show_spinner: bool = True,
    ) -> None:
        # Context-dependent phrases must remain verbatim. Otherwise the fuzzy
        # follow-up resolver can expand "what else" into an older suggested
        # question merely because that question contains the same words.
        if (
            not _is_ambiguous_context_followup(topic_text)
            and not isinstance(st.session_state.get("chat_active_discussion"), dict)
        ):
            topic_text = _resolve_typed_followup(topic_text)
        display_topic_text = topic_text.strip()
        interpreted_turn = interpret_turn(display_topic_text)
        semantic_topic_text = (
            interpreted_turn.semantic_text
            if interpreted_turn.has_substantive_text
            else display_topic_text
        )
        active_capability_boundary = st.session_state.get(
            "chat_active_capability_boundary"
        )
        normalized_boundary_reply = re.sub(
            r"[^a-z0-9 ]+",
            " ",
            display_topic_text.lower(),
        ).strip()
        boundary_followup = bool(
            re.match(
                r"^(?:yes|yeah|yep|sure|okay|ok|please|go ahead|do it|"
                r"continue|explain|explain more|tell me more)\b",
                normalized_boundary_reply,
            )
        )
        if isinstance(active_capability_boundary, dict) and boundary_followup:
            blocked_topic = str(
                active_capability_boundary.get("source_topic") or ""
            ).strip()
            if blocked_topic:
                topic_text = blocked_topic
                semantic_topic_text = blocked_topic
        elif assess_capability(display_topic_text) is None:
            st.session_state.chat_active_capability_boundary = None
        context_correction_question = ""
        context_correction_accepted = False
        pending_context_correction = st.session_state.get("chat_pending_context_correction")
        normalized_context_reply = re.sub(
            r"[^a-z0-9 ]+",
            " ",
            display_topic_text.lower(),
        ).strip()
        should_check_context_match = True
        if isinstance(pending_context_correction, dict):
            correction_candidate = str(
                pending_context_correction.get("candidate") or ""
            ).strip()
            normalized_candidate = re.sub(
                r"[^a-z0-9 ]+",
                " ",
                correction_candidate.lower(),
            ).strip()
            if correction_candidate and (
                re.match(r"^(yes|yeah|yep|correct|right|sure|continue|go ahead)\b", normalized_context_reply)
                or normalized_context_reply == normalized_candidate
            ):
                topic_text = correction_candidate
                semantic_topic_text = correction_candidate
                context_correction_accepted = True
                should_check_context_match = False
            elif re.match(r"^(no|nope|incorrect|neither)\b", normalized_context_reply):
                should_check_context_match = False
            st.session_state.chat_pending_context_correction = None
        if should_check_context_match:
            contextual_match = find_contextual_topic_match(
                display_topic_text,
                _active_topic_context_candidates(),
            )
            if contextual_match:
                correction_candidate = str(
                    contextual_match.get("candidate") or ""
                ).strip()
                active_topic = _latest_structured_chat_topic()
                if correction_candidate:
                    normalized_active_topic = re.sub(
                        r"[^a-z0-9 ]+",
                        " ",
                        active_topic.lower(),
                    ).strip()
                    normalized_correction = re.sub(
                        r"[^a-z0-9 ]+",
                        " ",
                        correction_candidate.lower(),
                    ).strip()
                    context_correction_question = (
                        f"Did you mean {correction_candidate}"
                        + (
                            f" in relation to {active_topic}"
                            if active_topic and normalized_active_topic != normalized_correction
                            else ""
                        )
                        + "? I want to confirm before answering."
                    )
                    st.session_state.chat_pending_context_correction = {
                        "candidate": correction_candidate,
                        "source_query": display_topic_text,
                    }
        prior_response_mode = _latest_response_mode()
        qm_confirmation_accepted = False
        qm_discussion_topic = ""
        start_discussion_topic = ""
        discussion_answer_request: Optional[Dict[str, Any]] = None
        discussion_freeform_followup = False
        contextual_previous_reply = _latest_assistant_conversation_reply()
        chat_user_profile = _refresh_chat_user_profile(display_topic_text)
        local_conversation_answer = _local_conversation_answer(
            display_topic_text,
            chat_user_profile,
        )
        topic_recommendation_request = _is_topic_recommendation_request(
            display_topic_text
        )
        recommended_topic = (
            "gradient descent" if topic_recommendation_request else ""
        )
        alternate_topic_recommendation = ""
        ini_product_answer = _chat_identity_answer(
            display_topic_text,
            chat_user_profile,
        ) or answer_ini_product_query(display_topic_text)
        ini_version_query = _looks_like_ini_version_query(display_topic_text)
        contextual_followup_topic = (
            _latest_meaningful_chat_topic()
            if (
                _is_ambiguous_context_followup(display_topic_text)
                and prior_response_mode != "conversation"
            )
            else ""
        )
        active_carm_context = st.session_state.get("chat_active_carm_context")
        used_active_carm_context = False

        pending_qm = st.session_state.get("chat_pending_qm_confirmation")
        if isinstance(pending_qm, dict):
            normalized_reply = re.sub(r"[^a-z0-9 ]+", " ", display_topic_text.lower()).strip()
            original_topic = (pending_qm.get("topic") or "").strip()
            if re.match(r"^(yes|yeah|yep|sure|okay|ok|please|go ahead|do it|generate)\b", normalized_reply):
                if original_topic:
                    topic_text = original_topic
                    semantic_topic_text = original_topic
                    qm_confirmation_accepted = True
            elif re.match(
                r"^(?:no|nope|not this|something else|anything else|another|"
                r"another one|different|different topic|suggest another)\b",
                normalized_reply,
            ):
                alternate_topic_recommendation = _next_topic_recommendation(
                    original_topic
                )
                recommended_topic = alternate_topic_recommendation
            if qm_confirmation_accepted:
                st.session_state.chat_study_mode_established = True
            st.session_state.chat_pending_qm_confirmation = None

        pending_discussion_action = st.session_state.get("chat_pending_discussion_action")
        if isinstance(pending_discussion_action, dict):
            action_reply = re.sub(r"[^a-z0-9 ]+", " ", display_topic_text.lower()).strip()
            action_topic = (pending_discussion_action.get("topic") or "").strip()
            if re.match(r"^(generate|question map|create|build|make)\b", action_reply):
                topic_text = action_topic
                semantic_topic_text = action_topic
                qm_confirmation_accepted = True
                st.session_state.chat_study_mode_established = True
            elif re.match(r"^(continue discussion|continue|discuss|discussion)\b", action_reply):
                start_discussion_topic = action_topic
                st.session_state.chat_study_mode_established = True
            st.session_state.chat_pending_discussion_action = None

        active_discussion = st.session_state.get("chat_active_discussion")
        if isinstance(active_discussion, dict) and not start_discussion_topic:
            questions = list(active_discussion.get("questions") or [])[:3]
            normalized_discussion_reply = re.sub(
                r"[^a-z0-9 ]+", " ", display_topic_text.lower()
            ).strip()
            selected_index: Optional[int] = None
            if re.fullmatch(r"[1-3]", normalized_discussion_reply):
                candidate = int(normalized_discussion_reply) - 1
                if candidate < len(questions):
                    selected_index = candidate
            elif normalized_discussion_reply == "next question":
                selected_index = min(int(active_discussion.get("current_index", -1)) + 1, len(questions) - 1)
            elif normalized_discussion_reply in {"previous question", "previous answer"}:
                selected_index = max(int(active_discussion.get("current_index", 0)) - 1, 0)
            elif normalized_discussion_reply == "next question set":
                next_set = int(active_discussion.get("set_number", 1)) + 1
                active_discussion.update(
                    {
                        "set_number": next_set,
                        "questions": _discussion_questions_for(
                            active_discussion.get("topic") or "this topic",
                            next_set,
                        ),
                        "current_index": -1,
                        "awaiting_option_index": None,
                    }
                )
                st.session_state.chat_active_discussion = active_discussion
                start_discussion_topic = active_discussion.get("topic") or "this topic"
            elif normalized_discussion_reply == "explain more":
                selected_index = int(active_discussion.get("current_index", 0))
                if 0 <= selected_index < len(questions):
                    discussion_answer_request = {
                        "index": selected_index,
                        "question": questions[selected_index],
                        "expand": True,
                    }
            elif isinstance(active_discussion.get("awaiting_option_index"), int):
                selected_index = int(active_discussion.get("awaiting_option_index"))
                if 0 <= selected_index < len(questions):
                    discussion_answer_request = {
                        "index": selected_index,
                        "question": questions[selected_index],
                        "option": display_topic_text,
                    }
                    active_discussion["awaiting_option_index"] = None

            if selected_index is not None and discussion_answer_request is None:
                if selected_index == 0 and "—" in questions[selected_index]:
                    active_discussion["awaiting_option_index"] = selected_index
                    active_discussion["current_index"] = selected_index
                    st.session_state.chat_active_discussion = active_discussion
                    discussion_answer_request = {
                        "index": selected_index,
                        "question": questions[selected_index],
                        "clarify_only": True,
                    }
                else:
                    discussion_answer_request = {
                        "index": selected_index,
                        "question": questions[selected_index],
                    }
                    if normalized_discussion_reply in {"previous question", "previous answer"}:
                        cached_answer = (active_discussion.get("answers") or {}).get(
                            str(selected_index)
                        )
                        if cached_answer:
                            discussion_answer_request["reuse_answer"] = cached_answer

            if (
                discussion_answer_request is None
                and not start_discussion_topic
                and re.search(
                    r"\b(you|your|yours|we|our|ours|this|that|it)\b",
                    normalized_discussion_reply,
                )
                and len(normalized_discussion_reply.split()) <= 24
            ):
                discussion_freeform_followup = True

        if not discussion_freeform_followup:
            general_reply = re.sub(
                r"[^a-z0-9 ]+", " ", display_topic_text.lower()
            ).strip()
            if (
                re.search(r"\b(you|your|yours|we|our|ours|this|that|it)\b", general_reply)
                and len(general_reply.split()) <= 24
                and not re.search(
                    r"\b(question map|qmap|generate|create|build|teach me|explain)\b",
                    general_reply,
                )
            ):
                discussion_freeform_followup = True

        if (
            not discussion_freeform_followup
            and not qm_confirmation_accepted
            and _looks_like_answer_to_last_question(
                display_topic_text,
                contextual_previous_reply,
            )
        ):
            discussion_freeform_followup = True

        if (
            _is_ambiguous_context_followup(display_topic_text)
            and prior_response_mode == "conversation"
            and not qm_confirmation_accepted
        ):
            discussion_freeform_followup = True

        # A short reply such as "VSCode" answers InI's previous MCP-host
        # clarification; it must not be misrouted as a brand-new learning topic.
        pending_context = st.session_state.get("chat_pending_context_clarification")
        if isinstance(pending_context, dict):
            reply_words = re.findall(r"[A-Za-z0-9+#.-]+", display_topic_text)
            if 0 < len(reply_words) <= 14:
                original_request = (pending_context.get("original_request") or "").strip()
                topic_text = (
                    f"{original_request} The application or tool specified by the user is "
                    f"{display_topic_text}."
                ).strip()
            st.session_state.chat_pending_context_clarification = None

        # CARM keeps the active practical goal across natural short replies.
        # This is intentionally semantic/structural rather than a list of
        # expected values such as operating systems or transport names.
        elif isinstance(active_carm_context, dict):
            reply_words = re.findall(r"[A-Za-z0-9+#.-]+", display_topic_text)
            explicit_new_request = bool(
                re.match(
                    r"^(what|who|why|when|where|how|explain|teach|compare|define|tell me|new topic)\b",
                    display_topic_text,
                    flags=re.IGNORECASE,
                )
                or "?" in display_topic_text
            )
            contextual_short_reply = (
                0 < len(reply_words) <= 14
                and not explicit_new_request
            )

            if contextual_short_reply:
                resolved_request = (
                    active_carm_context.get("resolved_request")
                    or active_carm_context.get("original_request")
                    or ""
                ).strip()
                previous_tail = (active_carm_context.get("last_answer") or "").strip()[-1600:]
                topic_text = (
                    f"Continue this active practical request: {resolved_request}\n\n"
                    f"The end of InI's previous answer was:\n{previous_tail}\n\n"
                    f"The user's latest natural-language reply is: {display_topic_text}\n"
                    "Interpret that reply as context for the active request, answer what it implies, "
                    "and do not treat it as a new standalone learning topic."
                ).strip()
                used_active_carm_context = True
            else:
                st.session_state.chat_active_carm_context = None

        if not topic_text.strip():
            return
        capability_boundary = assess_capability(topic_text)
        if capability_boundary:
            # A boundary ends any half-finished learning route. A later
            # confirmation such as "go ahead" must not bypass it.
            st.session_state.chat_active_capability_boundary = {
                "domain": capability_boundary.domain,
                "source_topic": topic_text,
            }
            st.session_state.chat_pending_context_clarification = None
            st.session_state.chat_pending_qm_confirmation = None
            st.session_state.chat_pending_discussion_action = None
        try:
            current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

            # Recording is independent of intent and response generation. A
            # greeting, typo, repeated message, or failed request remains part
            # of the user's permanent session record exactly as submitted.
            _record_chat_query(display_topic_text, "interrogate")
            current_sid = _persist_new_chat_session(current_sid)

            st.session_state.chat_popup_sid = None
            _reset_query_to_page("chat")

            spinner_context = (
                st.spinner("Generating question map... may take some time.")
                if show_spinner
                else nullcontext()
            )
            with spinner_context:
                if capability_boundary:
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "capability_boundary",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "unsupported_domain",
                        "needs_clarification": False,
                        "suppress_profile": True,
                        "reply": capability_boundary.reply,
                    }
                elif context_correction_question:
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "context_topic_correction",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "active_topic",
                        "needs_clarification": False,
                        "suppress_profile": True,
                        "reply": context_correction_question,
                    }
                elif alternate_topic_recommendation:
                    st.session_state.chat_pending_qm_confirmation = {
                        "topic": alternate_topic_recommendation,
                    }
                    data = {
                        "categories": {},
                        "followups": ["Generate Question Map"],
                        "intent": "topic_recommendation",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "conversation",
                        "needs_clarification": True,
                        "hide_clarification_title": True,
                        "suppress_profile": False,
                        "reply": _topic_recommendation_copy(
                            alternate_topic_recommendation
                        ),
                    }
                elif local_conversation_answer:
                    if topic_recommendation_request:
                        st.session_state.chat_pending_qm_confirmation = {
                            "topic": "gradient descent",
                        }
                    data = {
                        "categories": {},
                        "followups": (
                            ["Generate Question Map"]
                            if topic_recommendation_request
                            else []
                        ),
                        "intent": "local_conversation",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "conversation",
                        "needs_clarification": topic_recommendation_request,
                        "hide_clarification_title": topic_recommendation_request,
                        "suppress_profile": False,
                        "reply": local_conversation_answer,
                    }
                elif ini_product_answer:
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "ini_product_info",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "ini_product",
                        "needs_clarification": False,
                        "suppress_profile": False,
                        "reply": ini_product_answer,
                    }
                elif ini_version_query:
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "ini_version_info",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "ini_product",
                        "needs_clarification": False,
                        "suppress_profile": False,
                        "reply": (
                            "InI.ai v0.1.4 improves conversational intelligence and context switching, "
                            "adds guided Discussion Mode, preserves every submitted query, refines the "
                            "response-card experience and generation states, strengthens the First "
                            "Conversation Experience, and polishes InI branding and navigation. It was "
                            "released on July 17, 2026."
                        ),
                    }
                elif start_discussion_topic:
                    existing_discussion = st.session_state.get("chat_active_discussion")
                    if not isinstance(existing_discussion, dict) or (
                        existing_discussion.get("topic") != start_discussion_topic
                    ):
                        existing_discussion = {
                            "topic": start_discussion_topic,
                            "set_number": 1,
                            "questions": _discussion_questions_for(start_discussion_topic, 1),
                            "current_index": -1,
                            "awaiting_option_index": None,
                            "answers": {},
                        }
                    st.session_state.chat_active_discussion = existing_discussion
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "continue_discussion",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "",
                        "needs_clarification": False,
                        "reply": "Choose one of the three discussion directions below, or type its number in the input bar.",
                        "suppress_profile": True,
                    }
                elif discussion_answer_request:
                    discussion_topic = (
                        (st.session_state.get("chat_active_discussion") or {}).get("topic")
                        or "this topic"
                    )
                    selected_question = discussion_answer_request.get("question") or ""
                    if discussion_answer_request.get("clarify_only"):
                        data = {
                            "categories": {},
                            "followups": [],
                            "intent": "discussion_option_clarification",
                            "should_answer_direct": False,
                            "response_mode": "conversation",
                            "context_intent": "",
                            "needs_clarification": False,
                            "reply": "Which direction would you like—core concepts, mechanisms, applications, or limitations? Type the option below.",
                            "suppress_profile": True,
                        }
                    elif discussion_answer_request.get("reuse_answer"):
                        data = {
                            "categories": {},
                            "followups": [],
                            "intent": "discussion_answer",
                            "should_answer_direct": False,
                            "response_mode": "discussion_answer",
                            "context_intent": "",
                            "needs_clarification": False,
                            "reply": discussion_answer_request.get("reuse_answer") or "",
                        }
                    else:
                        line_limit = 20 if discussion_answer_request.get("expand") else 10
                        option_context = discussion_answer_request.get("option") or ""
                        data = {
                            "categories": {},
                            "followups": [],
                            "intent": "discussion_answer",
                            "should_answer_direct": True,
                            "response_mode": "discussion_answer",
                            "context_intent": "",
                            "needs_clarification": False,
                            "direct_answer_prompt": (
                                f"Answer this discussion question about {discussion_topic}: {selected_question}\n"
                                + (f"The user selected this direction: {option_context}.\n" if option_context else "")
                                + f"Use no more than {line_limit} concise lines. Be clear, specific, and conversational."
                            ),
                        }
                elif qm_discussion_topic:
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "topic_discussion",
                        "should_answer_direct": True,
                        "response_mode": "conversation",
                        "context_intent": "",
                        "needs_clarification": False,
                        "direct_answer_prompt": (
                            "Hold a natural, intelligent conversation about "
                            f"{qm_discussion_topic}. Give a concise orientation, then ask exactly "
                            "one useful question about which aspect interests the user. Do not create "
                            "a Question Map and do not sound like a textbook."
                        ),
                    }
                    topic_text = qm_discussion_topic
                elif contextual_followup_topic:
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "context_clarification",
                        "should_answer_direct": False,
                        "response_mode": "conversation",
                        "context_intent": "active_topic",
                        "needs_clarification": True,
                        "suppress_profile": True,
                        "reply": (
                            f"What would you like to explore further about {contextual_followup_topic}—"
                            "how it works, its performance, practical uses, or another aspect?"
                        ),
                    }
                elif discussion_freeform_followup:
                    discussion_topic = (
                        (st.session_state.get("chat_active_discussion") or {}).get("topic")
                        or st.session_state.chat.get("topic")
                        or st.session_state.get("chat_root_topic")
                        or "the active conversation"
                    )
                    data = {
                        "categories": {},
                        "followups": [],
                        "intent": "discussion_freeform_followup",
                        "should_answer_direct": True,
                        "response_mode": "conversation",
                        "context_intent": "active_discussion",
                        "needs_clarification": False,
                        "suppress_profile": False,
                        "direct_answer_prompt": (
                            f"Continue the active conversation about {discussion_topic}. "
                            + (
                                f"InI's immediately preceding response was: {contextual_previous_reply}\n"
                                if contextual_previous_reply
                                else ""
                            )
                            +
                            f"The user said: {display_topic_text}\n"
                            "Respond naturally to what they mean in this conversation. Preserve context, "
                            "use a warm concise tone, and briefly bridge the change from the previous topic "
                            "when the user moves back into casual conversation. Do not sound as though a new "
                            "conversation has started. Do not create an Introduction, Suggested Follow-ups, "
                            "or Question Map. If the message is about you, answer as InI rather than defining "
                            "the user's words."
                        ),
                    }
                else:
                    data = fetch_interrogate(semantic_topic_text)
                if context_correction_accepted and not (data.get("categories") or {}):
                    data["intent"] = "context_topic_correction_accepted"
                    data["context_intent"] = "active_topic"
                    data["suppress_profile"] = True
                st.session_state.chat["topic"] = semantic_topic_text

                if "chat_bottom_topic_input" in st.session_state:
                    del st.session_state["chat_bottom_topic_input"]

                has_existing_root = bool(
                    current_sid
                    and st.session_state.chat_loaded_sid == current_sid
                    and _session_has_existing_root()
                )

                # -------------------------------------------------
                # Intent-layer / direct-answer / conversational path
                # -------------------------------------------------
                if not (data.get("categories") or {}):
                    followups = data.get("followups") or []
                    intent_name = (data.get("intent") or "").strip().lower()
                    should_answer_direct = bool(data.get("should_answer_direct", False))
                    response_mode = (data.get("response_mode") or "standard").strip().lower()
                    context_intent = (data.get("context_intent") or "").strip().lower()
                    is_live_local_query = (
                        response_mode not in {"carm", "conversation"}
                        and _looks_like_live_local_query(topic_text)
                    )

                    if bool(data.get("needs_clarification")) and response_mode == "carm":
                        st.session_state.chat_pending_context_clarification = {
                            "original_request": display_topic_text,
                            "context_intent": context_intent,
                        }
                    else:
                        st.session_state.chat_pending_context_clarification = None

                    if should_answer_direct:
                        if is_live_local_query:
                            reply = (
                                "I can recognize this as a direct factual query, but live or location-specific "
                                "rates need a current data source. In v0, ask me to explain the topic, or use a "
                                "fully sourced query once live data is connected."
                            )
                            followups = []
                            answer_incomplete = False
                            answer_stop_reason = None
                            mode_name = "focused"
                        else:
                            answer_prompt = (data.get("direct_answer_prompt") or semantic_topic_text).strip()
                            generation_mode = (
                                "conversation" if response_mode == "conversation" else "carm"
                            )
                            direct_resp = fetch_study_full(
                                answer_prompt,
                                mode=generation_mode,
                                max_rounds=1 if generation_mode == "conversation" else 2,
                            )
                            reply = (direct_resp.get("answer") or "").strip() or "No answer generated."
                            followups = direct_resp.get("followups") or followups
                            answer_incomplete = bool(direct_resp.get("incomplete"))
                            answer_stop_reason = direct_resp.get("stop_reason") or None
                            mode_name = generation_mode
                    else:
                        reply = (data.get("reply") or "").strip() or "Send a topic to explore."
                        answer_incomplete = False
                        answer_stop_reason = None
                        mode_name = "focused"

                    # Repair a rare malformed contraction produced by compact
                    # conversational generations before it reaches the UI.
                    reply = re.sub(r"\bI[’']l\b", "I'll", reply)

                    show_followups = (
                        (should_answer_direct or bool(data.get("needs_clarification")))
                        and not is_live_local_query
                    )

                    direct_payload = {
                        "prompt": display_topic_text,
                        "text": reply,
                        "incomplete": answer_incomplete,
                        "stop_reason": answer_stop_reason,
                        "mode": mode_name,
                        "followups": followups,
                        "intent": (
                            "topic_recommendation"
                            if recommended_topic
                            else intent_name
                        ),
                        "should_answer_direct": should_answer_direct,
                        "response_mode": response_mode,
                        "context_intent": context_intent,
                        "show_followups": show_followups,
                        "needs_clarification": bool(data.get("needs_clarification")),
                        "profile_prompt": (
                            recommended_topic
                            if recommended_topic
                            else qm_discussion_topic or display_topic_text
                        ),
                        "suppress_profile": bool(data.get("suppress_profile", False)),
                        "show_action_buttons": bool(qm_discussion_topic),
                        "clarification_title": (
                            "Choose how to continue" if qm_discussion_topic else ""
                        ),
                        "hide_clarification_title": bool(
                            data.get("hide_clarification_title", False)
                        ),
                        "discussion_answer": (
                            {
                                "topic": (
                                    (st.session_state.get("chat_active_discussion") or {}).get("topic")
                                    or ""
                                ),
                                "question": discussion_answer_request.get("question") or "",
                                "index": int(discussion_answer_request.get("index", 0)),
                                "count": len(
                                    (st.session_state.get("chat_active_discussion") or {}).get("questions")
                                    or []
                                ),
                                "expanded_answer": bool(discussion_answer_request.get("expand")),
                            }
                            if discussion_answer_request and not discussion_answer_request.get("clarify_only")
                            else None
                        ),
                        "ts": now_label(),
                    }

                    if qm_discussion_topic:
                        direct_payload["followups"] = [
                            "Generate a Question Map",
                            "Continue Discussion",
                        ]
                        direct_payload["show_followups"] = True
                        st.session_state.chat_pending_discussion_action = {
                            "topic": qm_discussion_topic,
                        }
                    elif discussion_answer_request and not discussion_answer_request.get("clarify_only"):
                        active_state = st.session_state.get("chat_active_discussion") or {}
                        answer_index = int(discussion_answer_request.get("index", 0))
                        active_state["current_index"] = answer_index
                        active_state["awaiting_option_index"] = None
                        answers = active_state.setdefault("answers", {})
                        answers[str(answer_index)] = reply
                        st.session_state.chat_active_discussion = active_state

                    if (
                        response_mode == "conversation"
                        and intent_name not in {
                            "topic_discussion",
                            "continue_discussion",
                            "discussion_option_clarification",
                            "question_map_confirmation",
                            "context_clarification",
                        }
                    ):
                        st.session_state.chat_study_mode_established = False

                    if response_mode == "carm" and not bool(data.get("needs_clarification")):
                        if used_active_carm_context and isinstance(active_carm_context, dict):
                            base_request = (
                                active_carm_context.get("resolved_request")
                                or active_carm_context.get("original_request")
                                or ""
                            ).strip()
                            resolved_request = (
                                f"{base_request} User additionally specified: {display_topic_text}."
                            ).strip()
                        else:
                            resolved_request = semantic_topic_text

                        st.session_state.chat_active_carm_context = {
                            "original_request": resolved_request,
                            "resolved_request": resolved_request[-2400:],
                            "last_answer": reply[-3200:],
                            "context_intent": context_intent,
                        }
                    elif response_mode != "carm":
                        st.session_state.chat_active_carm_context = None

                    if has_existing_root:
                        _append_nc_message(
                            display_topic_text,
                            direct_payload,
                            "direct",
                        )
                        _persist_new_chat_session(current_sid)
                        st.rerun()
                        return
                    


                    st.session_state.chat["topic"] = display_topic_text
                    st.session_state.chat_root_topic = display_topic_text
                    st.session_state.chat["interrogate"] = None
                    st.session_state.chat["illustrate"] = None
                    st.session_state.chat_intro = ""
                    st.session_state.chat_direct_answer = direct_payload

                    st.session_state.chat_answers = {}
                    st.session_state.chat_followups = {}
                    st.session_state.chat_open_questions = set()
                    st.session_state.chat_visited_questions = set()

                    st.session_state.chat_root_interrogate = None
                    st.session_state.chat_root_illustrate = None
                    st.session_state.chat_root_intro = ""
                    st.session_state.chat_root_direct_answer = direct_payload
                    st.session_state.chat_root_answers = {}
                    st.session_state.chat_root_followups = {}
                    st.session_state.chat_root_open_questions = set()
                    st.session_state.chat_root_visited_questions = set()

                    _persist_new_chat_session(current_sid)
                    st.rerun()
                    return

                # -------------------------------------------------
                # Real topic -> question-map path
                # -------------------------------------------------
                st.session_state.chat_pending_context_clarification = None
                st.session_state.chat_active_carm_context = None
                explicit_qm_request = bool(
                    re.search(
                        r"\b(question\s*map|qmap|qm)\b|\b(generate|create|build|make)\b.*\bmap\b",
                        display_topic_text,
                        flags=re.IGNORECASE,
                    )
                )
                if (
                    has_existing_root
                    and prior_response_mode == "conversation"
                    and not st.session_state.chat_study_mode_established
                    and not explicit_qm_request
                    and not qm_confirmation_accepted
                ):
                    # Apply extraction until the topic stabilizes. Streamlit
                    # can retain an already-imported helper across hot reloads;
                    # repeated application also handles stacked instructions
                    # such as "can you explain artificial intelligence" even
                    # when the first pass removes only "can you".
                    clarification_topic = semantic_topic_text
                    for _ in range(4):
                        extracted_topic = extract_learning_topic(
                            clarification_topic
                        ).strip()
                        if (
                            not extracted_topic
                            or extracted_topic.casefold()
                            == clarification_topic.casefold()
                        ):
                            break
                        clarification_topic = extracted_topic
                    clarification_text = (
                        f"That sounds like a shift to a learning topic. Would you like me to "
                        f"generate a Question Map for {clarification_topic}?"
                    )
                    clarification_payload = {
                        "prompt": display_topic_text,
                        "text": clarification_text,
                        "incomplete": False,
                        "stop_reason": None,
                        "mode": "conversation",
                        "followups": ["Generate Question Map"],
                        "intent": "question_map_confirmation",
                        "should_answer_direct": True,
                        "response_mode": "conversation",
                        "context_intent": "",
                        "show_followups": True,
                        "needs_clarification": True,
                        "suppress_profile": True,
                        "clarification_title": "Question Map",
                        "hide_clarification_title": True,
                        "ts": now_label(),
                    }
                    st.session_state.chat_pending_qm_confirmation = {
                        "topic": clarification_topic,
                    }
                    _append_nc_message(display_topic_text, clarification_payload, "direct")
                    _persist_new_chat_session(current_sid)
                    st.rerun()
                    return
                st.session_state.chat_active_discussion = None
                if has_existing_root:
                    st.session_state.chat_study_mode_established = True
                    intro_resp = fetch_study_full(semantic_topic_text, mode="intro", max_rounds=0)
                    intro = intro_resp.get("answer", "").strip()
                    _append_interrogate_branch(display_topic_text, data, intro)
                    _persist_new_chat_session(current_sid)
                    st.rerun()
                    return

                st.session_state.chat["topic"] = semantic_topic_text
                st.session_state.chat_study_mode_established = True
                st.session_state.chat_root_topic = semantic_topic_text
                st.session_state.chat["interrogate"] = data

                intro_resp = fetch_study_full(semantic_topic_text, mode="intro")
                intro = intro_resp.get("answer", "").strip()

                st.session_state.chat_intro = intro
                st.session_state.chat["illustrate"] = None
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()

                st.session_state.chat_root_interrogate = {
                **data,
                "ts": now_label(),
                }
                st.session_state.chat_root_illustrate = None
                st.session_state.chat_root_intro = intro
                st.session_state.chat_root_answers = {}
                st.session_state.chat_root_followups = {}
                st.session_state.chat_root_open_questions = set()
                st.session_state.chat_root_visited_questions = set()

                _sync_chat_root_snapshot()
                _persist_new_chat_session(current_sid)

            st.rerun()
        except Exception as e:
            st.error(f"Error calling /interrogate: {e}")

    def _run_new_chat_illustrate(
        topic_text: str,
        show_spinner: bool = True,
    ) -> None:
        if not topic_text.strip():
            return
        capability_boundary = assess_capability(topic_text)
        if capability_boundary:
            _run_new_chat_interrogate(topic_text, show_spinner=False)
            return
        try:
            current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid
            _record_chat_query(topic_text, "illustrate")
            current_sid = _persist_new_chat_session(current_sid)

            if current_sid and st.session_state.chat_loaded_sid == current_sid and _session_has_existing_root():
                _run_new_chat_branch_illustrate(topic_text.strip())
                st.rerun()
                return

            st.session_state.chat_popup_sid = None
            _reset_query_to_page("chat")

            spinner_context = (
                st.spinner("Generating illustrations... please wait.")
                if show_spinner
                else nullcontext()
            )
            with spinner_context:
                data = fetch_illustrate(topic_text.strip())
                st.session_state.chat["topic"] = topic_text.strip()
                st.session_state.chat_root_topic = topic_text.strip()
                if "chat_bottom_topic_input" in st.session_state:
                    del st.session_state["chat_bottom_topic_input"]
                st.session_state.chat["illustrate"] = {
                    **data,
                    "ts": now_label(),
                }
                st.session_state.chat["interrogate"] = None
                st.session_state.chat_intro = ""
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()

                st.session_state.chat_root_interrogate = None
                st.session_state.chat_root_illustrate = {
                    **data,
                    "ts": now_label(),
                }
                st.session_state.chat_root_intro = ""
                st.session_state.chat_root_answers = {}
                st.session_state.chat_root_followups = {}
                st.session_state.chat_root_open_questions = set()
                st.session_state.chat_root_visited_questions = set()

                _persist_new_chat_session(current_sid)
            st.rerun()
        except Exception as e:
            st.error(f"Error calling /illustrate: {e}")

    def _looks_like_casual_generation(prompt: str) -> bool:
        raw_prompt = (prompt or "").lower().replace("’", "'").replace("'", "")
        normalized = re.sub(r"[^a-z0-9 ]+", " ", raw_prompt)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        casual_patterns = (
            r"^(hi|hello|hey|hiya|yo|sup|good morning|good afternoon|good evening)\b",
            r"^(how are you|how you doing|how are things|how are things going)\b",
            r"^(hows|how is) (it|life|everything)\b",
            r"^(so )?(whats|what is) (up|going on)\b",
            r"^what are you (doing|up to)\b",
            r"^(thanks|thank you|bye|goodbye|see you)\b",
            r"^(i am|im|my name is|you can call me|call me)\s+[a-z][a-z0-9 -]{0,39}$",
            r"^(cool|nice|awesome|wonderful|perfect|great|all good)$",
            r"^(rest for today|lets rest for today|let us rest for today|done for today|thats all for today|that is all for today|call it a day)$",
            r"^(who are you|what can you do|how can you help)\b",
            r"^(it is |its )?(so |too |very |really |quite |pretty )?(hot|cold|warm|chilly|humid|windy|rainy|uncomfortable)( today| tonight| outside| here)?$",
        )
        return any(re.match(pattern, normalized) for pattern in casual_patterns)

    def _is_explicit_qm_prompt(prompt: str) -> bool:
        return bool(
            re.search(
                r"\b(question\s*map|qmap|qm)\b|\b(generate|create|build|make)\b.*\bmap\b",
                prompt or "",
                flags=re.IGNORECASE,
            )
        )

    def _queue_new_chat_request(topic_text: str, action: str) -> bool:
        prompt = (topic_text or "").strip()
        action = (action or "interrogate").strip().lower()
        if action not in {"interrogate", "illustrate"}:
            action = "interrogate"

        if (
            not prompt
            or st.session_state._nc_pending_request
            or st.session_state._nc_generating
        ):
            return False

        # Product facts are deterministic local responses. Sending them
        # through the asynchronous-looking generation lifecycle only creates
        # avoidable latency and can leave a stale Thinking placeholder if a
        # hosted rerun interrupts the transition.
        quick_profile = _refresh_chat_user_profile(prompt)
        if action == "interrogate" and (
            _local_conversation_answer(prompt, quick_profile)
            or answer_ini_product_query(prompt)
        ):
            st.session_state._nc_bottom_composer_revision += 1
            st.session_state.chat_top_enter_submit = False
            st.session_state.chat_bottom_enter_submit = False
            st.session_state.nc_started = True
            _run_new_chat_interrogate(prompt, show_spinner=False)
            return True

        pending_qm_choice = st.session_state.get("chat_pending_qm_confirmation")
        normalized_choice = re.sub(r"[^a-z0-9 ]+", " ", prompt.lower()).strip()
        active_discussion_state = st.session_state.get("chat_active_discussion")
        discussion_interaction = bool(
            isinstance(active_discussion_state, dict)
            and (
                re.fullmatch(r"[1-3]", normalized_choice)
                or normalized_choice in {
                    "explain more",
                    "previous question",
                    "previous answer",
                    "next question",
                    "next question set",
                }
                or isinstance(active_discussion_state.get("awaiting_option_index"), int)
            )
        )
        interpreting_topic_shift = bool(
            _latest_response_mode() == "conversation"
            and not isinstance(pending_qm_choice, dict)
            and not _is_explicit_qm_prompt(prompt)
            and not _looks_like_casual_generation(prompt)
        )

        st.session_state._nc_pending_request = {
            "prompt": prompt,
            "action": action,
            "ts": now_label(),
            # Every request begins in interpretation. The generation phase is
            # selected only after this first state has been visibly rendered.
            "status_mode": "thinking",
        }
        st.session_state._nc_bottom_composer_revision += 1
        st.session_state.chat_top_enter_submit = False
        st.session_state.chat_bottom_enter_submit = False
        st.session_state.nc_started = True
        st.rerun()
        return True

    def _render_new_chat_generation_placeholder(
        action: str = "interrogate",
        status_mode: str = "generating",
    ) -> None:
        generation_icon_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
        generation_icon_data = base64.b64encode(
            generation_icon_path.read_bytes()
        ).decode("ascii")
        status_copy = "Creating illustration..." if action == "illustrate" else (
            "Thinking..."
            if status_mode == "thinking"
            else "Generating Question Map..."
            if status_mode == "question_map"
            else "Generating response... may take some time."
        )
        st.markdown(
            f"""
            <style>
            .nc-generation-placeholder .nc-generation-copy {{
                display: flex;
                align-items: center;
                gap: 9px;
                margin: 0;
                color: #4b5565;
                font-size: 17px;
                font-weight: 520;
                letter-spacing: -0.01em;
                line-height: 1.4;
            }}

            .nc-generation-placeholder img.nc-generation-icon {{
                width: 15px !important;
                height: 25px !important;
                max-width: 15px !important;
                max-height: 25px !important;
                display: block;
                flex: 0 0 auto;
                object-fit: contain;
                filter: drop-shadow(0 3px 7px rgba(245, 27, 63, 0.18));
                animation: nc-generation-icon-think 1.18s ease-in-out infinite;
            }}

            @keyframes nc-generation-icon-think {{
                0%, 100% {{ opacity: 0.30; transform: scale(0.94); }}
                46% {{ opacity: 1; transform: scale(1.025); }}
                62% {{ opacity: 0.72; transform: scale(1); }}
            }}
            </style>
            <div class="nc-generation-placeholder">
              <div class="nc-generation-copy">
                <img class="nc-generation-icon" src="data:image/png;base64,{generation_icon_data}" alt="">
                <span>{status_copy}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _generate_pending_new_chat_response(generation_slot: Any) -> None:
        pending = st.session_state._nc_pending_request
        if not isinstance(pending, dict):
            return

        if st.session_state._nc_generating:
            started_at = float(
                st.session_state.get("_nc_generating_started_at") or 0.0
            )
            # A live run for this session executes serially. If a later rerun
            # sees this lock, the earlier run was interrupted and cannot clear
            # it. Recover immediately instead of displaying Thinking forever.
            if not started_at or (time.time() - started_at) >= 2.0:
                st.session_state._nc_generating = False
                st.session_state._nc_generating_started_at = 0.0
            else:
                return

        prompt = (pending.get("prompt") or "").strip()
        action = (pending.get("action") or "interrogate").strip().lower()
        status_mode = (pending.get("status_mode") or "generating").strip().lower()
        if not prompt:
            st.session_state._nc_pending_request = None
            return

        st.session_state._nc_generating = True
        st.session_state._nc_generating_started_at = time.time()
        try:
            with generation_slot.container():
                _render_new_chat_generation_placeholder(action, "thinking")

            # Give the interpretation state enough time to be perceived, then
            # reveal the operation InI has selected. Clarification stays in the
            # Thinking state because no answer/map generation has begun.
            time.sleep(0.65)
            if action == "illustrate":
                resolved_status = "generating"
            elif (
                isinstance(
                    st.session_state.get("chat_pending_qm_confirmation"),
                    dict,
                )
                and bool(
                    re.match(
                        r"^(yes|yeah|yep|sure|okay|ok|please|go ahead|do it|generate)\b",
                        re.sub(r"[^a-z0-9 ]+", " ", prompt.lower()).strip(),
                    )
                )
            ) or _is_explicit_qm_prompt(prompt) or (
                st.session_state.chat_study_mode_established
                and not _looks_like_casual_generation(prompt)
                and not _looks_like_answer_to_last_question(
                    prompt,
                    _latest_assistant_conversation_reply(),
                )
            ):
                resolved_status = "question_map"
            else:
                # Conversation, clarification, short follow-ups, and unknown
                # requests remain in interpretation mode. "Generating
                # response" is reserved for a generation operation that InI
                # has positively identified, not every ordinary question.
                resolved_status = "thinking"

            if resolved_status != "thinking":
                generation_slot.empty()
                with generation_slot.container():
                    _render_new_chat_generation_placeholder(action, resolved_status)

            with generation_slot.container():
                if action == "illustrate":
                    _run_new_chat_illustrate(prompt, show_spinner=False)
                else:
                    _run_new_chat_interrogate(prompt, show_spinner=False)
        finally:
            st.session_state._nc_pending_request = None
            st.session_state._nc_generating = False
            st.session_state._nc_generating_started_at = 0.0

        st.rerun()

    def _render_pending_new_chat_continuation(pending: Dict[str, Any]) -> None:
        pending_prompt = (pending.get("prompt") or "").strip()
        pending_ts = (pending.get("ts") or "").strip()
        if not pending_prompt:
            return

        st.markdown('<div class="nc-pending-inline-anchor"></div>', unsafe_allow_html=True)
        _render_nc_user_bubble(
            pending_prompt,
            pending_ts,
            extra_class="nc-pending-inline-query",
        )

        generation_slot = st.empty()
        with generation_slot.container():
            _render_new_chat_generation_placeholder(
                (pending.get("action") or "interrogate").strip().lower(),
                (pending.get("status_mode") or "generating").strip().lower(),
            )

        _render_new_chat_bottom_uib()

        st.iframe(
            """
            <script>
            requestAnimationFrame(() => {
              try {
                const doc = window.parent.document;
                const anchor = doc.querySelector('.nc-pending-inline-anchor');
                if (anchor) {
                  anchor.scrollIntoView({ block: 'center', behavior: 'smooth' });
                }
              } catch (err) {}
            });
            </script>
            """,
            height=1,
            tab_index=-1,
        )

        _generate_pending_new_chat_response(generation_slot)

    def _render_nc_latest_scroll_target() -> None:
        st.markdown(
            '<div id="nc-latest-response" class="nc-latest-response-anchor"></div>',
            unsafe_allow_html=True,
        )

    def _render_nc_scroll_to_latest_once() -> None:
        if not st.session_state._nc_scroll_to_latest_response:
            return

        st.iframe(
            """
            <script>
            requestAnimationFrame(() => {
              try {
                const doc = window.parent.document;
                const win = doc.defaultView || window.parent;
                const anchor = doc.querySelector('#nc-latest-response');
                if (anchor) {
                  const top = anchor.getBoundingClientRect().top + win.scrollY - 82;
                  win.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
                  const scrollers = [
                    doc.scrollingElement,
                    doc.documentElement,
                    doc.body,
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('.main')
                  ].filter(Boolean);
                  for (const scroller of scrollers) {
                    if (scroller.scrollHeight > scroller.clientHeight + 20) {
                      const boxTop = anchor.getBoundingClientRect().top
                        - scroller.getBoundingClientRect().top
                        + scroller.scrollTop
                        - 82;
                      scroller.scrollTo({ top: Math.max(0, boxTop), behavior: 'smooth' });
                    }
                  }
                }
              } catch (err) {}
            });
            </script>
            """,
            height=1,
            tab_index=-1,
        )
        st.session_state._nc_scroll_to_latest_response = False

    def _render_nc_scroll_controls() -> None:
        st.iframe(
            """
            <script>
            (() => {
              try {
                const doc = window.parent.document;
                const win = doc.defaultView || window.parent;
                const old = doc.getElementById('ini-nc-scroll-controls');
                if (old) old.remove();

                const styleId = 'ini-nc-scroll-controls-style';
                if (!doc.getElementById(styleId)) {
                  const style = doc.createElement('style');
                  style.id = styleId;
                  style.textContent = `
                    #ini-nc-scroll-controls {
                      position: fixed;
                      z-index: 2147483000;
                      right: 22px;
                      top: 50%;
                      transform: translateY(-50%);
                      display: flex;
                      flex-direction: column;
                      gap: 8px;
                      pointer-events: auto;
                    }
                    #ini-nc-scroll-controls button {
                      width: 38px;
                      height: 38px;
                      border: 1px solid rgba(15, 23, 42, 0.12);
                      border-radius: 13px;
                      color: #0f172a;
                      background: rgba(255, 255, 255, 0.94);
                      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.11);
                      font: 800 17px/1 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                      cursor: pointer;
                      transition: transform 120ms ease, border-color 120ms ease, color 120ms ease;
                    }
                    #ini-nc-scroll-controls button:hover {
                      transform: translateY(-1px);
                      border-color: rgba(245, 27, 63, 0.45);
                      color: #f51b3f;
                    }
                    #ini-nc-scroll-controls button[title="Your queries"] {
                      border-color: #f51b3f;
                      background: rgba(255, 255, 255, 0.94);
                      color: #f51b3f;
                    }
                    #ini-nc-scroll-controls button[title="Your queries"]:hover {
                      border-color: #d91435;
                      background: #ffffff;
                      color: #d91435;
                    }
                    #ini-nc-query-navigator {
                      position: fixed;
                      inset: 0;
                      z-index: 2147483001;
                      display: grid;
                      place-items: center;
                      padding: 22px;
                      background: rgba(15, 23, 42, 0.24);
                      backdrop-filter: blur(4px);
                    }
                    #ini-nc-query-navigator__panel {
                      width: min(500px, 100%);
                      max-height: min(680px, calc(100vh - 44px));
                      overflow: auto;
                      padding: 20px;
                      border: 1px solid #e7eaf0;
                      border-radius: 20px;
                      background: #ffffff;
                      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.2);
                    }
                    .ini-nc-query-navigator__header {
                      display: flex;
                      align-items: center;
                      justify-content: space-between;
                      gap: 16px;
                      margin-bottom: 5px;
                    }
                    .ini-nc-query-navigator__title {
                      margin: 0;
                      color: #111827;
                      font: 700 18px/1.3 "Aptos", "Segoe UI", sans-serif;
                    }
                    .ini-nc-query-navigator__caption {
                      margin: 0 0 16px;
                      color: #6b7280;
                      font: 400 13px/1.45 "Aptos", "Segoe UI", sans-serif;
                    }
                    .ini-nc-query-navigator__close {
                      width: 32px;
                      height: 32px;
                      border: 1px solid #e5e7eb;
                      border-radius: 10px;
                      background: #ffffff;
                      color: #4b5563;
                      font: 600 18px/1 "Aptos", "Segoe UI", sans-serif;
                      cursor: pointer;
                    }
                    .ini-nc-query-navigator__item {
                      display: flex;
                      align-items: center;
                      gap: 10px;
                      width: 100%;
                      margin: 0;
                      padding: 12px 4px;
                      border: 0;
                      border-bottom: 1px solid #edf0f4;
                      border-radius: 10px;
                      background: transparent;
                      color: #374151;
                      text-align: left;
                      font: 400 14px/1.45 "Aptos", "Segoe UI", sans-serif;
                      cursor: pointer;
                      transition: background 120ms ease, padding 120ms ease;
                    }
                    .ini-nc-query-navigator__item:hover {
                      padding-left: 10px;
                      padding-right: 10px;
                      background: #f7f8fa;
                    }
                    .ini-nc-query-navigator__number {
                      display: grid;
                      flex: 0 0 auto;
                      place-items: center;
                      width: 22px;
                      height: 22px;
                      border-radius: 999px;
                      background: #fff1f3;
                      color: #f51b3f;
                      font: 700 12px/1 "Aptos", "Segoe UI", sans-serif;
                    }
                    .ini-nc-query-navigator__label {
                      flex: 1 1 auto;
                      min-width: 0;
                      overflow: hidden;
                      text-overflow: ellipsis;
                      white-space: nowrap;
                    }
                    .ini-nc-query-navigator__arrow {
                      flex: 0 0 auto;
                      color: #9ca3af;
                      font: 500 17px/1 "Aptos", "Segoe UI", sans-serif;
                    }
                    @media (max-width: 760px) {
                      #ini-nc-scroll-controls {
                        right: max(7px, env(safe-area-inset-right));
                        top: 50%;
                        bottom: auto;
                        display: flex;
                        gap: 6px;
                        transform: translateY(-50%);
                      }
                      #ini-nc-scroll-controls button {
                        width: 34px;
                        height: 34px;
                        border-radius: 11px;
                        font-size: 15px;
                        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.10);
                      }
                      #ini-nc-query-navigator {
                        padding:
                          max(12px, env(safe-area-inset-top))
                          max(12px, env(safe-area-inset-right))
                          max(12px, env(safe-area-inset-bottom))
                          max(12px, env(safe-area-inset-left));
                      }
                      #ini-nc-query-navigator__panel {
                        width: 100%;
                        max-height: calc(100dvh - 24px);
                        padding: 16px;
                        border-radius: 16px;
                      }
                      .ini-nc-query-navigator__label {
                        overflow: visible;
                        text-overflow: clip;
                        white-space: normal;
                      }
                    }
                  `;
                  doc.head.appendChild(style);
                }

                const scrollables = () => [
                  doc.scrollingElement,
                  doc.documentElement,
                  doc.body,
                  doc.querySelector('[data-testid="stAppViewContainer"]'),
                  doc.querySelector('[data-testid="stMain"]'),
                  doc.querySelector('.main')
                ].filter(Boolean).filter((el, index, arr) => arr.indexOf(el) === index);

                const applyScroll = (kind) => {
                  const isMobile = win.matchMedia('(max-width: 760px)').matches;
                  if (isMobile) {
                    const candidates = scrollables()
                      .map((el) => ({
                        el,
                        range: Math.max(0, el.scrollHeight - el.clientHeight)
                      }))
                      .filter(({ range }) => range > 8)
                      .sort((a, b) => b.range - a.range);
                    const target = candidates.find(({ el }) =>
                      el.matches?.('[data-testid="stMain"], [data-testid="stAppViewContainer"], .main')
                    )?.el || candidates[0]?.el;
                    if (!target) return;

                    const viewportHeight = target.clientHeight || win.innerHeight;
                    const currentTop = target.scrollTop || 0;
                    const maxTop = Math.max(0, target.scrollHeight - viewportHeight);
                    let nextTop = currentTop;
                    if (kind === 'home') nextTop = 0;
                    else if (kind === 'end') nextTop = maxTop;
                    else if (kind === 'up') nextTop = Math.max(0, currentTop - (viewportHeight * 0.72));
                    else if (kind === 'down') nextTop = Math.min(maxTop, currentTop + (viewportHeight * 0.72));
                    target.scrollTo({ top: nextTop, behavior: 'smooth' });
                    if (kind === 'end') {
                      const settleAtEnd = () => target.scrollTo({
                        top: Math.max(0, target.scrollHeight - target.clientHeight),
                        behavior: 'auto'
                      });
                      win.requestAnimationFrame(() => win.requestAnimationFrame(settleAtEnd));
                      win.setTimeout(settleAtEnd, 240);
                    }
                    return;
                  }

                  const amount = win.innerHeight * 0.82;
                  for (const el of scrollables()) {
                    if (kind === 'home') {
                      if (el === doc.scrollingElement || el === doc.documentElement || el === doc.body) {
                        win.scrollTo({ top: 0, behavior: 'smooth' });
                      }
                      el.scrollTo?.({ top: 0, behavior: 'smooth' });
                    } else if (kind === 'end') {
                      const bottom = Math.max(0, el.scrollHeight - el.clientHeight);
                      if (el === doc.scrollingElement || el === doc.documentElement || el === doc.body) {
                        win.scrollTo({ top: doc.documentElement.scrollHeight, behavior: 'smooth' });
                      }
                      el.scrollTo?.({ top: bottom, behavior: 'smooth' });
                    } else if (kind === 'up') {
                      if (el === doc.scrollingElement || el === doc.documentElement || el === doc.body) {
                        win.scrollBy({ top: -amount, behavior: 'smooth' });
                      }
                      el.scrollBy?.({ top: -amount, behavior: 'smooth' });
                    } else if (kind === 'down') {
                      if (el === doc.scrollingElement || el === doc.documentElement || el === doc.body) {
                        win.scrollBy({ top: amount, behavior: 'smooth' });
                      }
                      el.scrollBy?.({ top: amount, behavior: 'smooth' });
                    }
                  }
                };

                const openQueryNavigator = () => {
                  doc.getElementById('ini-nc-query-navigator')?.remove();
                  const queries = [...doc.querySelectorAll('.nc-user-bubble')]
                    .map((bubble) => ({
                      bubble,
                      text: bubble.querySelector('.nc-user-bubble__prompt')?.innerText?.trim() || ''
                    }))
                    .filter(({ text }) => text);

                  const overlay = doc.createElement('div');
                  overlay.id = 'ini-nc-query-navigator';
                  const panel = doc.createElement('section');
                  panel.id = 'ini-nc-query-navigator__panel';
                  panel.setAttribute('role', 'dialog');
                  panel.setAttribute('aria-modal', 'true');
                  panel.setAttribute('aria-label', 'Your queries');

                  const header = doc.createElement('div');
                  header.className = 'ini-nc-query-navigator__header';
                  const title = doc.createElement('h2');
                  title.className = 'ini-nc-query-navigator__title';
                  title.textContent = 'Your queries';
                  const close = doc.createElement('button');
                  close.className = 'ini-nc-query-navigator__close';
                  close.type = 'button';
                  close.setAttribute('aria-label', 'Close query list');
                  close.textContent = '×';
                  header.append(title, close);
                  panel.append(header);

                  const caption = doc.createElement('p');
                  caption.className = 'ini-nc-query-navigator__caption';
                  caption.textContent = queries.length
                    ? 'Choose a query to jump directly to it.'
                    : 'Your queries will appear here as the conversation grows.';
                  panel.append(caption);

                  queries.forEach(({ bubble, text }, index) => {
                    const item = doc.createElement('button');
                    item.className = 'ini-nc-query-navigator__item';
                    item.type = 'button';
                    const number = doc.createElement('span');
                    number.className = 'ini-nc-query-navigator__number';
                    number.textContent = String(index + 1);
                    const label = doc.createElement('span');
                    label.className = 'ini-nc-query-navigator__label';
                    label.textContent = text;
                    const arrow = doc.createElement('span');
                    arrow.className = 'ini-nc-query-navigator__arrow';
                    arrow.textContent = '→';
                    item.append(number, label, arrow);
                    item.addEventListener('click', () => {
                      overlay.remove();
                      bubble.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    });
                    panel.append(item);
                  });

                  const dismiss = () => overlay.remove();
                  close.addEventListener('click', dismiss);
                  overlay.addEventListener('click', (event) => {
                    if (event.target === overlay) dismiss();
                  });
                  overlay.append(panel);
                  doc.body.append(overlay);
                };

                const wrap = doc.createElement('div');
                wrap.id = 'ini-nc-scroll-controls';
                const actions = [
                  ['Home', '↑', () => applyScroll('home')],
                  ['Page up', '⇞', () => applyScroll('up')],
                  ['Page down', '⇟', () => applyScroll('down')],
                  ['End', '↓', () => applyScroll('end')],
                ];
                actions.push(['Your queries', 'Q', openQueryNavigator]);
                for (const [title, label, action] of actions) {
                  const btn = doc.createElement('button');
                  btn.type = 'button';
                  btn.title = title;
                  btn.setAttribute('aria-label', title);
                  btn.textContent = label;
                  btn.addEventListener('click', action);
                  wrap.appendChild(btn);
                }
                doc.body.appendChild(wrap);
              } catch (err) {}
            })();
            </script>
            """,
            height=1,
            tab_index=-1,
        )

    def _render_new_chat_top_uib() -> None:
        if st.session_state.chat_top_topic_input == "" and st.session_state.chat.get("topic"):
            st.session_state.chat_top_topic_input = st.session_state.chat.get("topic", "")

        icon_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
        icon_data = base64.b64encode(icon_path.read_bytes()).decode("ascii")
        st.markdown(
            f"""
            <style>
            [data-testid="stMainBlockContainer"]:has(.nc-landing-marker) {{
                width: 100%;
                max-width: none;
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }}

            [data-testid="stVerticalBlock"]:has(.nc-landing-marker) {{
                min-height: calc(100vh - 70px);
            }}

            .nc-landing-marker {{
                display: none;
            }}

            [data-testid="stElementContainer"]:has(.nc-landing-brand) {{
                width: min(100%, 900px);
                margin: clamp(70px, 13vh, 145px) auto 0;
            }}

            .nc-landing-brand {{
                width: 100%;
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
                align-items: center;
            }}

            .nc-landing-brand-left {{
                display: flex;
                align-items: center;
                justify-self: end;
                gap: 8px;
            }}

            .nc-landing-brand img {{
                width: 70px;
                height: 70px;
                object-fit: contain;
                flex: 0 0 70px;
                margin-right: -14px;
                transform: translateX(10px);
            }}

            .nc-landing-wordmark {{
                color: #0f172a;
                font-size: 43px;
                font-weight: 800;
                line-height: 1;
            }}

            .nc-landing-wordmark-accent {{
                grid-column: 3;
                justify-self: start;
                color: #f51b3f;
            }}

            .nc-landing-wordmark-dot {{
                grid-column: 2;
                justify-self: center;
            }}

            .nc-landing-heading {{
                margin: 10px auto 0;
                color: #111827;
                font-size: 30px;
                font-weight: 760;
                line-height: 1.2;
                text-align: center;
            }}

            .nc-landing-greeting {{
                margin: 20px auto 0;
                color: #4b5563;
                font-size: 16px;
                font-weight: 600;
                line-height: 1.35;
                text-align: center;
            }}

            .nc-landing-subtitle {{
                margin: 10px auto 28px;
                color: #667085;
                font-size: 15px;
                line-height: 1.5;
                text-align: center;
            }}

            .st-key-nc_landing_composer {{
                width: min(100%, 860px);
                margin-inline: auto;
                padding: 8px 10px 10px;
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 20px;
                background:
                    linear-gradient(180deg, #ffffff 0%, #fdfefe 100%);
                box-shadow:
                    0 24px 64px rgba(15, 23, 42, 0.08),
                    0 6px 18px rgba(15, 23, 42, 0.035),
                    inset 0 1px 0 rgba(255, 255, 255, 0.98);
                transition: border-color 180ms ease, box-shadow 180ms ease,
                    transform 180ms ease;
            }}

            .st-key-nc_landing_composer:focus-within {{
                border-color: rgba(100, 116, 139, 0.28);
                box-shadow:
                    0 26px 68px rgba(15, 23, 42, 0.095),
                    0 7px 20px rgba(15, 23, 42, 0.04),
                    inset 0 1px 0 rgba(255, 255, 255, 1);
                transform: translateY(-1px);
            }}

            .st-key-nc_landing_composer
            div[data-testid="stTextArea"]:has(textarea[aria-label="NC_TOP_TOPIC"]) {{
                width: min(100%, 860px);
                margin-inline: auto;
                background: transparent !important;
                border: 0 !important;
                box-shadow: none !important;
            }}

            .st-key-nc_landing_composer
            div[data-testid="stTextArea"]:has(textarea[aria-label="NC_TOP_TOPIC"]) > div {{
                overflow: hidden !important;
                padding: 0 !important;
                border: 0 !important;
                border-radius: 14px !important;
                background: transparent !important;
                box-shadow: none !important;
            }}

            .st-key-nc_landing_composer
            div[data-testid="stTextArea"]:has(textarea[aria-label="NC_TOP_TOPIC"]) textarea,
            .st-key-nc_landing_composer
            div[data-testid="stTextArea"]:has(textarea[aria-label="NC_TOP_TOPIC"]) textarea:focus {{
                min-height: 70px !important;
                height: auto !important;
                max-height: 190px !important;
                padding: 18px 18px 12px !important;
                box-sizing: border-box !important;
                resize: none !important;
                overflow-y: auto !important;
                field-sizing: content;
                border: 0 !important;
                border-radius: 14px !important;
                outline: 0 !important;
                color: #111827 !important;
                background: transparent !important;
                box-shadow: none !important;
                font-size: 16px !important;
                line-height: 1.45 !important;
                caret-color: #087f7b;
            }}

            .st-key-nc_landing_composer
            div[data-testid="stTextArea"]:has(textarea[aria-label="NC_TOP_TOPIC"])
            textarea::placeholder {{
                color: #8b95a3 !important;
                opacity: 1 !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_top_interrogate) {{
                width: min(100%, 370px);
                margin: 18px auto 0;
                gap: 14px;
                flex-wrap: nowrap;
            }}

            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_top_interrogate)
            > div[data-testid="stColumn"] {{
                width: 0 !important;
                min-width: 0 !important;
                flex: 1 1 0 !important;
            }}

            .st-key-nc_top_interrogate div.stButton > button[kind="secondary"],
            .st-key-nc_top_illustrate div.stButton > button[kind="secondary"] {{
                width: 100% !important;
                min-width: 0 !important;
                height: 42px !important;
                min-height: 42px !important;
                justify-content: center !important;
                padding: 0 18px !important;
                margin: 0 !important;
                border: 1px solid #071126 !important;
                border-radius: 13px !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                background: #071126 !important;
                box-shadow: 0 4px 11px rgba(7, 17, 38, 0.13) !important;
                transition: transform 120ms ease, background 120ms ease,
                    box-shadow 120ms ease;
            }}

            .st-key-nc_top_interrogate div.stButton > button[kind="secondary"]:hover,
            .st-key-nc_top_illustrate div.stButton > button[kind="secondary"]:hover {{
                transform: translateY(-1px);
                border-color: #111d35 !important;
                background: #111d35 !important;
                box-shadow: 0 6px 14px rgba(7, 17, 38, 0.17) !important;
            }}

            .st-key-nc_top_interrogate div.stButton > button[kind="secondary"] p,
            .st-key-nc_top_interrogate div.stButton > button[kind="secondary"] span,
            .st-key-nc_top_illustrate div.stButton > button[kind="secondary"] p,
            .st-key-nc_top_illustrate div.stButton > button[kind="secondary"] span {{
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                font-size: 14px !important;
                font-weight: 800 !important;
                line-height: 1 !important;
                letter-spacing: 0 !important;
                margin: 0 !important;
                white-space: nowrap !important;
            }}

            [data-testid="stElementContainer"]:has(.nc-explore-label) {{
                width: min(100%, 860px);
                margin: 30px auto 9px;
            }}

            .nc-explore-label {{
                color: #6b7280;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }}

            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_ai) {{
                width: min(100%, 860px);
                margin-inline: auto;
                display: grid !important;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
            }}

            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_ai)
            > div[data-testid="stColumn"] {{
                width: auto !important;
                min-width: 0 !important;
                flex: none !important;
            }}

            .st-key-nc_explore_ai button,
            .st-key-nc_explore_quantum button,
            .st-key-nc_explore_cognitive button,
            .st-key-nc_explore_kubernetes button {{
                position: relative;
                width: 100% !important;
                min-width: 0 !important;
                height: 42px !important;
                min-height: 42px !important;
                justify-content: center !important;
                gap: 8px;
                padding: 0 12px !important;
                margin: 0 !important;
                overflow: hidden;
                border: 1px solid #dde3e8 !important;
                border-radius: 8px !important;
                color: #34433f !important;
                background: #ffffff !important;
                box-shadow: 0 2px 7px rgba(15, 23, 42, 0.035) !important;
            }}

            .st-key-nc_explore_ai div.stButton > button[kind="secondary"]:hover,
            .st-key-nc_explore_quantum div.stButton > button[kind="secondary"]:hover,
            .st-key-nc_explore_cognitive div.stButton > button[kind="secondary"]:hover,
            .st-key-nc_explore_kubernetes div.stButton > button[kind="secondary"]:hover {{
                border-color: #f2a4b2 !important;
                color: #d91d3f !important;
                -webkit-text-fill-color: #d91d3f !important;
                background: #fff3f5 !important;
            }}

            .st-key-nc_explore_ai div.stButton > button[kind="secondary"]:hover p,
            .st-key-nc_explore_quantum div.stButton > button[kind="secondary"]:hover p,
            .st-key-nc_explore_cognitive div.stButton > button[kind="secondary"]:hover p,
            .st-key-nc_explore_kubernetes div.stButton > button[kind="secondary"]:hover p {{
                color: #d91d3f !important;
                -webkit-text-fill-color: #d91d3f !important;
            }}

            .st-key-nc_explore_ai button p,
            .st-key-nc_explore_quantum button p,
            .st-key-nc_explore_cognitive button p,
            .st-key-nc_explore_kubernetes button p {{
                min-width: 0;
                overflow: hidden;
                color: inherit !important;
                -webkit-text-fill-color: currentColor !important;
                font-size: 12px !important;
                font-weight: 650 !important;
                line-height: 1.2 !important;
                text-overflow: ellipsis;
                white-space: nowrap !important;
            }}

            .st-key-nc_explore_ai button::before,
            .st-key-nc_explore_quantum button::before,
            .st-key-nc_explore_cognitive button::before,
            .st-key-nc_explore_kubernetes button::before {{
                width: 17px;
                height: 17px;
                display: block;
                flex: 0 0 17px;
                background: currentColor;
                content: "";
                -webkit-mask-position: center;
                -webkit-mask-repeat: no-repeat;
                -webkit-mask-size: contain;
                mask-position: center;
                mask-repeat: no-repeat;
                mask-size: contain;
            }}

            .st-key-nc_explore_ai button::before {{
                -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.5 4A3.5 3.5 0 0 0 6 7.5c0 .3.04.58.1.85A3.5 3.5 0 0 0 7.5 15H9v3a2 2 0 0 0 4 0V6.5A2.5 2.5 0 0 0 10.5 4Z'/%3E%3Cpath d='M14.5 4A3.5 3.5 0 0 1 18 7.5c0 .3-.04.58-.1.85A3.5 3.5 0 0 1 16.5 15H15'/%3E%3Cpath d='M9 9h2M15 9h2M9 13h2M15 13h2'/%3E%3C/svg%3E");
                mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.5 4A3.5 3.5 0 0 0 6 7.5c0 .3.04.58.1.85A3.5 3.5 0 0 0 7.5 15H9v3a2 2 0 0 0 4 0V6.5A2.5 2.5 0 0 0 10.5 4Z'/%3E%3Cpath d='M14.5 4A3.5 3.5 0 0 1 18 7.5c0 .3-.04.58-.1.85A3.5 3.5 0 0 1 16.5 15H15'/%3E%3Cpath d='M9 9h2M15 9h2M9 13h2M15 13h2'/%3E%3C/svg%3E");
            }}

            .st-key-nc_explore_quantum button::before {{
                -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8'%3E%3Ccircle cx='12' cy='12' r='1.5' fill='black'/%3E%3Cellipse cx='12' cy='12' rx='9' ry='3.8'/%3E%3Cellipse cx='12' cy='12' rx='9' ry='3.8' transform='rotate(60 12 12)'/%3E%3Cellipse cx='12' cy='12' rx='9' ry='3.8' transform='rotate(120 12 12)'/%3E%3C/svg%3E");
                mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8'%3E%3Ccircle cx='12' cy='12' r='1.5' fill='black'/%3E%3Cellipse cx='12' cy='12' rx='9' ry='3.8'/%3E%3Cellipse cx='12' cy='12' rx='9' ry='3.8' transform='rotate(60 12 12)'/%3E%3Cellipse cx='12' cy='12' rx='9' ry='3.8' transform='rotate(120 12 12)'/%3E%3C/svg%3E");
            }}

            .st-key-nc_explore_cognitive button::before {{
                -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M8 18H5l1.2-3A7 7 0 1 1 19 11a7 7 0 0 1-7 7Z'/%3E%3Cpath d='M9 10h6M9 13h4'/%3E%3C/svg%3E");
                mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M8 18H5l1.2-3A7 7 0 1 1 19 11a7 7 0 0 1-7 7Z'/%3E%3Cpath d='M9 10h6M9 13h4'/%3E%3C/svg%3E");
            }}

            .st-key-nc_explore_kubernetes button::before {{
                -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3 7.8 4.5v9L12 21l-7.8-4.5v-9Z'/%3E%3Ccircle cx='12' cy='12' r='2.3'/%3E%3Cpath d='M12 5v4.7M18 8.5l-4 2.3M18 15.5l-4-2.3M12 19v-4.7M6 15.5l4-2.3M6 8.5l4 2.3'/%3E%3C/svg%3E");
                mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3 7.8 4.5v9L12 21l-7.8-4.5v-9Z'/%3E%3Ccircle cx='12' cy='12' r='2.3'/%3E%3Cpath d='M12 5v4.7M18 8.5l-4 2.3M18 15.5l-4-2.3M12 19v-4.7M6 15.5l4-2.3M6 8.5l4 2.3'/%3E%3C/svg%3E");
            }}

            @media (max-width: 1100px) {{
                div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_ai) {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 8px;
                }}
            }}

            @media (max-width: 760px) {{
                [data-testid="stElementContainer"]:has(.nc-landing-brand) {{
                    margin-top: 42px;
                }}

                .nc-landing-brand {{
                    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
                }}

                .nc-landing-brand-left {{
                    gap: 7px;
                }}

                .nc-landing-brand img {{
                    width: 58px;
                    height: 58px;
                    flex-basis: 58px;
                }}

                .nc-landing-wordmark {{
                    font-size: 35px;
                }}

                .nc-landing-heading {{
                    max-width: 92%;
                    margin-top: 18px;
                    font-size: 25px;
                }}

                .nc-landing-subtitle {{
                    max-width: 92%;
                    margin-bottom: 22px;
                    font-size: 14px;
                }}

                .st-key-nc_landing_composer {{
                    width: calc(100% - 18px);
                    padding: 7px 8px 8px;
                    border-radius: 18px;
                }}

                div[data-testid="stHorizontalBlock"]:has(.st-key-nc_top_interrogate) {{
                    width: min(calc(100% - 34px), 350px);
                    gap: 12px;
                }}

                .st-key-nc_top_interrogate div.stButton > button[kind="secondary"],
                .st-key-nc_top_illustrate div.stButton > button[kind="secondary"] {{
                    height: 44px !important;
                    min-height: 44px !important;
                    padding-inline: 10px !important;
                }}

                div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_ai) {{
                    width: calc(100% - 18px);
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 8px;
                }}

                [data-testid="stElementContainer"]:has(.nc-explore-label) {{
                    width: calc(100% - 18px);
                }}
            }}

            @media (max-width: 380px) {{
                .st-key-nc_explore_ai button,
                .st-key-nc_explore_quantum button,
                .st-key-nc_explore_cognitive button,
                .st-key-nc_explore_kubernetes button {{
                    gap: 5px;
                    padding-inline: 7px !important;
                }}

                .st-key-nc_explore_ai button::before,
                .st-key-nc_explore_quantum button::before,
                .st-key-nc_explore_cognitive button::before,
                .st-key-nc_explore_kubernetes button::before {{
                    width: 14px;
                    height: 14px;
                    flex-basis: 14px;
                }}

                .st-key-nc_explore_ai button p,
                .st-key-nc_explore_quantum button p,
                .st-key-nc_explore_cognitive button p,
                .st-key-nc_explore_kubernetes button p {{
                    font-size: 11px !important;
                    text-overflow: clip;
                }}
            }}
            </style>
            <div class="nc-landing-marker"></div>
            <div class="nc-landing-brand">
              <div class="nc-landing-brand-left">
                <img src="data:image/png;base64,{icon_data}" alt="">
                <span class="nc-landing-wordmark">InI</span>
              </div>
              <span class="nc-landing-wordmark nc-landing-wordmark-dot nc-landing-wordmark-accent">.</span>
              <span class="nc-landing-wordmark nc-landing-wordmark-accent">ai</span>
            </div>
            <div class="nc-landing-heading">What would you like to understand?</div>
            <div class="nc-landing-subtitle">Begin with a topic, question, or idea.</div>
            """,
            unsafe_allow_html=True,
        )

        run = False
        illustrate_run = False
        explore_topic = None

        with st.container(key="nc_landing_composer"):
            st.text_area(
                "NC_TOP_TOPIC",
                placeholder="Ask InI anything...",
                key="chat_top_topic_input",
                label_visibility="collapsed",
                height=70,
                on_change=_request_chat_top_enter_submit,
            )

        action_cols = st.columns(2, gap="small")
        with action_cols[0]:
            run = st.button(
                "Interrogate",
                key="nc_top_interrogate",
                type="secondary",
                use_container_width=True,
            )
        with action_cols[1]:
            illustrate_run = st.button(
                "Illustrate",
                key="nc_top_illustrate",
                type="secondary",
                use_container_width=True,
            )

        st.markdown('<div class="nc-explore-label">Explore</div>', unsafe_allow_html=True)
        explore_cols = st.columns(4, gap="small")
        explore_items = [
            ("Artificial intelligence", "nc_explore_ai"),
            ("Quantum computing", "nc_explore_quantum"),
            ("Cognitive science", "nc_explore_cognitive"),
            ("Kubernetes", "nc_explore_kubernetes"),
        ]
        for col, (label, key) in zip(explore_cols, explore_items):
            with col:
                if st.button(label, key=key, use_container_width=True):
                    explore_topic = label

        st.iframe(
            """
            <script>
            (() => {
              const parentDoc = window.parent.document;
              const bindEnter = () => {
                const input = parentDoc.querySelector(
                  'textarea[aria-label="NC_TOP_TOPIC"]'
                );

                if (!input || input.dataset.iniEnterBound) {
                  return false;
                }

                input.dataset.iniEnterBound = "true";
                input.addEventListener("keydown", (event) => {
                  if (
                    event.key === "Enter"
                    && !event.shiftKey
                    && !event.ctrlKey
                    && !event.metaKey
                    && !event.isComposing
                  ) {
                    event.preventDefault();
                    event.stopPropagation();
                    input.dispatchEvent(new KeyboardEvent("keydown", {
                      key: "Enter",
                      code: "Enter",
                      ctrlKey: true,
                      bubbles: true,
                      cancelable: true,
                    }));
                  }
                });
                return true;
              };

              if (!bindEnter()) {
                let attempts = 0;
                const timer = window.setInterval(() => {
                  attempts += 1;
                  if (bindEnter() || attempts >= 20) {
                    window.clearInterval(timer);
                  }
                }, 50);
              }
            })();
            </script>
            """,
            height=1,
            tab_index=-1,
        )

        if illustrate_run:
            _queue_new_chat_request(
                st.session_state.chat_top_topic_input,
                "illustrate",
            )

        if explore_topic:
            _queue_new_chat_request(explore_topic, "interrogate")

        if run or st.session_state.chat_top_enter_submit:
            _queue_new_chat_request(
                st.session_state.chat_top_topic_input,
                "interrogate",
            )


    def _render_new_chat_bottom_uib() -> None:
        st.markdown(
            """
            <style>
            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) {
                position: fixed;
                z-index: 50;
                right: auto;
                bottom: 18px;
                left: 50%;
                width: min(980px, calc(100vw - 32px));
                margin: 0;
                padding: 7px 8px 7px 16px;
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: nowrap;
                border: 1px solid #d9dee4;
                border-radius: 18px;
                background: #ffffff;
                box-shadow: 0 7px 22px rgba(15, 23, 42, 0.075);
                transform: translateX(-50%);
            }

            [data-testid="stAppViewContainer"]:has(
                [data-testid="stSidebar"][aria-expanded="true"]
            ) div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) {
                left: calc(50% + 128px);
                width: min(980px, calc(100vw - 288px));
            }

            [data-testid="stMainBlockContainer"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) {
                padding-bottom: 112px !important;
            }

            [data-testid="stMain"]:has(.nc-pending-screen) {
                position: relative;
            }

            [data-testid="stMain"]:has(.nc-pending-screen)::before {
                position: absolute;
                z-index: 20;
                inset: 0;
                min-height: 100%;
                background: #ffffff;
                content: "";
                pointer-events: none;
            }

            [data-testid="stElementContainer"]:has(.nc-pending-query),
            [data-testid="stElementContainer"]:has(.nc-generation-placeholder) {
                position: relative;
                z-index: 30;
            }

            .nc-pending-query {
                position: fixed !important;
                z-index: 30;
                top: 104px;
                right: 32px;
                left: 32px;
                margin: 0 !important;
            }

            [data-testid="stAppViewContainer"]:has(
                [data-testid="stSidebar"][aria-expanded="true"]
            ) .nc-pending-query {
                left: 288px;
            }

            [data-testid="stMain"]:has(.nc-pending-screen)
            .nc-generation-placeholder {
                position: fixed;
                z-index: 30;
                top: 194px;
                left: 96px;
                width: min(920px, calc(100vw - 64px));
                margin: 0;
                transform: none;
            }

            [data-testid="stAppViewContainer"]:has(
                [data-testid="stSidebar"][aria-expanded="true"]
            ) [data-testid="stMain"]:has(.nc-pending-screen)
            .nc-generation-placeholder {
                left: 352px;
                width: min(920px, calc(100vw - 384px));
            }

            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_ai),
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_quantum),
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_cognitive),
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_kubernetes),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_ai),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_quantum),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_cognitive),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_kubernetes),
            [data-testid="stElementContainer"]:has(.nc-explore-label) {
                display: none !important;
            }

            [data-testid="stMainBlockContainer"]:has(input[aria-label="NC_BOTTOM_TOPIC"])::after {
                position: fixed;
                z-index: 40;
                right: 0;
                bottom: 0;
                left: 0;
                height: 88px;
                background: #ffffff;
                content: "";
                pointer-events: none;
            }

            [data-testid="stAppViewContainer"]:has(
                [data-testid="stSidebar"][aria-expanded="true"]
            ) [data-testid="stMainBlockContainer"]:has(input[aria-label="NC_BOTTOM_TOPIC"])::after {
                left: 256px;
            }

            .nc-generation-placeholder {
                width: min(100%, 920px);
                min-height: 0;
                margin: 14px 0 20px;
                padding: 4px 0;
                border: 0;
                border-radius: 0;
                background: transparent;
                box-shadow: none;
            }

            .nc-generation-copy {
                display: flex;
                align-items: center;
                gap: 10px;
                margin: 0;
                color: #5f6b7c;
                font-size: 16px;
                font-weight: 500;
                line-height: 1.4;
            }

            .nc-generation-icon {
                width: 15px;
                height: 25px;
                display: block;
                flex: 0 0 auto;
                object-fit: contain;
                animation: nc-generation-icon-breathe 1.45s ease-in-out infinite;
            }

            @keyframes nc-generation-icon-breathe {
                0%, 100% { opacity: 0.42; transform: scale(0.92); }
                50% { opacity: 1; transform: scale(1); }
            }

            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
            > div[data-testid="stColumn"]:first-child {
                width: 0 !important;
                min-width: 0 !important;
                flex: 1 1 auto !important;
            }

            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
            > div[data-testid="stColumn"]:nth-child(2) {
                width: 116px !important;
                min-width: 116px !important;
                flex: 0 0 116px !important;
            }

            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
            > div[data-testid="stColumn"]:nth-child(3) {
                width: 116px !important;
                min-width: 116px !important;
                flex: 0 0 116px !important;
            }

            div[data-testid="stTextInput"]:has(input[aria-label="NC_BOTTOM_TOPIC"]),
            div[data-testid="stTextInput"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) > div,
            div[data-testid="stTextInput"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
            [data-testid="stTextInputRootElement"] {
                border: 0 !important;
                outline: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextInput"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) div {
                background-color: transparent !important;
                background-image: none !important;
                box-shadow: none !important;
            }

            input[aria-label="NC_BOTTOM_TOPIC"],
            input[aria-label="NC_BOTTOM_TOPIC"]:focus,
            input[aria-label="NC_BOTTOM_TOPIC"]:active {
                width: 100% !important;
                height: 44px !important;
                min-height: 44px !important;
                padding: 0 !important;
                border: 0 !important;
                border-radius: 12px !important;
                outline: 0 !important;
                color: #111827 !important;
                background: transparent !important;
                box-shadow: none !important;
                font-size: 14px !important;
                caret-color: #f51b3f;
            }

            input[aria-label="NC_BOTTOM_TOPIC"]:-webkit-autofill,
            input[aria-label="NC_BOTTOM_TOPIC"]:-webkit-autofill:hover,
            input[aria-label="NC_BOTTOM_TOPIC"]:-webkit-autofill:focus {
                -webkit-text-fill-color: #111827 !important;
                -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
                box-shadow: 0 0 0 1000px #ffffff inset !important;
            }

            .st-key-nc_bottom_interrogate div.stButton > button,
            .st-key-nc_bottom_illustrate div.stButton > button {
                width: 100% !important;
                min-width: 0 !important;
                height: 40px !important;
                min-height: 40px !important;
                max-height: 40px !important;
                padding: 0 12px !important;
                margin: 0 !important;
                justify-content: center !important;
                overflow: hidden !important;
                border: 1px solid #071126 !important;
                border-radius: 14px !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                background: #071126 !important;
                box-shadow: none !important;
                white-space: nowrap !important;
            }

            .st-key-nc_bottom_interrogate div.stButton > button:hover,
            .st-key-nc_bottom_illustrate div.stButton > button:hover {
                border-color: #111d35 !important;
                background: #111d35 !important;
            }

            .st-key-nc_bottom_interrogate div.stButton > button p,
            .st-key-nc_bottom_interrogate div.stButton > button span,
            .st-key-nc_bottom_illustrate div.stButton > button p,
            .st-key-nc_bottom_illustrate div.stButton > button span {
                margin: 0 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                font-size: 12px !important;
                font-weight: 800 !important;
                line-height: 1 !important;
                letter-spacing: 0 !important;
                white-space: nowrap !important;
                overflow-wrap: normal !important;
                word-break: keep-all !important;
            }

            @media (max-width: 560px) {
                .nc-pending-query {
                    top: 82px;
                    right: 16px;
                    left: 16px !important;
                }

                [data-testid="stMain"]:has(.nc-pending-screen)
                .nc-generation-placeholder,
                [data-testid="stAppViewContainer"]:has(
                    [data-testid="stSidebar"][aria-expanded="true"]
                ) [data-testid="stMain"]:has(.nc-pending-screen)
                .nc-generation-placeholder {
                    top: 166px;
                    left: 16px;
                    width: calc(100vw - 32px);
                    transform: none;
                }

                div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) {
                    width: calc(100% - 12px);
                    padding: 7px;
                    display: grid !important;
                    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                    gap: 7px;
                }

                [data-testid="stAppViewContainer"]:has(
                    [data-testid="stSidebar"][aria-expanded="true"]
                ) div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) {
                    left: 50%;
                    width: calc(100% - 12px);
                    transform: translateX(-50%);
                }

                [data-testid="stMainBlockContainer"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) {
                    padding-bottom: 144px !important;
                }

                [data-testid="stMainBlockContainer"]:has(input[aria-label="NC_BOTTOM_TOPIC"])::after,
                [data-testid="stAppViewContainer"]:has(
                    [data-testid="stSidebar"][aria-expanded="true"]
                ) [data-testid="stMainBlockContainer"]:has(input[aria-label="NC_BOTTOM_TOPIC"])::after {
                    left: 0;
                    height: 124px;
                }

                div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
                > div[data-testid="stColumn"]:first-child {
                    width: auto !important;
                    min-width: 0 !important;
                    grid-column: 1 / -1;
                    flex: none !important;
                }

                div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
                > div[data-testid="stColumn"]:nth-child(2),
                div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"])
                > div[data-testid="stColumn"]:nth-child(3) {
                    width: auto !important;
                    min-width: 0 !important;
                    flex: none !important;
                }

                input[aria-label="NC_BOTTOM_TOPIC"] {
                    height: 40px !important;
                    min-height: 40px !important;
                    padding-inline: 9px !important;
                }

                .st-key-nc_bottom_interrogate div.stButton > button,
                .st-key-nc_bottom_illustrate div.stButton > button {
                    height: 38px !important;
                    min-height: 38px !important;
                    max-height: 38px !important;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        run = False
        illustrate_run = False
        composer_revision = st.session_state._nc_bottom_composer_revision
        composer_key = f"chat_bottom_topic_input_{composer_revision}"

        with st.container(key="nc_bottom_composer"):
            input_col, int_col, ill_col = st.columns(
                [8.5, 1.4, 1.4],
                gap="small"
            )

            with input_col:
                st.text_input(
                    "NC_BOTTOM_TOPIC",
                    key=composer_key,
                    label_visibility="collapsed",
                    placeholder="Ask InI anything to continue...",
                    on_change=_request_chat_bottom_enter_submit,
                )

            with int_col:
                run = st.button(
                    "Interrogate",
                    key="nc_bottom_interrogate",
                    use_container_width=True,
                )

            with ill_col:
                illustrate_run = st.button(
                    "Illustrate",
                    key="nc_bottom_illustrate",
                    use_container_width=True,
                )

        if illustrate_run:
            _queue_new_chat_request(
                st.session_state.get(composer_key, ""),
                "illustrate",
            )

        if run or st.session_state.chat_bottom_enter_submit:
            _queue_new_chat_request(
                st.session_state.get(composer_key, ""),
                "interrogate",
            )

        # A request rerun can leave a previous fixed composer mounted beside
        # this current one. Keep the current (last-rendered) owned composer
        # and remove only those stale complete composer nodes.
        st.iframe(
            """
            <script>
            (() => {
              const clean = () => {
                const doc = window.parent.document;
                const composers = Array.from(
                  doc.querySelectorAll('.st-key-nc_bottom_composer')
                );
                composers.slice(0, -1).forEach((composer) => composer.remove());
              };
              clean();
              requestAnimationFrame(clean);
              setTimeout(clean, 80);
            })();
            </script>
            """,
            height=1,
            tab_index=-1,
        )

    # Auto-run FUQ opened in a new tab for New Chat
    if chat_q and st.session_state.chat_seed_done != chat_q:
        try:
            if chat_sid:
                _load_new_chat_session(chat_sid)

            with st.spinner("Generating details... please wait."):
                resp = fetch_study(chat_q, mode="focused")
                answer = normalize_whitespace_for_readability(
                    normalize_mojibake(resp.get("answer", "") or "")
                ).strip() or "No answer generated."

                followups = resp.get("followups") or []
                _append_chat_branch(chat_q, "fuq")

                st.session_state.chat_direct_answer = {
                    "prompt": chat_q,
                    "text": answer,
                    "incomplete": bool(resp.get("incomplete")),
                    "stop_reason": resp.get("stop_reason") or None,
                    "mode": "focused",
                    "followups": followups,
                    "ts": now_label()
                }

                st.session_state.chat["interrogate"] = None
                st.session_state.chat_intro = ""
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()
                st.session_state.chat_seed_done = chat_q
                _persist_new_chat_session(st.session_state.chat_active_id or st.session_state.chat_loaded_sid)
            st.rerun()
        except Exception as e:
            st.error(f"Error auto-running chat FUQ: {e}")

    has_new_chat_content = any([
        st.session_state.chat.get("interrogate"),
        st.session_state.chat.get("illustrate"),
        st.session_state.chat_direct_answer,
        bool(st.session_state.chat_answers),
    ])
    pending_new_chat_request = st.session_state._nc_pending_request

    is_new_chat_landing = (
        not st.session_state.nc_started
        and not has_new_chat_content
        and not pending_new_chat_request
    )

    if is_new_chat_landing:
        _render_new_chat_top_uib()
    elif not pending_new_chat_request:
        active_chat_title = (st.session_state.chat_root_topic or "").strip()
        if st.session_state.chat_branch_answers:
            latest_branch = st.session_state.chat_branch_answers[-1]
            if isinstance(latest_branch, dict):
                active_chat_title = (
                    latest_branch.get("topic")
                    or latest_branch.get("prompt")
                    or active_chat_title
                )
        if not active_chat_title and isinstance(st.session_state.chat_direct_answer, dict):
            active_chat_title = (
                st.session_state.chat_direct_answer.get("prompt")
                or st.session_state.chat.get("topic")
                or ""
            )
        active_chat_title = active_chat_title or "New Chat"
        st.caption(
            "Explore the key ideas, profile and question ladder for this topic."
        )

    if has_new_chat_content:
        _render_nc_scroll_controls()

    if isinstance(pending_new_chat_request, dict) and not has_new_chat_content:
        pending_prompt = (pending_new_chat_request.get("prompt") or "").strip()
        pending_ts = (pending_new_chat_request.get("ts") or "").strip()
        st.markdown(
            """
            <style>
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_ai),
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_quantum),
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_cognitive),
            div[data-testid="stHorizontalBlock"]:has(.st-key-nc_explore_kubernetes),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_ai),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_quantum),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_cognitive),
            [data-testid="stElementContainer"]:has(.st-key-nc_explore_kubernetes),
            [data-testid="stElementContainer"]:has(.nc-explore-label) {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="nc-pending-screen" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        _render_nc_user_bubble(
            pending_prompt,
            pending_ts,
            extra_class="nc-pending-query",
        )

        generation_slot = st.empty()
        with generation_slot.container():
            _render_new_chat_generation_placeholder(
                (pending_new_chat_request.get("action") or "interrogate").strip().lower(),
                (pending_new_chat_request.get("status_mode") or "generating").strip().lower(),
            )

        _render_new_chat_bottom_uib()
        _generate_pending_new_chat_response(generation_slot)
        return

    illustrate_data = st.session_state.chat.get("illustrate")
    if isinstance(illustrate_data, dict) and (illustrate_data.get("illustration_text") or "").strip():
        _render_nc_user_bubble(
            st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "",
            st.session_state.chat_root_illustrate.get("ts", "") if isinstance(st.session_state.chat_root_illustrate, dict) else "",
)

        _render_simple_response(
            "root_response_card",
            "### Illustrations\n\n" + (illustrate_data.get("illustration_text") or ""),
            illustrate_data.get("ts") or "",
            topic_profile=_profile_for_response(
                st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "",
                mode_override="illustration",
            ),
        )

        if st.session_state.chat_branch_answers:
            root_has_open_answer_divider = any(
                q in st.session_state.chat_answers
                for q in st.session_state.chat_open_questions
            )
            if not root_has_open_answer_divider:
                st.markdown("---")
            total_branches = len(st.session_state.chat_branch_answers)
            for idx, item in enumerate(st.session_state.chat_branch_answers, start=1):
                kind = (item.get("kind") or "interrogate").strip().lower()
                topic = (item.get("topic") or item.get("prompt") or f"Continued topic {idx}").strip()
                ts = (item.get("ts") or "").strip()

                if idx == total_branches:
                    _render_nc_latest_scroll_target()

                _render_nc_user_bubble(topic, ts)

                if kind == "illustrate":
                    illustrate_payload = item.get("illustrate") or {}
                    illustration_text = ""
                    if isinstance(illustrate_payload, dict):
                        illustration_text = (illustrate_payload.get("illustration_text") or "").strip()

                    if illustration_text:
                        _render_branch_simple_response(
                            idx - 1,
                            illustration_text,
                            illustrate_payload.get("ts", ""),
                            topic_profile=_profile_for_response(
                                topic,
                                mode_override="illustration",
                            ),
                        )
                    else:
                        st.caption("No illustration generated.")

                elif kind == "direct":
                    direct_payload = item.get("direct_answer") or {}
                    raw_answer = (direct_payload.get("text") or "").strip() if isinstance(direct_payload, dict) else ""

                    if raw_answer:
                        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)
                        show_followups = bool(direct_payload.get("show_followups", True))
                        followups = embedded_followups or (direct_payload.get("followups") or [])
                        _render_branch_simple_response(
                            idx - 1,
                            clean_answer or raw_answer,
                            direct_payload.get("ts") or "",
                            followups if show_followups else None,
                            bool(
                                direct_payload.get("needs_clarification")
                                or direct_payload.get("show_action_buttons")
                            ),
                            (
                                direct_payload.get("response_mode") in {"carm", "conversation"}
                                and not bool(direct_payload.get("needs_clarification"))
                            ),
                            topic_profile=(
                                None
                                if direct_payload.get("suppress_profile")
                                else _profile_for_response(topic, direct_payload)
                            ),
                            compact_profile=(
                                direct_payload.get("response_mode") == "conversation"
                                and not direct_payload.get("suppress_profile")
                            ),
                            clarification_title=direct_payload.get("clarification_title") or "",
                            response_payload=direct_payload,
                        )

                    else:
                        st.caption("No direct answer generated.")

                else:
                    _render_branch_question_map(idx - 1, item)

                st.markdown("---")

        if isinstance(pending_new_chat_request, dict):
            _render_pending_new_chat_continuation(pending_new_chat_request)
        elif not chat_q:
            _render_nc_scroll_to_latest_once()
            _render_new_chat_bottom_uib()
        return

    direct_answer = st.session_state.chat_direct_answer
    if isinstance(direct_answer, dict) and (direct_answer.get("text") or "").strip():
        _render_nc_user_bubble(
            direct_answer.get("prompt") or st.session_state.chat.get("topic") or "",
            direct_answer.get("ts") or "",
        )

        raw_answer = (direct_answer.get("text") or "").strip()
        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

        show_followups = bool(direct_answer.get("show_followups", True))
        followups = embedded_followups or (direct_answer.get("followups") or [])

        _render_simple_response(
            "root_response_card",
            clean_answer or raw_answer,
            direct_answer.get("ts") or now_label(),
            followups if show_followups else None,
            bool(
                direct_answer.get("needs_clarification")
                or direct_answer.get("show_action_buttons")
            ),
            (
                direct_answer.get("response_mode") in {"carm", "conversation"}
                and not bool(direct_answer.get("needs_clarification"))
            ),
            topic_profile=(
                None
                if direct_answer.get("suppress_profile")
                else _profile_for_response(
                    direct_answer.get("prompt") or st.session_state.chat.get("topic") or "",
                    direct_answer,
                )
            ),
            compact_profile=(
                direct_answer.get("response_mode") == "conversation"
                and not direct_answer.get("suppress_profile")
            ),
            clarification_title=direct_answer.get("clarification_title") or "",
            response_payload=direct_answer,
        )

        # Direct/conversational roots have the same persistent branch timeline
        # as Question Map roots. Render every saved turn instead of showing only
        # the first casual query after a rerun or reload.
        if st.session_state.chat_branch_answers:
            st.markdown("---")
            total_branches = len(st.session_state.chat_branch_answers)
            for idx, item in enumerate(st.session_state.chat_branch_answers, start=1):
                kind = (item.get("kind") or "interrogate").strip().lower()
                topic = (
                    item.get("topic")
                    or item.get("prompt")
                    or f"Continued topic {idx}"
                ).strip()
                ts = (item.get("ts") or "").strip()

                if idx == total_branches:
                    _render_nc_latest_scroll_target()

                _render_nc_user_bubble(topic, ts)

                if kind == "illustrate":
                    illustrate_payload = item.get("illustrate") or {}
                    illustration_text = (
                        (illustrate_payload.get("illustration_text") or "").strip()
                        if isinstance(illustrate_payload, dict)
                        else ""
                    )
                    if illustration_text:
                        _render_branch_simple_response(
                            idx - 1,
                            illustration_text,
                            illustrate_payload.get("ts", ""),
                            topic_profile=_profile_for_response(
                                topic,
                                mode_override="illustration",
                            ),
                        )
                    else:
                        st.caption("No illustration generated.")
                elif kind == "direct":
                    branch_payload = item.get("direct_answer") or {}
                    raw_branch_answer = (
                        (branch_payload.get("text") or "").strip()
                        if isinstance(branch_payload, dict)
                        else ""
                    )
                    if raw_branch_answer:
                        clean_branch_answer, embedded_branch_followups = (
                            split_answer_and_embedded_followups(raw_branch_answer)
                        )
                        branch_followups = embedded_branch_followups or (
                            branch_payload.get("followups") or []
                        )
                        show_branch_followups = bool(
                            branch_payload.get("show_followups", True)
                        )
                        _render_branch_simple_response(
                            idx - 1,
                            clean_branch_answer or raw_branch_answer,
                            branch_payload.get("ts") or ts,
                            branch_followups if show_branch_followups else None,
                            bool(
                                branch_payload.get("needs_clarification")
                                or branch_payload.get("show_action_buttons")
                            ),
                            (
                                branch_payload.get("response_mode")
                                in {"carm", "conversation"}
                                and not bool(branch_payload.get("needs_clarification"))
                            ),
                            topic_profile=(
                                None
                                if branch_payload.get("suppress_profile")
                                else _profile_for_response(topic, branch_payload)
                            ),
                            compact_profile=(
                                branch_payload.get("response_mode") == "conversation"
                                and not branch_payload.get("suppress_profile")
                            ),
                            clarification_title=branch_payload.get("clarification_title") or "",
                            response_payload=branch_payload,
                        )
                    else:
                        st.caption("No direct answer generated.")
                else:
                    _render_branch_question_map(idx - 1, item)

                st.markdown("---")

        is_incomplete = bool(direct_answer.get("incomplete"))

        

        if is_incomplete and direct_answer.get("response_mode") != "carm":
                direct_key = "__chat_direct_answer__"

                if st.button("Continue", key="nc_cont_direct_answer"):
                    st.session_state._nc_continue_loading_q = direct_key
                    st.rerun()

                if st.session_state._nc_continue_loading_q == direct_key:
                    st.markdown("⏳ **Continuing...**")

                    previous_text = (direct_answer.get("text") or "").strip()
                    mode = (direct_answer.get("mode") or "focused").strip()
                    prompt = (direct_answer.get("prompt") or "").strip()

                    if previous_text and prompt:
                        try:
                            resp = fetch_study(
                                topic=prompt,
                                mode=mode,
                                continue_mode=True,
                                previous_answer=previous_text,
                            )

                            chunk = normalize_whitespace_for_readability(
                                normalize_mojibake(resp.get("answer", "") or "")
                            ).strip()

                            if chunk:
                                combined = (previous_text.rstrip() + "\n\n" + chunk).strip()
                            else:
                                combined = previous_text

                            st.session_state.chat_direct_answer = {
                                "prompt": prompt,
                                "text": combined,
                                "incomplete": bool(resp.get("incomplete")),
                                "stop_reason": resp.get("stop_reason") or None,
                                "mode": mode,
                                "followups": resp.get("followups") or direct_answer.get("followups") or [],
                                "intent": direct_answer.get("intent"),
                                "should_answer_direct": direct_answer.get("should_answer_direct", False),
                                "show_followups": direct_answer.get("show_followups", True),
                                "ts": now_label()
                            }
                            _persist_new_chat_session()

                        except Exception as e:
                            st.error(f"Error continuing answer: {e}")
                        finally:
                            st.session_state._nc_continue_loading_q = None

                        st.rerun()

        if isinstance(pending_new_chat_request, dict):
            _render_pending_new_chat_continuation(pending_new_chat_request)
        elif not chat_q:
            _render_nc_scroll_to_latest_once()
            _render_new_chat_bottom_uib()
        return

    data = st.session_state.chat.get("interrogate")
    if isinstance(data, dict) and data.get("categories"):
        _render_nc_user_bubble(
            st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "",
            st.session_state.chat_root_interrogate.get("ts", "") if isinstance(st.session_state.chat_root_interrogate, dict) else "",
        )

        



        _render_question_map_response_icon()
        with st.container(border=True, key="root_response_card"):
            root_ts = (
                st.session_state.chat_root_interrogate.get("ts", "")
                if isinstance(st.session_state.chat_root_interrogate, dict)
                else now_label()
            )
            continue_journey: dict[str, Any] = {}

            intro = st.session_state.chat_intro
            if intro:
                learning_paths, intro_without_paths = extract_learning_paths(intro)
                your_question, intro_without_question = extract_your_question(
                    intro_without_paths
                )
                core_explanation, intro_without_core = extract_core_explanation(
                    intro_without_question
                )
                learning_loop, intro_without_loop = extract_learning_loop(
                    intro_without_core
                )
                continue_journey, intro_without_journey = extract_continue_journey(
                    intro_without_loop
                )
                clean_intro, intro_followups = split_answer_and_embedded_followups(
                    intro_without_journey
                )
                profile_rows, intro_body = extract_topic_profile(clean_intro or intro)
                profile_rows, prerequisites = split_prerequisites(profile_rows)

                render_topic_profile(profile_rows)
                render_nc_prerequisites(prerequisites)
                if intro_body:
                    render_nc_intro_preview(intro_body)
                render_nc_your_question(your_question)
                render_nc_core_explanation(core_explanation)
                render_nc_learning_loop(learning_loop)

                if learning_paths:
                    render_nc_learning_paths(learning_paths)
                elif intro_followups:
                    render_nc_followup_panel(
                        intro_followups,
                        st.session_state.chat_active_id,
                    )

            cats = data.get("categories") or {}

            ladder = [
                ("Orientation", ["Orientation"]),
                ("Foundations", ["Foundations"]),
                ("Mechanisms", ["Mechanisms"]),
                ("Methods & Tools", ["Methods & Tools"]),
                ("Applications", ["Applications"]),
                ("Pitfalls", ["Pitfalls"]),
                ("Advanced / Future", ["Advanced / Future"]),
            ]

            question_map_panel = st.container(
                border=True,
                key="root_question_map_panel",
            )
            with question_map_panel:
                with st.container(
                    horizontal=True,
                    horizontal_alignment="distribute",
                    vertical_alignment="center",
                    gap="small",
                    key="root_qmap_header",
                ):
                    render_nc_section_title(
                        "Question Map",
                        card_class="ini-nc-qmap-marker",
                    )
                    hide_answers = st.toggle(
                        "Hide answers",
                        value=False,
                        key="hide_answers_newchat",
                    )

                question_map_content = question_map_panel
                selected_section = st.radio(
                    "Question Map section",
                    [section for section, _ in ladder],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="root_qm_section",
                )

            for section, cat_keys in ladder:
                qs = []

                for ck in cat_keys:
                    items = cats.get(ck) or []
                    for it in items:
                        q = (it.get("question") or "").strip()
                        if q and q not in qs:
                            qs.append(q)

                if not qs:
                    continue

                open_section = section == selected_section
                if open_section:
                    for q in qs:
                        visited = q in st.session_state.chat_visited_questions
                        is_open = q in st.session_state.chat_open_questions

                        button_label = f"✓ {q}" if visited else q

                        if question_map_content.button(
                            button_label,
                            key=f"q_{section}_{q}",
                            type="secondary",
                        ):
                            st.session_state.chat_visited_questions.add(q)

                            if is_open:
                                st.session_state.chat_open_questions.discard(q)
                                _sync_chat_root_snapshot()
                                _persist_new_chat_session()
                                st.rerun()

                            if q in st.session_state.chat_answers:
                                st.session_state.chat_open_questions.add(q)
                                _sync_chat_root_snapshot()
                                _persist_new_chat_session()
                                st.rerun()

                            try:
                                with question_map_content:
                                    with st.spinner("Generating details... please wait."):
                                        resp = fetch_study(q, mode="focused")
                                        answer = normalize_whitespace_for_readability(
                                            normalize_mojibake(resp.get("answer", "") or "")
                                        ).strip() or "No answer generated."

                                        followups = resp.get("followups") or []

                                        st.session_state.chat_answers[q] = {
                                            "text": answer,
                                            "incomplete": bool(resp.get("incomplete")),
                                            "stop_reason": resp.get("stop_reason") or None,
                                            "prompt": q,
                                            "mode": "deep",
                                        }
                                        st.session_state.chat_followups[q] = followups
                                        st.session_state.chat_open_questions.add(q)
                                        _sync_chat_root_snapshot()
                                        _persist_new_chat_session()

                                st.rerun()

                            except Exception as e:
                                question_map_content.error(f"Error calling /study/ai: {e}")

                        if q in st.session_state.chat_open_questions and not hide_answers:
                            answer_obj = st.session_state.chat_answers.get(q, {})
                            raw_answer = ""

                            if isinstance(answer_obj, dict):
                                raw_answer = (answer_obj.get("text") or "").strip()
                            else:
                                raw_answer = str(answer_obj or "").strip()

                            if raw_answer:
                                clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

                                followups = embedded_followups or st.session_state.chat_followups.get(q, [])
                                with question_map_content:
                                    _render_nc_ai_bubble(
                                        "#### Answer\n\n" + (clean_answer or raw_answer),
                                        "",
                                        answer_card_key=f"qmap_answer_card_{abs(hash(f'root:{section}:{q}'))}",
                                    )
                                    if followups:
                                        render_nc_section_title("Suggested Follow-ups")
                                        render_followup_links(
                                            "chat",
                                            followups,
                                            st.session_state.chat_active_id,
                                            target="_blank",
                                        )

                                is_incomplete = False
                                if isinstance(answer_obj, dict):
                                    is_incomplete = bool(answer_obj.get("incomplete"))

                                if is_incomplete:
                                    if st.button("Continue", key=f"nc_cont_{section}_{q}"):
                                        st.session_state._nc_continue_loading_q = q
                                        st.rerun()

                                    if st.session_state._nc_continue_loading_q == q:
                                        st.markdown("⏳ **Continuing...**")

                                        answer_obj = st.session_state.chat_answers.get(q, {})
                                        if isinstance(answer_obj, dict):
                                            previous_text = (answer_obj.get("text") or "").strip()
                                            mode = (answer_obj.get("mode") or "deep").strip()
                                        else:
                                            previous_text = str(answer_obj or "").strip()
                                            mode = "deep"

                                        if previous_text:
                                            try:
                                                resp = fetch_study(
                                                    topic=q,
                                                    mode=mode,
                                                    continue_mode=True,
                                                    previous_answer=previous_text,
                                                )

                                                chunk = normalize_whitespace_for_readability(
                                                    normalize_mojibake(resp.get("answer", "") or "")
                                                ).strip()

                                                if chunk:
                                                    combined = (previous_text.rstrip() + "\n\n" + chunk).strip()
                                                else:
                                                    combined = previous_text

                                                st.session_state.chat_answers[q] = {
                                                    "text": combined,
                                                    "incomplete": bool(resp.get("incomplete")),
                                                    "stop_reason": resp.get("stop_reason") or None,
                                                    "prompt": q,
                                                    "mode": mode,
                                                }

                                                if resp.get("followups"):
                                                    st.session_state.chat_followups[q] = resp.get("followups") or []

                                                _sync_chat_root_snapshot()
                                                _persist_new_chat_session()

                                            except Exception as e:
                                                st.error(f"Error continuing answer: {e}")

                                            finally:
                                                st.session_state._nc_continue_loading_q = None

                                            st.rerun()

                                question_map_panel.markdown("---")

            render_nc_continue_journey(continue_journey)
            st.markdown(
                f"<div style='margin-top:14px; text-align:right; color:#64748b; font-size:11px;'>{root_ts}</div>",
                unsafe_allow_html=True,
            )
        



                    

        if st.session_state.chat_branch_answers:
            st.markdown("---")
            total_branches = len(st.session_state.chat_branch_answers)
            for idx, item in enumerate(st.session_state.chat_branch_answers, start=1):
                kind = (item.get("kind") or "interrogate").strip().lower()
                topic = (item.get("topic") or item.get("prompt") or f"Continued topic {idx}").strip()
                ts = (item.get("ts") or "").strip()

                if idx == total_branches:
                    _render_nc_latest_scroll_target()

                _render_nc_user_bubble(topic, ts)

                if kind == "illustrate":
                    illustrate_payload = item.get("illustrate") or {}
                    illustration_text = ""
                    if isinstance(illustrate_payload, dict):
                        illustration_text = (illustrate_payload.get("illustration_text") or "").strip()

                    if illustration_text:
                        _render_branch_simple_response(
                            idx - 1,
                            illustration_text,
                            item.get("ts") or "",
                            topic_profile=_profile_for_response(
                                topic,
                                mode_override="illustration",
                            ),
                        )
                    else:
                        st.caption("No illustration generated.")

                elif kind == "direct":
                    direct_payload = item.get("direct_answer") or {}
                    raw_answer = (direct_payload.get("text") or "").strip() if isinstance(direct_payload, dict) else ""


                    if raw_answer:
                        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)
                        show_followups = bool(direct_payload.get("show_followups", True))
                        followups = embedded_followups or (direct_payload.get("followups") or [])
                        _render_branch_simple_response(
                            idx - 1,
                            clean_answer or raw_answer,
                            direct_payload.get("ts") or "",
                            followups if show_followups else None,
                            topic_profile=(
                                None
                                if direct_payload.get("suppress_profile")
                                else _profile_for_response(topic, direct_payload)
                            ),
                            compact_profile=(
                                direct_payload.get("response_mode") == "conversation"
                                and not direct_payload.get("suppress_profile")
                            ),
                            clarification_title=direct_payload.get("clarification_title") or "",
                            response_payload=direct_payload,
                        )
                    else:
                        st.caption("No direct answer generated.")

                
                        

                else:
                    _render_branch_question_map(idx - 1, item)

                st.markdown("---")

        if isinstance(pending_new_chat_request, dict):
            _render_pending_new_chat_continuation(pending_new_chat_request)
        else:
            _render_nc_scroll_to_latest_once()
            _render_new_chat_bottom_uib()
        return


def _continue_one_chunk(sess: Dict[str, Any], msg_id: str) -> None:
    idx = None
    for i, m in enumerate(sess["messages"]):
        if m.get("id") == msg_id:
            idx = i
            break
    if idx is None:
        return

    m = sess["messages"][idx]
    if m.get("role") != "assistant":
        return

    prompt = (m.get("prompt") or "").strip()
    mode = (m.get("mode") or "deep").strip()

    if not prompt:
        m["incomplete"] = False
        m["stop_reason"] = None
        return

    resp = fetch_study(
        topic=prompt,
        mode=mode,
        continue_mode=True,
        previous_answer=m.get("text") or "",
    )

    chunk_raw = normalize_mojibake(resp.get("answer", "") or "")
    chunk = normalize_whitespace_for_readability(chunk_raw).strip()

    if not chunk:
        m["incomplete"] = False
        m["stop_reason"] = None
        m["ts"] = now_label()
        return

    root_id = m.get("continued_root") or m.get("id")
    parts = 1
    for mm in sess["messages"]:
        if mm.get("role") == "assistant" and (mm.get("continued_root") or mm.get("id")) == root_id:
            if mm.get("continued_part"):
                parts = max(parts, int(mm["continued_part"]))

    next_part = parts + 1
    labeled = f"**Continued (Part {next_part})**\n\n{chunk}"

    m["incomplete"] = False
    m["stop_reason"] = None
    m["ts"] = now_label()

    followups = resp.get("followups") or []
    sess["messages"].append(
        {
            "id": new_msg_id("a"),
            "role": "assistant",
            "text": labeled,
            "ts": now_label(),
            "incomplete": bool(resp.get("incomplete")),
            "stop_reason": resp.get("stop_reason") or None,
            "prompt": prompt,
            "mode": mode,
            "continued_root": root_id,
            "continued_part": next_part,
            "followups": followups,
        }
    )

    _persist_learning_session(st.session_state.learning_active_id, sess)


def _mode_hint_text(mode: str) -> str:
    m = (mode or "deep").lower()
    if m == "high":
        return "Overview"
    if m == "quiz":
        return "Quiz"
    return "Deep (default)"


def _request_chat_top_enter_submit() -> None:
    st.session_state.chat_top_enter_submit = True

def _request_chat_bottom_enter_submit() -> None:
    st.session_state.chat_bottom_enter_submit = True


def _is_typed_continue_intent(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    if not t:
        return False
    t = re.sub(r"\s+", " ", t)

    intents = {
        "continue", "cont", "go ahead", "go on", "carry on", "next", "more",
        "yes", "y", "yeah", "yep", "ok", "okay", "sure", "pls continue",
        "please continue", "see more", "show more"
    }
    return t in intents


def _find_last_incomplete_assistant_id(sess: Dict[str, Any]) -> Optional[str]:
    for m in reversed(sess.get("messages", [])):
        if m.get("role") == "assistant" and needs_continue_flag(m):
            return m.get("id")
    return None


def _typed_continue_should_fire(sess: Dict[str, Any], user_text: str) -> bool:
    if not _is_typed_continue_intent(user_text):
        return False
    return _find_last_incomplete_assistant_id(sess) is not None


def _queue_learning_request(
    sess: Dict[str, Any],
    prompt: str,
    mode: str,
    *,
    display_prompt: Optional[str] = None,
    fetch_full: bool = False,
) -> bool:
    prompt = (prompt or "").strip()
    mode = (mode or "deep").strip().lower()
    if mode not in {"deep", "high", "quiz"}:
        mode = "deep"

    if (
        not prompt
        or st.session_state._mnl_pending_request
        or st.session_state._mnl_generating
    ):
        return False

    if _typed_continue_should_fire(sess, prompt):
        sess["messages"].append(
            {"id": new_msg_id("u"), "role": "user", "text": prompt, "ts": now_label(), "mode_label": mode_label(mode)}
        )

        target_id = _find_last_incomplete_assistant_id(sess)
        if target_id:
            st.session_state._mnl_continue_loading_id = target_id

        st.session_state.uib_text = ""
        _persist_learning_session(st.session_state.learning_active_id, sess)
        return True

    sess["messages"].append(
        {
            "id": new_msg_id("u"),
            "role": "user",
            "text": (display_prompt or prompt).strip(),
            "ts": now_label(),
            "mode_label": mode_label(mode),
        }
    )
    sess["last_prompt"] = (display_prompt or prompt).strip()
    st.session_state.uib_text = ""
    st.session_state._mnl_pending_request = {
        "prompt": prompt,
        "mode": mode,
        "fetch_full": bool(fetch_full),
    }
    _persist_learning_session(st.session_state.learning_active_id, sess)
    return True


def _consume_requested_learning_send(sess: Dict[str, Any]) -> None:
    payload = st.session_state._mnl_send_payload
    if not isinstance(payload, dict):
        return

    st.session_state._mnl_send_payload = None
    _queue_learning_request(
        sess,
        payload.get("prompt") or "",
        payload.get("mode") or "deep",
    )


def _render_learning_assistant_label() -> None:
    st.markdown(
        """
        <div class="mnl-assistant-label">
          <span class="mnl-assistant-mark">InI</span>
          <span>InI Tutor</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _generate_pending_learning_response(
    sess: Dict[str, Any],
    generation_slot: Any,
) -> None:
    pending = st.session_state._mnl_pending_request
    if not isinstance(pending, dict) or st.session_state._mnl_generating:
        return

    prompt = (pending.get("prompt") or "").strip()
    mode = (pending.get("mode") or "deep").strip().lower()
    fetch_full = bool(pending.get("fetch_full"))
    st.session_state._mnl_generating = True

    try:
        with generation_slot.container():
            with st.container(key="mnl_generation"):
                _render_learning_assistant_label()
                with st.spinner("Generating answer... may take some time."):
                    if fetch_full:
                        resp = fetch_study_full(prompt, mode=mode)
                    else:
                        resp = fetch_study(prompt, mode=mode)

            answer = normalize_whitespace_for_readability(normalize_mojibake(resp.get("answer", "") or "")) or "No answer generated."
            followups = resp.get("followups") or []
            sess["messages"].append(
                {
                    "id": new_msg_id("a"),
                    "role": "assistant",
                    "text": answer,
                    "ts": now_label(),
                    "incomplete": bool(resp.get("incomplete")),
                    "stop_reason": resp.get("stop_reason") or None,
                    "prompt": prompt,
                    "mode": mode,
                    "response_id": resp.get("response_id"),
                    "continue_token": resp.get("continue_token"),
                    "followups": followups,
                }
            )
    except Exception as e:
        sess["messages"].append({"id": new_msg_id("e"), "role": "assistant", "text": f"Error calling API: {e}", "ts": now_label()})
    finally:
        st.session_state._mnl_pending_request = None
        st.session_state._mnl_generating = False
        _persist_learning_session(st.session_state.learning_active_id, sess)

    st.rerun()


def _render_user_mode_hint(mode_lbl: str) -> None:
    active = (mode_lbl or "Deep").strip()
    lines = [
        ("➤", "Deep (default)"),
        ("◎", "Overview"),
        ("?", "Quiz"),
    ]
    for ico, label in lines:
        if label.startswith(active):
            st.caption(f"**{ico} {label}**")
        else:
            st.caption(f"{ico} {label}")


def _render_my_learning_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"]:has(.mnl-page-marker) {
          width: 100%;
          max-width: 1280px;
          margin-left: auto;
          margin-right: auto;
          padding-top: 1.8rem;
          padding-bottom: 2rem;
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-empty-spacer) {
          max-width: none;
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-empty-spacer) .mnl-header {
          width: min(100%, 840px);
        }
        [data-testid="stVerticalBlock"]:has(.mnl-page-marker) {
          min-height: calc(100vh - 64px);
        }
        .mnl-page-marker { display: none; }
        .mnl-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 0;
        }
        .mnl-title {
          color: #111827;
          font-size: 32px;
          font-weight: 780;
          line-height: 1.15;
        }
        .mnl-status {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: #92400e;
          font-size: 13px;
          font-weight: 650;
          white-space: nowrap;
        }
        .mnl-status::before {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #f59e0b;
          content: "";
        }
        .mnl-mode-label {
          margin-bottom: 7px;
          color: #6b7280;
          font-size: 12px;
          font-weight: 650;
          text-transform: uppercase;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-mnl_mode_deep) {
          width: min(100%, 520px);
          gap: 4px;
          flex-wrap: nowrap;
          padding: 4px;
          border: 1px solid #dfe3e8;
          border-radius: 7px;
          background: #f4f6f7;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-mnl_mode_deep)
        > div[data-testid="stColumn"] {
          width: 0 !important;
          min-width: 0 !important;
          flex: 1 1 0 !important;
        }
        .st-key-mnl_mode_deep button,
        .st-key-mnl_mode_overview button,
        .st-key-mnl_mode_quiz button {
          min-width: 0 !important;
          height: 38px;
          border: 0 !important;
          border-radius: 5px !important;
          box-shadow: none !important;
          font-weight: 650 !important;
        }
        .st-key-mnl_mode_deep button[kind="secondary"],
        .st-key-mnl_mode_overview button[kind="secondary"],
        .st-key-mnl_mode_quiz button[kind="secondary"] {
          color: #4b5563 !important;
          background: transparent !important;
        }
        .st-key-mnl_mode_deep button[kind="primary"],
        .st-key-mnl_mode_overview button[kind="primary"],
        .st-key-mnl_mode_quiz button[kind="primary"] {
          color: #ffffff !important;
          background: #087f7b !important;
        }
        .mnl-divider {
          height: 1px;
          margin: 18px 0 26px;
          background: #e5e7eb;
        }
        .mnl-assistant-label {
          display: flex;
          align-items: center;
          gap: 9px;
          margin: 0 0 13px;
          color: #374151;
          font-size: 13px;
          font-weight: 700;
        }
        .mnl-assistant-mark {
          display: inline-flex;
          width: 29px;
          height: 29px;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          color: #ffffff;
          background: #087f7b;
          font-size: 11px;
        }
        .mnl-mode-tag {
          display: inline-block;
          margin-top: 9px;
          color: #4f625e;
          font-size: 11px;
          font-weight: 650;
        }
        [class*="st-key-mnl_user_"] {
          width: min(72%, 680px);
          margin-left: auto;
          margin-bottom: 18px;
          padding: 15px 17px 11px;
          border: 1px solid #d8e4e1;
          border-radius: 8px;
          background: #f2f7f6;
          box-shadow: 0 3px 12px rgba(15, 23, 42, 0.05);
        }
        [class*="st-key-mnl_user_"] p {
          margin-bottom: 0;
          line-height: 1.5;
        }
        [class*="st-key-mnl_assistant_"],
        .st-key-mnl_generation {
          width: min(calc(92% + 12px), 912px);
          margin-right: auto;
          margin-bottom: 22px;
          padding: 17px 19px 13px;
          border: 1px solid #e1e6e5;
          border-radius: 8px;
          background: #ffffff;
          box-shadow: 0 4px 16px rgba(15, 23, 42, 0.055);
          transform: translateX(-12px);
        }
        [class*="st-key-mnl_assistant_"] p,
        [class*="st-key-mnl_assistant_"] li {
          line-height: 1.55;
        }
        @media (min-width: 1200px) {
          [data-testid="stAppViewContainer"]:has(
            [data-testid="stSidebar"][aria-expanded="true"]
          ) [class*="st-key-mnl_assistant_"],
          [data-testid="stAppViewContainer"]:has(
            [data-testid="stSidebar"][aria-expanded="true"]
          ) .st-key-mnl_generation {
            --mnl-left-extension:
              clamp(12px, calc(38vw - 486px), 240px);
            width:
              min(calc(92% + var(--mnl-left-extension)), 1152px);
            transform:
              translateX(calc(0px - var(--mnl-left-extension)));
          }
        }
        .mnl-message-time {
          margin-top: 10px;
          color: #73807d;
          font-size: 11px;
          line-height: 1.25;
          text-align: right;
        }
        [class*="st-key-mnl_user_"]
        [data-testid="stMarkdownContainer"]:has(.mnl-message-time),
        [class*="st-key-mnl_assistant_"]
        [data-testid="stMarkdownContainer"]:has(.mnl-message-time) {
          margin-bottom: 0 !important;
        }
        .st-key-mnl_generation {
          min-height: 92px;
        }
        .st-key-mnl_generation [data-testid="stSpinner"] {
          margin-top: 3px;
          color: #52606d;
        }
        .mnl-empty-spacer {
          height: clamp(150px, calc(50vh - 125px), 320px);
        }
        [data-testid="stElementContainer"]:has(.mnl-active-spacer) {
          min-height: 44px;
          flex: 1 1 auto;
        }
        .mnl-active-spacer { height: 100%; }
        [data-testid="stMainBlockContainer"]:has(.mnl-page-marker) {
          padding-bottom: 7.5rem;
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)::after {
          position: fixed;
          z-index: 40;
          right: 0;
          bottom: 0;
          left: 0;
          height: 96px;
          background: #ffffff;
          content: "";
          pointer-events: none;
        }
        [data-testid="stAppViewContainer"]:has(
          [data-testid="stSidebar"][aria-expanded="true"]
        ) [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)::after {
          left: 256px;
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)
        [data-testid="stForm"]:has(input[aria-label="MNL_PROMPT"]) {
          position: fixed;
          z-index: 50;
          bottom: 18px;
          left: 50%;
          width: min(1110px, calc(100vw - 32px));
          height: auto !important;
          transform: translateX(-50%);
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)
        [data-testid="stForm"]:has(input[aria-label="MNL_PROMPT"])
        > [data-testid="stVerticalBlock"] {
          height: auto !important;
          flex: 0 0 auto !important;
        }
        [data-testid="stAppViewContainer"]:has(
          [data-testid="stSidebar"][aria-expanded="true"]
        ) [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)
        [data-testid="stForm"]:has(input[aria-label="MNL_PROMPT"]) {
          left: calc(50% + 128px);
          width: min(1110px, calc(100vw - 288px));
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"]) {
          width: min(100%, 920px);
          align-items: center;
          gap: 10px;
          flex-wrap: nowrap;
          margin-inline: auto;
          padding: 7px 8px 7px 17px;
          border: 1px solid #cfd5da;
          border-radius: 999px;
          background: #ffffff;
          box-shadow: 0 7px 22px rgba(17, 24, 39, 0.08);
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"] {
          min-width: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:first-child {
          width: auto !important;
          flex: 1 1 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(n+2) {
          width: 44px !important;
          flex: 0 0 44px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(1) { order: 1; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(2) { order: 4; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(3) { order: 2; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(4) { order: 3; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        [data-testid="stTextInput"],
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        [data-testid="stTextInputRootElement"] {
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        [data-testid="stTextInputRootElement"] > div {
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"]) input,
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"]) input:focus,
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"]) input:active {
          min-height: 43px;
          padding: 0 !important;
          color: #111827;
          outline: none !important;
          background-color: transparent !important;
          background-image: none !important;
          box-shadow: none !important;
          caret-color: #087f7b;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        input:-webkit-autofill,
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        input:-webkit-autofill:hover,
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        input:-webkit-autofill:focus {
          -webkit-text-fill-color: #111827 !important;
          -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
          box-shadow: 0 0 0 1000px #ffffff inset !important;
        }
        .st-key-mnl_quiz button,
        .st-key-mnl_overview button,
        .st-key-mnl_send button {
          width: 44px !important;
          min-width: 44px !important;
          height: 44px !important;
          padding: 0 !important;
          border: 1px solid #cbd2d8 !important;
          border-radius: 50% !important;
          font-size: 18px !important;
          line-height: 1 !important;
          box-shadow: 0 2px 7px rgba(15, 23, 42, 0.07) !important;
          transition: transform 120ms ease, border-color 120ms ease,
            background 120ms ease, box-shadow 120ms ease;
        }
        .st-key-mnl_quiz button:hover,
        .st-key-mnl_overview button:hover,
        .st-key-mnl_send button:hover {
          transform: translateY(-1px);
          border-color: #8ca7a1 !important;
          box-shadow: 0 4px 10px rgba(15, 23, 42, 0.1) !important;
        }
        .st-key-mnl_quiz button:disabled,
        .st-key-mnl_overview button:disabled,
        .st-key-mnl_send button:disabled {
          transform: none;
          box-shadow: none !important;
        }
        .st-key-mnl_quiz button,
        .st-key-mnl_overview button {
          position: relative;
          font-size: 0 !important;
        }
        .st-key-mnl_quiz button p,
        .st-key-mnl_overview button p {
          position: absolute !important;
          width: 1px !important;
          height: 1px !important;
          padding: 0 !important;
          margin: -1px !important;
          overflow: hidden !important;
          clip: rect(0, 0, 0, 0) !important;
          white-space: nowrap !important;
        }
        .st-key-mnl_quiz button::before,
        .st-key-mnl_overview button::before {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 22px;
          height: 22px;
          display: block;
          background: currentColor;
          content: "";
          transform: translate(-50%, -50%);
          -webkit-mask-position: center;
          -webkit-mask-repeat: no-repeat;
          -webkit-mask-size: contain;
          mask-position: center;
          mask-repeat: no-repeat;
          mask-size: contain;
        }
        .st-key-mnl_quiz button::before {
          -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%20fill='none'%20stroke='black'%20stroke-width='1.8'%20stroke-linecap='round'%20stroke-linejoin='round'%3E%3Cpath%20d='m3%207%202%202%204-4'/%3E%3Cpath%20d='M13%206h8'/%3E%3Cpath%20d='m3%2017%202%202%204-4'/%3E%3Cpath%20d='M13%2018h8'/%3E%3Cpath%20d='M13%2012h8'/%3E%3C/svg%3E");
          mask-image: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%20fill='none'%20stroke='black'%20stroke-width='1.8'%20stroke-linecap='round'%20stroke-linejoin='round'%3E%3Cpath%20d='m3%207%202%202%204-4'/%3E%3Cpath%20d='M13%206h8'/%3E%3Cpath%20d='m3%2017%202%202%204-4'/%3E%3Cpath%20d='M13%2018h8'/%3E%3Cpath%20d='M13%2012h8'/%3E%3C/svg%3E");
        }
        .st-key-mnl_overview button::before {
          -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%20fill='none'%20stroke='black'%20stroke-width='1.8'%20stroke-linecap='round'%20stroke-linejoin='round'%3E%3Cpath%20d='m12.83%202.18a2%202%200%200%200-1.66%200L2.6%206.08a1%201%200%200%200%200%201.83l8.58%203.91a2%202%200%200%200%201.66%200l8.58-3.9a1%201%200%200%200%200-1.83z'/%3E%3Cpath%20d='m22%2012.5-9.17%204.17a2%202%200%200%201-1.66%200L2%2012.5'/%3E%3Cpath%20d='m22%2017.5-9.17%204.17a2%202%200%200%201-1.66%200L2%2017.5'/%3E%3C/svg%3E");
          mask-image: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%20fill='none'%20stroke='black'%20stroke-width='1.8'%20stroke-linecap='round'%20stroke-linejoin='round'%3E%3Cpath%20d='m12.83%202.18a2%202%200%200%200-1.66%200L2.6%206.08a1%201%200%200%200%200%201.83l8.58%203.91a2%202%200%200%200%201.66%200l8.58-3.9a1%201%200%200%200%200-1.83z'/%3E%3Cpath%20d='m22%2012.5-9.17%204.17a2%202%200%200%201-1.66%200L2%2012.5'/%3E%3Cpath%20d='m22%2017.5-9.17%204.17a2%202%200%200%201-1.66%200L2%2017.5'/%3E%3C/svg%3E");
        }
        .st-key-mnl_send [aria-label="Shortcut Enter"] {
          display: none !important;
        }
        .st-key-mnl_quiz button[kind^="secondary"],
        .st-key-mnl_overview button[kind^="secondary"],
        .st-key-mnl_send button[kind^="secondary"] {
          color: #374151 !important;
          background: #ffffff !important;
        }
        .st-key-mnl_quiz button[kind^="primary"],
        .st-key-mnl_overview button[kind^="primary"],
        .st-key-mnl_send button[kind^="primary"] {
          color: #ffffff !important;
          border-color: #087f7b !important;
          background: #087f7b !important;
        }
        .st-key-mnl_send button[kind^="primary"] {
          border-color: #f51b3f !important;
          background: #f51b3f !important;
        }
        .st-key-mnl_quiz button,
        .st-key-mnl_overview button,
        .st-key-mnl_quiz button[kind^="secondary"],
        .st-key-mnl_overview button[kind^="secondary"] {
          color: #34433f !important;
          border-color: transparent !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        .st-key-mnl_quiz button:hover,
        .st-key-mnl_overview button:hover {
          color: #087f7b !important;
          border-color: transparent !important;
          background: #edf6f4 !important;
          box-shadow: none !important;
          transform: none;
        }
        .st-key-mnl_quiz button[kind^="primary"],
        .st-key-mnl_overview button[kind^="primary"] {
          color: #087f7b !important;
          border-color: transparent !important;
          background: #dff1ed !important;
          box-shadow: none !important;
        }
        @media (max-width: 700px) {
          [data-testid="stMainBlockContainer"]:has(.mnl-page-marker) { padding-top: 1.1rem; }
          [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)
          [data-testid="stForm"]:has(input[aria-label="MNL_PROMPT"]),
          [data-testid="stAppViewContainer"]:has(
            [data-testid="stSidebar"][aria-expanded="true"]
          ) [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)
          [data-testid="stForm"]:has(input[aria-label="MNL_PROMPT"]) {
            bottom: 10px;
            left: 50%;
            width: calc(100vw - 20px);
          }
          [data-testid="stAppViewContainer"]:has(
            [data-testid="stSidebar"][aria-expanded="true"]
          ) [data-testid="stMainBlockContainer"]:has(.mnl-active-spacer)::after {
            left: 0;
          }
          .mnl-header {
            align-items: flex-start;
            flex-direction: column;
            gap: 7px;
          }
          .mnl-title { font-size: 27px; }
          [class*="st-key-mnl_user_"] {
            width: 92%;
          }
          [class*="st-key-mnl_assistant_"],
          .st-key-mnl_generation {
            width: 100%;
            transform: none;
          }
          .mnl-empty-spacer { height: 120px; }
        }
        </style>
        <div class="mnl-page-marker"></div>
        """,
        unsafe_allow_html=True,
    )


def _render_learning_mode_tag(mode_lbl: str) -> None:
    active = (mode_lbl or "Deep").strip()
    if active not in {"Deep", "Overview", "Quiz"}:
        active = "Deep"
    st.markdown(
        f'<span class="mnl-mode-tag">{active} mode</span>',
        unsafe_allow_html=True,
    )


def _set_learning_mode(mode: str) -> None:
    st.session_state.uib_mode = mode
    st.rerun()


def page_my_new_learning() -> None:
    _render_my_learning_styles()
    st.markdown(
        """
        <div class="mnl-header">
          <div class="mnl-title">My New Learning</div>
          <div class="mnl-status">In active development</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]

    if "learn_seed_done" not in st.session_state:
        st.session_state.learn_seed_done = ""

    if learn_q and st.session_state.learn_seed_done != learn_q:
        resolved_learn_q = normalize_clicked_followup_prompt(learn_q)
        if _queue_learning_request(
            sess,
            resolved_learn_q,
            "deep",
            display_prompt=learn_q,
            fetch_full=True,
        ):
            st.session_state.learn_seed_done = learn_q

    _consume_requested_learning_send(sess)

    last_incomplete_id = None
    for mm in reversed(sess.get("messages", [])):
        if mm.get("role") == "assistant" and needs_continue_flag(mm):
            last_incomplete_id = mm.get("id")
            break

    for message_index, msg in enumerate(sess["messages"]):
        role = msg.get("role", "assistant")
        ts = msg.get("ts") or ""
        text = normalize_whitespace_for_readability(
            normalize_mojibake(msg.get("text", "") or "")
        )
        message_id = msg.get("id") or f"legacy_{message_index}"

        if role == "user":
            with st.container(key=f"mnl_user_{message_id}"):
                st.markdown(text)
                _render_learning_mode_tag(msg.get("mode_label") or "Deep")
                if ts:
                    st.markdown(
                        f'<div class="mnl-message-time">{ts}</div>',
                        unsafe_allow_html=True,
                    )

        else:
            if (msg.get("text") or "").lstrip().startswith("**Continued (Part "):
                st.markdown("---")

            with st.container(key=f"mnl_assistant_{message_id}"):
                _render_learning_assistant_label()

                clean_answer, embedded_followups = split_answer_and_embedded_followups(text)
                st.markdown(clean_answer or text)

                followups = embedded_followups or (msg.get("followups") or [])
                if followups:
                    st.markdown("#### Suggested follow-ups")
                    render_followup_links(
                        "learn",
                        followups,
                        st.session_state.learning_active_id,
                        target="_self",
                    )

                if needs_continue_flag(msg) and (msg.get("id") == last_incomplete_id):
                    msg_id = msg.get("id")

                    if st.button("Continue", key=f"cont-{msg_id}"):
                        st.session_state._mnl_continue_loading_id = msg_id
                        st.rerun()

                    if st.session_state._mnl_continue_loading_id == msg_id:
                        st.markdown("⏳ **Continuing...**")

                        try:
                            _continue_one_chunk(sess, msg_id)

                        except Exception as e:
                            sess["messages"].append(
                                {
                                    "id": new_msg_id("e"),
                                    "role": "assistant",
                                    "text": f"Error continuing: {e}",
                                    "ts": now_label(),
                                }
                            )

                        finally:
                            st.session_state._mnl_continue_loading_id = None

                        st.rerun()

                if ts:
                    st.markdown(
                        f'<div class="mnl-message-time">{ts}</div>',
                        unsafe_allow_html=True,
                    )

    generation_slot = st.empty()

    spacer_class = "mnl-active-spacer" if sess["messages"] else "mnl-empty-spacer"
    st.markdown(f'<div class="{spacer_class}"></div>', unsafe_allow_html=True)

    current_mode = st.session_state.uib_mode
    composer_busy = bool(
        st.session_state._mnl_pending_request
        or st.session_state._mnl_generating
    )
    composer_revision = st.session_state._mnl_composer_revision
    composer_text_key = f"mnl_prompt_{composer_revision}"
    with st.form(
        "mnl_composer",
        clear_on_submit=False,
        enter_to_submit=True,
        border=False,
    ):
        input_cols = st.columns([11, 0.75, 0.75, 0.75], gap="small")
        with input_cols[0]:
            st.text_input(
                "MNL_PROMPT",
                key=composer_text_key,
                label_visibility="collapsed",
                placeholder="Ask InI anything to learn...",
                disabled=composer_busy,
            )

        with input_cols[1]:
            with st.container(key="mnl_send"):
                send_submitted = st.form_submit_button(
                    "➤",
                    help="Send (Deep by default)",
                    type="primary" if current_mode == "deep" else "secondary",
                    disabled=composer_busy,
                    shortcut="Enter",
                )

        with input_cols[2]:
            with st.container(key="mnl_quiz"):
                quiz_selected = st.form_submit_button(
                    "Quiz",
                    help="Quiz",
                    type="primary" if current_mode == "quiz" else "secondary",
                    disabled=composer_busy,
                )

        with input_cols[3]:
            with st.container(key="mnl_overview"):
                overview_selected = st.form_submit_button(
                    "Overview",
                    help="Overview",
                    type="primary" if current_mode == "high" else "secondary",
                    disabled=composer_busy,
                )

    if quiz_selected:
        _set_learning_mode("deep" if current_mode == "quiz" else "quiz")
    elif overview_selected:
        _set_learning_mode("deep" if current_mode == "high" else "high")
    elif send_submitted:
        st.session_state._mnl_send_payload = {
            "prompt": st.session_state.get(composer_text_key, ""),
            "mode": current_mode,
        }
        st.session_state._mnl_composer_revision += 1
        st.rerun()

    if st.session_state._mnl_pending_request:
        _generate_pending_learning_response(sess, generation_slot)

def page_new_project() -> None:
    st.markdown('<div class="bigtitle">New Project</div>', unsafe_allow_html=True)
    st.info("Coming soon in v1.", icon="🧩")


# =========================
# Router
# =========================
if st.session_state.page == "Home":
    page_home()
elif st.session_state.page == "New Chat":
    page_new_chat()
elif st.session_state.page == "My New Learning":
    page_my_new_learning()
else:
    page_new_project()


# =========================
# First Conversation Experience — static shell (Stage 2)
# =========================
fce_action = st.session_state.fce_pending_action
if fce_action:
    st.session_state.fce_pending_action = None
    st.session_state.fce_static_open = False
    st.session_state.fce_force_open = False
    if fce_action == "go-introduction":
        _reset_query_to_page("home")
    elif fce_action == "go-chat":
        _reset_query_to_page("chat")
    st.rerun()

if st.session_state.fce_static_open:
    fce_icon_path = Path(__file__).with_name("ini_buta_icon_cropped.png")
    fce_icon_data = "data:image/png;base64," + base64.b64encode(
        fce_icon_path.read_bytes()
    ).decode("ascii")
    fce_action = render_fce(
        messages=FCE_MESSAGES,
        topics=FCE_TOPIC_EXAMPLES,
        quote=st.session_state.fce_quote,
        icon_data=fce_icon_data,
        force_open=st.session_state.fce_force_open,
        on_action_change=_capture_fce_action,
    )

    if fce_action:
        st.session_state.fce_static_open = False
        if fce_action == "go-introduction":
            _reset_query_to_page("home")
        elif fce_action == "go-chat":
            _reset_query_to_page("chat")
        st.rerun()
