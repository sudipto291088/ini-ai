"""Browser-local clock: no Python callbacks or periodic application reruns."""

import streamlit as st


CLOCK_CSS = """
* { box-sizing: border-box; }
.clock_tile {
  width:100%; border:1px solid rgba(148,163,184,.20); border-radius:12px;
  background:#fff; color:#111827; padding:14px 12px 11px; margin:6px 0 12px;
  font-family:var(--st-font, sans-serif);
  box-shadow:0 10px 26px rgba(15,23,42,.055),0 2px 7px rgba(15,23,42,.035);
}
.clock_center {display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:9px;}
.clock_date_group,.clock_time_group {display:flex; align-items:center; gap:7px; min-width:0;}
.clock_time_group {padding-left:10px; border-left:1px solid rgba(148,163,184,.30);}
.clock_calendar_icon,.clock_face_icon {width:25px; height:25px; color:#111827; flex:0 0 auto;}
.clock_date_stack {display:flex; flex-direction:column; min-width:0; line-height:1.05;}
.clock_day {font-size:9px; font-weight:520; color:#667085; white-space:nowrap;}
.clock_date {font-size:10px; font-weight:550; color:#344054; white-space:nowrap; letter-spacing:-.08px;}
.clock_time {font-size:17px; font-weight:560; line-height:1; letter-spacing:.5px; font-variant-numeric:tabular-nums;}
.clock_ampm {font-size:9px; font-weight:520; color:#667085; margin-top:5px;}
.badge {display:flex; align-items:center; gap:10px; width:100%; margin-top:12px;
  padding:10px 2px 1px; border-top:1px solid rgba(148,163,184,.24);
  font-size:11px; font-weight:500; color:#475467;}
.badge::before {content:""; width:7px; height:7px; border-radius:50%; background:#f51b3f;
  box-shadow:0 0 0 3px rgba(245,27,63,.08);}
"""

CLOCK_JS = """
export default function ({parentElement, data}) {
  const root = parentElement.querySelector('[data-clock-root]');
  root.innerHTML = data.html;
  const text = (selector, value) => {
    const element = root.querySelector(selector);
    if (element.textContent !== value) element.textContent = value;
  };
  const hands = root.querySelectorAll('.clock_face_icon path');
  const update = () => {
    // Read the actual device time on every tick; never accumulate timer drift.
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    const second = now.getSeconds();
    text('.clock_time', `${hour % 12 || 12}:${String(minute).padStart(2, '0')}`);
    text('.clock_ampm', hour >= 12 ? 'PM' : 'AM');
    text('.clock_day', now.toLocaleDateString('en-US', {weekday:'short'}));
    text('.clock_date', now.toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'}));
    hands[0].setAttribute('transform', `rotate(${(hour % 12) * 30 + minute * .5 + second / 120} 16 16)`);
    hands[1].setAttribute('transform', `rotate(${minute * 6 + second * .1} 16 16)`);
  };
  update();
  const timer = window.setInterval(update, 1000);
  const onVisible = () => { if (!document.hidden) update(); };
  document.addEventListener('visibilitychange', onVisible);
  return () => {
    window.clearInterval(timer);
    document.removeEventListener('visibilitychange', onVisible);
  };
}
"""

_CLOCK = st.components.v2.component(
    "ini_sidebar_clock",
    html='<div data-clock-root></div>',
    css=CLOCK_CSS,
    js=CLOCK_JS,
)


def render_sidebar_clock(html: str) -> None:
    _CLOCK(data={"html": html}, key="ini_sidebar_clock", width="stretch", height="content")
