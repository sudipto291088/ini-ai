"""First Conversation Experience component for InI.ai."""

from collections.abc import Callable
from typing import Any, Dict, List, Optional

import streamlit as st


_FCE_COMPONENT = st.components.v2.component(
    "ini_first_conversation_experience",
    html='<div id="ini-fce-root" aria-live="polite"></div>',
    css="""
    #ini-fce-root { font-family: Aptos, "Segoe UI", system-ui, sans-serif; }
    .ini-fce-overlay { position: absolute; inset: 0; width: 100%; height: 100%; display: grid; place-items: center; padding: 28px; box-sizing: border-box; background: rgba(16, 24, 40, .34); backdrop-filter: blur(3px); z-index: 1; opacity: 0; transition: opacity 420ms ease; pointer-events: none; }
    .ini-fce-overlay.is-visible { opacity: 1; pointer-events: auto; }
    .ini-fce-panel { width: min(60vw, 810px); max-height: min(82vh, 790px); box-sizing: border-box; display: flex; flex-direction: column; overflow: hidden; border: 1px solid rgba(226,232,240,.92); border-radius: 22px; background: rgba(255,255,255,.985); color: #1b2432; box-shadow: 0 28px 72px rgba(15,23,42,.20); }
    .ini-fce-header { display: flex; align-items: center; justify-content: space-between; flex: 0 0 auto; padding: 22px 30px; }
    .ini-fce-brand { display: flex; align-items: center; gap: 9px; color: #182231; font-size: 16px; font-weight: 700; }
    .ini-fce-brand img { display: block; width: 23px; height: 23px; object-fit: contain; }
    .ini-fce-close { width: 34px; height: 34px; border: 1px solid #e4e7ec; border-radius: 10px; background: #fff; color: #667085; font: 400 22px/1 Aptos, "Segoe UI", sans-serif; cursor: pointer; }
    .ini-fce-close:hover, .ini-fce-close:focus-visible { border-color: #cbd2dc; color: #17211f; outline: 2px solid rgba(245,27,63,.20); outline-offset: 2px; }
    .ini-fce-body { flex: 1 1 auto; overflow: auto; padding: 0 54px; scroll-behavior: smooth; }
    .ini-fce-transcript { min-height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 42px 0; box-sizing: border-box; }
    .ini-fce-message { margin: 0; color: #4b5565; font-size: clamp(21px, 2vw, 29px); font-weight: 400; line-height: 1.46; letter-spacing: -.017em; white-space: pre-line; }
    .ini-fce-message.identity, .ini-fce-message.philosophy, .ini-fce-message.journey, .ini-fce-message.final { color: #17211f; font-weight: 600; }
    .ini-fce-message.philosophy { color: #202b3a; }
    .ini-fce-caret { display: inline-block; width: 2px; height: 1.03em; margin-left: 5px; vertical-align: -.12em; background: #f51b3f; animation: ini-fce-cursor 820ms steps(1, end) infinite; }
    .ini-fce-quote { margin: 0; padding-left: 22px; border-left: 2px solid #f51b3f; }
    .ini-fce-quote-text { color: #2d3747; font-size: clamp(20px, 1.8vw, 26px); font-style: italic; line-height: 1.48; }
    .ini-fce-quote-author { margin-top: 14px; color: #546071; font-size: 14px; font-weight: 700; }
    .ini-fce-quote-note { margin-top: 5px; color: #87909e; font-size: 12px; }
    .ini-fce-topics { display: flex; flex-wrap: wrap; gap: 9px; margin: 22px 0 0; }
    .ini-fce-topic { padding: 7px 10px; border: 1px solid #e7eaf0; border-radius: 999px; background: #f7f8fa; color: #596373; font-size: 13px; line-height: 1.2; }
    .ini-fce-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex: 0 0 auto; padding: 18px 30px 22px; background: #fff; }
    .ini-fce-controls { display: flex; flex-wrap: wrap; gap: 8px; }
    .ini-fce-button { min-height: 38px; padding: 9px 12px; border: 1px solid #e1e5eb; border-radius: 11px; background: #fff; color: #4b5563; font: 600 13px/1.2 Aptos, "Segoe UI", sans-serif; cursor: pointer; }
    .ini-fce-button:hover, .ini-fce-button:focus-visible { border-color: #cbd2dc; background: #f8f9fb; outline: 2px solid rgba(245,27,63,.18); outline-offset: 2px; }
    .ini-fce-button.primary { border-color: #f51b3f; background: #f51b3f; color: #fff; }
    .ini-fce-button.primary:hover, .ini-fce-button.primary:focus-visible { border-color: #d91435; background: #d91435; }
    .ini-fce-final-actions { display: grid; grid-template-columns: .8fr 1.15fr 1.15fr; gap: 10px; margin-top: 4px; }
    .ini-fce-final-actions .ini-fce-button { min-height: 45px; }
    @keyframes ini-fce-cursor { 0%, 45% { opacity: 1; } 46%, 100% { opacity: 0; } }
    @media (max-width: 900px) { .ini-fce-panel { width: min(82vw, 720px); } .ini-fce-body { padding-inline: 34px; } }
    .ini-fce-overlay.is-mobile { padding: 10px; }
    .ini-fce-overlay.is-mobile .ini-fce-panel { width: calc(100% - 20px); max-width: none; max-height: calc(100% - 20px); border-radius: 18px; }
    .ini-fce-overlay.is-mobile .ini-fce-header { padding: 15px 17px; }
    .ini-fce-overlay.is-mobile .ini-fce-body { min-width: 0; min-height: 0; padding-inline: 20px; }
    .ini-fce-overlay.is-mobile .ini-fce-transcript { min-width: 0; min-height: 0; padding-block: 22px; }
    .ini-fce-overlay.is-mobile .ini-fce-message { max-width: 100%; overflow-wrap: anywhere; word-break: normal; font-size: clamp(18px, 5.2vw, 21px); }
    .ini-fce-overlay.is-mobile .ini-fce-footer { align-items: stretch; flex-direction: column-reverse; padding: 12px 17px 15px; }
    .ini-fce-overlay.is-mobile .ini-fce-controls { width: 100%; }
    .ini-fce-overlay.is-mobile .ini-fce-button { flex: 1 1 auto; }
    .ini-fce-overlay.is-mobile .ini-fce-final-actions { grid-template-columns: 1fr; }
    @media (max-width: 640px) { .ini-fce-overlay { padding: 10px; } .ini-fce-panel { width: calc(100% - 20px); max-width: none; max-height: calc(100% - 20px); border-radius: 18px; } .ini-fce-header { padding: 15px 17px; } .ini-fce-body { min-width: 0; min-height: 0; padding-inline: 20px; } .ini-fce-transcript { min-width: 0; min-height: 0; padding-block: 22px; } .ini-fce-message { max-width: 100%; overflow-wrap: anywhere; font-size: clamp(18px, 5.2vw, 21px); } .ini-fce-footer { align-items: stretch; flex-direction: column-reverse; padding: 12px 17px 15px; } .ini-fce-controls { width: 100%; } .ini-fce-button { flex: 1 1 auto; } .ini-fce-final-actions { grid-template-columns: 1fr; } }
    @media (prefers-reduced-motion: reduce) { .ini-fce-overlay { transition: none; } .ini-fce-body { scroll-behavior: auto; } .ini-fce-caret { animation: none; } }
    """,
    js="""
    export default function (component) {
      const { parentElement, data, setStateValue, setTriggerValue } = component;
      const root = parentElement.querySelector('#ini-fce-root');
      if (!root) return;

      if (localStorage.getItem('ini_fce_seen') === '1' && !data.force_open) {
        root.innerHTML = '';
        setTriggerValue('action', 'seen');
        return;
      }

      const host = root.getRootNode().host;
      const originalHostStyle = host.getAttribute('style');
      // Streamlit places this component inside the main-content region.
      // The overlay itself expands left by the visible sidebar width below.
      const sidebar = document.querySelector('[data-testid="stSidebar"]');
      const hasCoarsePointer = window.matchMedia('(pointer: coarse)').matches;
      const physicalShortSide = Math.min(window.screen?.width || Infinity, window.screen?.height || Infinity);
      const isMobileViewport = window.matchMedia('(max-width: 720px)').matches
        || (hasCoarsePointer && physicalShortSide <= 720);
      const sidebarWidth = !isMobileViewport && sidebar && sidebar.offsetParent !== null
        ? sidebar.getBoundingClientRect().width
        : 0;
      const syncHostToViewport = () => {
        const viewport = window.visualViewport;
        if (isMobileViewport && viewport) {
          Object.assign(host.style, {
            position: 'fixed',
            inset: 'auto',
            left: `${viewport.offsetLeft}px`,
            top: `${viewport.offsetTop}px`,
            width: `${viewport.width}px`,
            height: `${viewport.height}px`,
            zIndex: '2147483000',
            pointerEvents: 'auto',
          });
          return;
        }
        Object.assign(host.style, {
          position: 'fixed',
          inset: '0',
          width: 'auto',
          height: 'auto',
          zIndex: '2147483000',
          pointerEvents: 'auto',
        });
      };
      syncHostToViewport();
      window.visualViewport?.addEventListener('resize', syncHostToViewport);
      window.visualViewport?.addEventListener('scroll', syncHostToViewport);

      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const flowStorageKey = 'ini_fce_active_flow';
      let savedFlow = null;
      try { savedFlow = JSON.parse(sessionStorage.getItem(flowStorageKey) || 'null'); } catch (error) { savedFlow = null; }
      const state = savedFlow || { view: 'intro', startedAt: Date.now() + 2500, visibleAt: Date.now() + 2000, timer: null };
      if (!state.visibleAt) state.visibleAt = Date.now() + 2000;
      state.hold = false;
      const saveFlow = () => sessionStorage.setItem(flowStorageKey, JSON.stringify({ view: state.view, startedAt: state.startedAt, visibleAt: state.visibleAt }));
      saveFlow();
      const escapeHtml = (value) => String(value || '').replace(/[&<>'"]/g, (character) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[character]));
      const textMarkup = (message, text, isTyping) => `<p class="ini-fce-message ${escapeHtml(message.emphasis || '')}">${escapeHtml(text)}${isTyping ? '<span class="ini-fce-caret" aria-hidden="true"></span>' : ''}</p>`;
      const quoteMarkup = () => `<section class="ini-fce-quote"><div class="ini-fce-quote-text">“${escapeHtml(data.quote.quote)}”</div><div class="ini-fce-quote-author">— ${escapeHtml(data.quote.author)}</div>${data.quote.attribution_note ? `<div class="ini-fce-quote-note">${escapeHtml(data.quote.attribution_note)}</div>` : ''}</section>`;
      const topicsMarkup = () => `<div class="ini-fce-topics">${(data.topics || []).map((topic) => `<span class="ini-fce-topic">${escapeHtml(topic)}</span>`).join('')}</div>`;
      const finalMarkup = () => `<p class="ini-fce-message final">${escapeHtml(data.messages[data.messages.length - 1].text)}</p><div class="ini-fce-final-actions"><button class="ini-fce-button" type="button" data-action="replay">Replay</button><button class="ini-fce-button" type="button" data-action="go-introduction">Take Me to Introduction</button><button class="ini-fce-button primary" type="button" data-action="go-chat">Start a New Chat</button></div>`;

      const currentProgress = () => {
        let elapsed = Date.now() - state.startedAt;
        for (let index = 0; index < data.messages.length; index += 1) {
          const message = data.messages[index];
          const typingTime = message.text.length * 27;
          if (elapsed <= typingTime + 3000) {
            return { index, characters: Math.max(0, Math.min(message.text.length, Math.floor(elapsed / 27))), complete: false };
          }
          elapsed -= typingTime + 3000;
        }
        const lastIndex = data.messages.length - 1;
        return { index: lastIndex, characters: data.messages[lastIndex].text.length, complete: true };
      };

      const elapsedBeforeMessage = (targetIndex) => data.messages
        .slice(0, targetIndex)
        .reduce((elapsed, message) => elapsed + (message.text.length * 27) + 3000, 0);

      const finish = (action) => {
        root.innerHTML = '';
        sessionStorage.removeItem(flowStorageKey);
        setStateValue('action', action);
        setTriggerValue('action', action);
      };

      const transcriptMarkup = () => {
        const progress = currentProgress();
        const message = data.messages[progress.index];
        let block = textMarkup(message, message.text.slice(0, progress.characters), progress.characters < message.text.length);
        if (progress.characters >= message.text.length) {
          if (message.topics) block += topicsMarkup();
          if (message.quote) block += quoteMarkup();
        }
        return block;
      };

      const render = () => {
        clearTimeout(state.timer);
        if (state.hold) {
          state.timer = setTimeout(render, 50);
          return;
        }
        const progress = state.view === 'intro' ? currentProgress() : null;
        if (progress?.complete) { state.view = 'end'; saveFlow(); render(); return; }
        const all = state.view === 'all';
        const end = state.view === 'end';
        const content = end ? finalMarkup() : all
          ? `${data.messages.slice(0, -1).map((message) => `${textMarkup(message, message.text, false)}${message.topics ? topicsMarkup() : ''}${message.quote ? quoteMarkup() : ''}`).join('')}${finalMarkup()}`
          : transcriptMarkup();
        const canGoBack = progress && progress.index > 0 && progress.index < data.messages.length - 1;
        const footer = end ? '' : `<footer class="ini-fce-footer">${all ? '<div></div>' : `<div class="ini-fce-controls">${canGoBack ? '<button class="ini-fce-button" type="button" data-action="back">Previous</button>' : ''}<button class="ini-fce-button" type="button" data-action="skip">Skip Introduction</button><button class="ini-fce-button" type="button" data-action="show-all">Show Everything</button></div>`}<button class="ini-fce-button" type="button" data-action="skip-end">Skip to End</button></footer>`;
        if (Date.now() >= state.visibleAt) localStorage.setItem('ini_fce_seen', '1');
        const desktopExpansion = isMobileViewport ? '' : `left:-${sidebarWidth}px;width:calc(100% + ${sidebarWidth}px)`;
        const mobileClass = isMobileViewport ? ' is-mobile' : '';
        root.innerHTML = `<section class="ini-fce-overlay${mobileClass}${Date.now() >= state.visibleAt ? ' is-visible' : ''}" role="dialog" aria-modal="true" aria-label="Welcome to InI.ai" style="${desktopExpansion}"><div class="ini-fce-panel"><header class="ini-fce-header"><div class="ini-fce-brand"><img src="${escapeHtml(data.icon_data)}" alt="InI.ai icon"> <span>InI.ai</span></div><button class="ini-fce-close" type="button" aria-label="Close First Conversation Experience" data-action="close">×</button></header><main class="ini-fce-body"><div class="ini-fce-transcript">${content}</div></main>${footer}</div></section>`;
        root.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', (event) => {
          event.stopPropagation();
          const action = button.dataset.action;
          if (action === 'show-all') { state.view = 'all'; saveFlow(); render(); return; }
          if (action === 'skip-end') { state.view = 'end'; saveFlow(); render(); return; }
          if (action === 'replay') { state.view = 'intro'; state.startedAt = Date.now() + 500; saveFlow(); render(); return; }
          if (action === 'back') {
            const progress = currentProgress();
            state.startedAt = Date.now() - elapsedBeforeMessage(Math.max(0, progress.index - 1)) + 500;
            saveFlow();
            render();
            return;
          }
          if (action) finish(action);
        }));
        const body = root.querySelector('.ini-fce-body');
        if (!all && !end) {
          body.scrollTop = body.scrollHeight;
          state.timer = setTimeout(render, 35);
        }
      };

      const handleAction = (event) => {
        const button = event.target.closest?.('[data-action]');
        if (!button || !root.contains(button)) return;
        const action = button.dataset.action;
        if (action === 'show-all') { state.view = 'all'; saveFlow(); render(); return; }
        if (action === 'skip-end') { state.view = 'end'; saveFlow(); render(); return; }
        if (action === 'replay') { state.view = 'intro'; state.startedAt = Date.now() + 500; saveFlow(); render(); return; }
        if (action === 'back') {
          const progress = currentProgress();
          state.startedAt = Date.now() - elapsedBeforeMessage(Math.max(0, progress.index - 1)) + 500;
          saveFlow();
          render();
          return;
        }
        if (action) finish(action);
      };

      const onKeyDown = (event) => { if (event.key === 'Escape') finish('close'); };
      const holdControls = () => { state.hold = true; clearTimeout(state.timer); };
      const releaseControls = () => { state.hold = false; };
      root.addEventListener('click', handleAction);
      root.addEventListener('pointerdown', holdControls, true);
      root.addEventListener('pointerup', releaseControls, true);
      document.addEventListener('keydown', onKeyDown);
      if (reducedMotion) state.view = 'all';
      render();
      return () => {
        clearTimeout(state.timer);
        root.removeEventListener('click', handleAction);
        root.removeEventListener('pointerdown', holdControls, true);
        root.removeEventListener('pointerup', releaseControls, true);
        document.removeEventListener('keydown', onKeyDown);
        window.visualViewport?.removeEventListener('resize', syncHostToViewport);
        window.visualViewport?.removeEventListener('scroll', syncHostToViewport);
        if (originalHostStyle === null) host.removeAttribute('style');
        else host.setAttribute('style', originalHostStyle);
      };
    }
    """,
)


def render_fce(
    *,
    messages: List[Dict[str, Any]],
    topics: List[str],
    quote: Dict[str, Optional[str]],
    icon_data: str,
    force_open: bool = False,
    key: str = "ini_fce",
    on_action_change: Optional[Callable[[], None]] = None,
) -> Optional[str]:
    """Render the isolated FCE and return a browser action when one occurs."""
    result = _FCE_COMPONENT(
        key=key,
        data={
            "messages": messages,
            "topics": topics,
            "quote": quote,
            "icon_data": icon_data,
            "force_open": force_open,
        },
        on_action_change=on_action_change or (lambda: None),
    )
    return getattr(result, "action", None)
