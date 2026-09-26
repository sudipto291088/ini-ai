"""Compact animated release notice for the empty New Chat landing screen."""

from typing import Optional

import streamlit as st


_NEW_CHAT_UPDATE = st.components.v2.component(
    "ini_new_chat_update_v11",
    html='<div id="ini-new-chat-update-root"></div>',
    css="""
    #ini-new-chat-update-root {
      width: min(100%, 820px);
      height: 50px;
      margin: 0 auto;
      overflow: hidden;
      background: transparent;
      box-shadow: none;
      font-family: Aptos, "Segoe UI", system-ui, sans-serif;
    }
    .ini-update-notice {
      position: relative;
      width: 100%;
      height: 100%;
      background: transparent;
      color: var(--st-text-color, #17211f);
    }
    .ini-update-mukut {
      position: absolute;
      top: 50%;
      left: 50%;
      width: 15px;
      height: 27px;
      object-fit: contain;
      opacity: 0;
      filter: drop-shadow(0 3px 7px rgba(245, 27, 63, .16));
      transform: translate(-50%, -50%) scale(.78);
      transform-origin: center;
    }
    .ini-update-copy {
      position: absolute;
      top: 50%;
      left: 40px;
      right: 4px;
      min-width: 0;
      opacity: 0;
      transform: translate(10px, -50%);
    }
    .ini-update-kicker {
      display: block;
      margin-bottom: 2px;
      color: var(--st-primary-color, #f51b3f);
      font-size: 9px;
      font-weight: 760;
      line-height: 1.1;
    }
    .ini-update-message {
      display: block;
      overflow: hidden;
      color: var(--st-text-color, #17211f);
      font-size: 13px;
      font-weight: 650;
      line-height: 1.25;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ini-update-notice.is-animated .ini-update-mukut {
      animation: ini-update-mukut 1.75s cubic-bezier(.22, .8, .28, 1) forwards;
    }
    .ini-update-notice.is-animated .ini-update-copy {
      animation: ini-update-copy .48s ease 1.48s forwards;
    }
    .ini-update-notice.is-settled .ini-update-mukut {
      left: 12px;
      opacity: 1;
      transform: translate(0, -50%) scale(1);
    }
    .ini-update-notice.is-settled .ini-update-copy {
      opacity: 1;
      transform: translate(0, -50%);
    }
    @keyframes ini-update-mukut {
      0% { left: 50%; opacity: 0; transform: translate(-50%, -50%) scale(.72); }
      18% { opacity: 1; transform: translate(-50%, -50%) scale(1.08); }
      30% { opacity: .34; transform: translate(-50%, -50%) scale(.92); }
      42% { opacity: 1; transform: translate(-50%, -50%) scale(1.06); }
      55% { left: 50%; opacity: 1; transform: translate(-50%, -50%) scale(1); }
      100% { left: 12px; opacity: 1; transform: translate(0, -50%) scale(1); }
    }
    @keyframes ini-update-copy {
      to { opacity: 1; transform: translate(0, -50%); }
    }
    @media (max-width: 640px) {
      #ini-new-chat-update-root { width: calc(100% - 24px); height: 54px; }
      .ini-update-copy { left: 34px; right: 4px; }
      .ini-update-message {
        overflow: visible;
        font-size: 12px;
        line-height: 1.25;
        text-overflow: clip;
        white-space: normal;
      }
      .ini-update-mukut { width: 14px; height: 25px; }
      .ini-update-notice.is-settled .ini-update-mukut { left: 8px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .ini-update-notice.is-animated .ini-update-mukut,
      .ini-update-notice.is-animated .ini-update-copy { animation: none; }
      .ini-update-notice.is-animated .ini-update-mukut {
        left: 12px;
        opacity: 1;
        transform: translate(0, -50%) scale(1);
      }
      .ini-update-notice.is-animated .ini-update-copy {
        opacity: 1;
        transform: translate(0, -50%);
      }
    }
    """,
    js="""
    export default function (component) {
      const { data, parentElement } = component;
      const root = parentElement.querySelector('#ini-new-chat-update-root');
      if (!root) return;

      const version = String(data.version || 'latest');
      const seenKey = `ini-new-chat-update:v3:${version}`;
      const shouldAnimate = sessionStorage.getItem(seenKey) !== '1';
      root.innerHTML = `
        <section class="ini-update-notice"
          aria-label="New in ${data.version}: ${data.message}">
          <img class="ini-update-mukut" src="${data.icon_data}" alt="Mukut">
          <span class="ini-update-copy">
            <span class="ini-update-kicker">New in ${data.version}</span>
            <span class="ini-update-message">${data.message}</span>
          </span>
        </section>`;

      const notice = root.querySelector('.ini-update-notice');
      let splashPollTimer = null;
      let revealTimer = null;
      const waitForNewChat = () => {
        if (sessionStorage.getItem('ini_opening_splash_seen_session') !== '1') {
          splashPollTimer = window.setTimeout(waitForNewChat, 100);
          return;
        }
        revealTimer = window.setTimeout(() => {
          notice?.classList.add(shouldAnimate ? 'is-animated' : 'is-settled');
          if (shouldAnimate) sessionStorage.setItem(seenKey, '1');
        }, 3000);
      };
      waitForNewChat();

      return () => {
        window.clearTimeout(splashPollTimer);
        window.clearTimeout(revealTimer);
      };
    }
    """,
)


def render_new_chat_update(
    *,
    icon_data: str,
    version: str = "v0.1.7",
    message: str = "Learn an entire subject through questions",
    key: Optional[str] = "ini-new-chat-update-v017",
) -> None:
    """Render the small, borderless release announcement."""
    _NEW_CHAT_UPDATE(
        data={"icon_data": icon_data, "version": version, "message": message},
        key=key,
        height=50,
    )
