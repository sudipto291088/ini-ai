"""Compact animated release notice for the empty New Chat landing screen."""

from collections.abc import Callable
from typing import Optional

import streamlit as st


_NEW_CHAT_UPDATE = st.components.v2.component(
    "ini_new_chat_update_v25",
    html='<div id="ini-new-chat-update-root"></div>',
    css="""
    #ini-new-chat-update-root {
      width: min(100%, 820px);
      height: 0;
      margin: 0 auto;
      overflow: hidden;
      background: transparent;
      box-shadow: none;
      font-family: Aptos, "Segoe UI", system-ui, sans-serif;
      transition: height .42s cubic-bezier(.22, .78, .24, 1);
    }
    .ini-update-notice {
      position: relative;
      width: 100%;
      min-height: 54px;
      background: transparent;
      color: var(--st-text-color, #17211f);
    }
    .ini-update-spacer {
      display: block;
      font-size: 1px;
      line-height: 54px;
      visibility: hidden;
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
      right: 25px;
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
      display: inline-block;
      min-width: 0;
      overflow: hidden;
      color: var(--st-text-color, #17211f);
      font-size: 13px;
      font-weight: 650;
      line-height: 1.25;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ini-update-line {
      display: flex;
      min-width: 0;
      align-items: baseline;
      gap: 10px;
    }
    .ini-update-action {
      flex: 0 0 auto;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--st-primary-color, #f51b3f);
      font: 700 10px/1.2 Aptos, "Segoe UI", system-ui, sans-serif;
      cursor: pointer;
      white-space: nowrap;
    }
    .ini-update-action:hover,
    .ini-update-action:focus-visible {
      color: #d91435;
      text-decoration: underline;
      text-underline-offset: 3px;
      outline: none;
    }
    .ini-update-dismiss {
      position: absolute;
      z-index: 2;
      top: 50%;
      right: 2px;
      width: 22px;
      height: 22px;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: transparent;
      color: #7b8492;
      font: 400 19px/20px Aptos, "Segoe UI", system-ui, sans-serif;
      cursor: pointer;
      opacity: .64;
      transform: translateY(-50%);
      transition: color .16s ease, opacity .16s ease, background .16s ease;
    }
    .ini-update-dismiss:hover,
    .ini-update-dismiss:focus-visible {
      background: rgba(245, 27, 63, .055);
      color: var(--st-primary-color, #f51b3f);
      opacity: 1;
      outline: none;
    }
    .ini-update-notice.is-dismissing {
      opacity: 0;
      transform: translateY(-3px);
      transition: opacity .16s ease, transform .16s ease;
    }
    .ini-update-notice.is-hidden {
      opacity: 0;
      pointer-events: none;
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
      #ini-new-chat-update-root { width: calc(100% - 24px); }
      .ini-update-copy { left: 34px; right: 24px; }
      .ini-update-message {
        overflow: visible;
        font-size: 12px;
        line-height: 1.25;
        text-overflow: clip;
        white-space: normal;
      }
      .ini-update-line { gap: 7px; }
      .ini-update-action { font-size: 9px; }
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
      const { data, parentElement, setTriggerValue } = component;
      const root = parentElement.querySelector('#ini-new-chat-update-root');
      if (!root) return;

      const version = String(data.version || 'latest');
      const visitor = String(data.visitor_id || 'anonymous');
      const seenKey = `ini-new-chat-update:v3:${version}`;
      const dismissedKey = `ini-new-chat-update:dismissed:${version}:${visitor}`;
      const forceOpen = Boolean(data.force_open);
      const wasDismissed = localStorage.getItem(dismissedKey) === '1';
      const shouldAnimate = !forceOpen && sessionStorage.getItem(seenKey) !== '1';

      root.innerHTML = `
        <section class="ini-update-notice is-hidden"
          aria-label="New in ${data.version}: ${data.message}">
          <span class="ini-update-spacer" aria-hidden="true">&nbsp;</span>
          <img class="ini-update-mukut" src="${data.icon_data}" alt="Mukut">
          <span class="ini-update-copy">
            <span class="ini-update-kicker">New in ${data.version}</span>
            <span class="ini-update-line">
              <span class="ini-update-message">${data.message}</span>
              <button class="ini-update-action" type="button">Explore now →</button>
            </span>
          </span>
          <button class="ini-update-dismiss" type="button"
            aria-label="Dismiss this update" title="Dismiss">×</button>
        </section>`;

      const notice = root.querySelector('.ini-update-notice');
      const action = root.querySelector('.ini-update-action');
      const dismiss = root.querySelector('.ini-update-dismiss');
      const setFlowHeight = (height, animate) => {
        root.style.transition = animate
          ? 'height .42s cubic-bezier(.22, .78, .24, 1)'
          : 'none';
        root.style.height = `${height}px`;
      };
      const revealNotice = (animate) => {
        notice?.classList.remove('is-hidden', 'is-dismissing');
        notice?.classList.add(animate ? 'is-animated' : 'is-settled');
        if (animate) {
          setFlowHeight(0, false);
          window.requestAnimationFrame(() => {
            window.requestAnimationFrame(() => setFlowHeight(54, true));
          });
          sessionStorage.setItem(seenKey, '1');
          return;
        }
        setFlowHeight(54, false);
      };
      const exploreSubject = () => setTriggerValue('action', 'explore-subject');
      let splashPollTimer = null;
      let revealTimer = null;
      let dismissTimer = null;
      const dismissUpdate = () => {
        localStorage.setItem(dismissedKey, '1');
        notice?.classList.add('is-dismissing');
        setFlowHeight(0, true);
        dismissTimer = window.setTimeout(() => {
          if (forceOpen) setTriggerValue('action', 'dismiss');
          else root.innerHTML = '';
        }, 440);
      };
      action?.addEventListener('click', exploreSubject);
      dismiss?.addEventListener('click', dismissUpdate);

      if (wasDismissed && !forceOpen) {
        root.innerHTML = '';
        setFlowHeight(0, false);
      } else if (shouldAnimate) {
        setFlowHeight(0, false);
        const waitForNewChat = () => {
          if (sessionStorage.getItem('ini_opening_splash_seen_session') !== '1') {
            splashPollTimer = window.setTimeout(waitForNewChat, 100);
            return;
          }
          // The opening splash consumes roughly the first second. Starting the
          // reveal 2.4s later keeps the total arrival inside the intended 3–4s
          // window without coinciding with the guidance sentence pause.
          revealTimer = window.setTimeout(() => revealNotice(true), 2400);
        };
        waitForNewChat();
      } else {
        revealNotice(false);
      }

      return () => {
        window.clearTimeout(splashPollTimer);
        window.clearTimeout(revealTimer);
        window.clearTimeout(dismissTimer);
        action?.removeEventListener('click', exploreSubject);
        dismiss?.removeEventListener('click', dismissUpdate);
      };
    }
    """,
)


def render_new_chat_update(
    *,
    icon_data: str,
    version: str = "v0.1.7",
    message: str = "Learn an entire subject through questions",
    visitor_id: str = "anonymous",
    force_open: bool = False,
    key: Optional[str] = "ini-new-chat-update-v017",
    on_action_change: Optional[Callable[[], None]] = None,
) -> Optional[str]:
    """Render the small, borderless release announcement."""
    result = _NEW_CHAT_UPDATE(
        data={
            "icon_data": icon_data,
            "version": version,
            "message": message,
            "visitor_id": visitor_id,
            "force_open": force_open,
        },
        key=key,
        on_action_change=on_action_change or (lambda: None),
    )
    return getattr(result, "action", None)
