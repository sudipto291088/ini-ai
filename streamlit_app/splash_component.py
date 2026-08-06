"""Opening Mukut splash for each fresh InI.ai page load."""

from collections.abc import Callable
from typing import Optional

import streamlit as st


_SPLASH_COMPONENT = st.components.v2.component(
    "ini_opening_mukut_splash_v1",
    html='<div id="ini-opening-splash-root" aria-live="polite"></div>',
    css="""
    #ini-opening-splash-root {
      font-family: Aptos, "Segoe UI", system-ui, sans-serif;
    }
    .ini-opening-splash {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      overflow: hidden;
      background:
        radial-gradient(circle at 50% 48%, rgba(245, 27, 63, .055), transparent 25%),
        #ffffff;
      opacity: 0;
      transition: opacity 420ms ease;
    }
    .ini-opening-splash.is-visible { opacity: 1; }
    .ini-opening-splash.is-leaving { opacity: 0; }
    .ini-opening-splash__stage {
      width: min(34vw, 148px);
      min-width: 92px;
      perspective: 920px;
      transform-style: preserve-3d;
    }
    .ini-opening-splash__mukut {
      display: block;
      width: 100%;
      height: auto;
      transform-origin: 50% 50%;
      backface-visibility: visible;
      filter: drop-shadow(0 13px 22px rgba(245, 27, 63, .13));
      animation: ini-opening-mukut-turn 2.35s cubic-bezier(.34,.08,.14,1) both;
      will-change: transform, filter;
    }
    @keyframes ini-opening-mukut-turn {
      0% {
        transform: rotateY(-90deg) scale(.90);
        filter: brightness(.88) drop-shadow(0 8px 16px rgba(245, 27, 63, .08));
      }
      18% { transform: rotateY(-42deg) scale(.98); }
      52% {
        transform: rotateY(210deg) scale(1.025);
        filter: brightness(.94) drop-shadow(0 15px 25px rgba(245, 27, 63, .16));
      }
      82% { transform: rotateY(372deg) scale(1.012); }
      100% {
        transform: rotateY(360deg) scale(1);
        filter: brightness(1) drop-shadow(0 10px 20px rgba(245, 27, 63, .11));
      }
    }
    @media (max-width: 640px) {
      .ini-opening-splash__stage { width: min(35vw, 122px); }
    }
    @media (prefers-reduced-motion: reduce) {
      .ini-opening-splash__mukut {
        animation: ini-opening-mukut-arrive 900ms ease-out both;
      }
      @keyframes ini-opening-mukut-arrive {
        from { opacity: 0; transform: scale(.96); }
        to { opacity: 1; transform: scale(1); }
      }
    }
    """,
    js="""
    export default function (component) {
      const { parentElement, data, setTriggerValue } = component;
      const root = parentElement.querySelector('#ini-opening-splash-root');
      if (!root) return;

      const loadId = String(Math.round(performance.timeOrigin));
      const completedKey = 'ini_opening_splash_completed_load';
      const startedKey = `ini_opening_splash_started_${loadId}`;
      const audienceKey = `ini_opening_splash_audience_${loadId}`;

      if (sessionStorage.getItem(completedKey) === loadId) {
        root.innerHTML = '';
        return;
      }

      const host = root.getRootNode().host;
      const originalHostStyle = host.getAttribute('style');
      let hostRestored = false;
      const syncHostToViewport = () => {
        const viewport = window.visualViewport;
        Object.assign(host.style, {
          position: 'fixed',
          inset: 'auto',
          left: `${viewport?.offsetLeft || 0}px`,
          top: `${viewport?.offsetTop || 0}px`,
          width: `${viewport?.width || window.innerWidth}px`,
          height: `${viewport?.height || window.innerHeight}px`,
          zIndex: '2147483600',
          pointerEvents: 'auto',
        });
      };
      const restoreHost = () => {
        if (hostRestored) return;
        hostRestored = true;
        window.visualViewport?.removeEventListener('resize', syncHostToViewport);
        window.visualViewport?.removeEventListener('scroll', syncHostToViewport);
        if (originalHostStyle === null) host.removeAttribute('style');
        else host.setAttribute('style', originalHostStyle);
      };
      syncHostToViewport();
      window.visualViewport?.addEventListener('resize', syncHostToViewport);
      window.visualViewport?.addEventListener('scroll', syncHostToViewport);

      if (!sessionStorage.getItem(audienceKey)) {
        sessionStorage.setItem(
          audienceKey,
          localStorage.getItem('ini_fce_seen') === '1' ? 'returning' : 'first-time',
        );
      }
      const audience = sessionStorage.getItem(audienceKey) || 'returning';
      const startedAt = Number(sessionStorage.getItem(startedKey)) || Date.now();
      sessionStorage.setItem(startedKey, String(startedAt));

      root.innerHTML = `<section class="ini-opening-splash" role="status" aria-label="InI.ai is opening"><div class="ini-opening-splash__stage"><img class="ini-opening-splash__mukut" src="${data.icon_data}" alt="Mukut"></div></section>`;
      const overlay = root.querySelector('.ini-opening-splash');
      requestAnimationFrame(() => overlay?.classList.add('is-visible'));

      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const visibleFor = reducedMotion ? 1200 : 2850;
      const elapsed = Math.max(0, Date.now() - startedAt);
      const leaveTimer = window.setTimeout(() => {
        overlay?.classList.add('is-leaving');
      }, Math.max(0, visibleFor - elapsed));
      const finishTimer = window.setTimeout(() => {
        sessionStorage.setItem(completedKey, loadId);
        root.innerHTML = '';
        restoreHost();
        setTriggerValue('complete', audience);
      }, Math.max(0, visibleFor + 430 - elapsed));

      return () => {
        window.clearTimeout(leaveTimer);
        window.clearTimeout(finishTimer);
        restoreHost();
      };
    }
    """,
)


def render_app_splash(
    *,
    icon_data: str,
    key: str = "ini_app_splash",
    on_complete_change: Optional[Callable[[], None]] = None,
) -> Optional[str]:
    """Render the splash and return ``first-time`` or ``returning`` on completion."""
    result = _SPLASH_COMPONENT(
        key=key,
        data={"icon_data": icon_data},
        on_complete_change=on_complete_change or (lambda: None),
    )
    return getattr(result, "complete", None)
