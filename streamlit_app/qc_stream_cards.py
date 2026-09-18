"""Clickable Question Curriculum cards with a one-time, in-card text reveal."""

from typing import Any

import streamlit as st


_CARDS_HTML = """
<div class="qc-stream-cards" role="group"></div>
"""

_CARDS_CSS = """
.qc-stream-cards {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.55rem;
  width: 100%;
  font-family: inherit;
}
.qc-stream-cards button {
  display: block;
  box-sizing: border-box;
  width: fit-content;
  max-width: 100%;
  height: auto;
  padding: 0.78rem 1.05rem;
  border: 1px solid rgba(194, 202, 213, 0.16);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 5px 18px rgba(15, 23, 42, 0.045);
  color: #31333f;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 450;
  line-height: 1.42;
  text-align: left;
  white-space: normal;
  overflow-wrap: break-word;
  word-break: normal;
  cursor: pointer;
}
.qc-stream-cards button:hover {
  border-color: rgba(227, 50, 80, 0.22);
  background: #fffafb;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.065);
}
.qc-stream-cards button:focus-visible {
  outline: 2px solid #e33250;
  outline-offset: 2px;
}
"""

_CARDS_JS = """
export default function ({ data, parentElement, setTriggerValue }) {
  const root = parentElement.querySelector('.qc-stream-cards');
  const items = Array.isArray(data.items) ? data.items : [];
  root.setAttribute('aria-label', data.label || 'Questions');
  root.replaceChildren();

  let timer;
  let stopped = false;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const animate = Boolean(data.animate) && !reducedMotion;
  const totalLetters = items.reduce((total, item) => total + Array.from(item.label).length, 0);
  // Keep the full path timely even when a subject has many long questions.
  const letterDelay = Math.max(5, Math.min(24, 18000 / Math.max(totalLetters, 1)));

  function addCard(item) {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', item.label);
    button.onclick = () => {
      stopped = true;
      clearTimeout(timer);
      setTriggerValue('selected', item.id);
    };
    root.appendChild(button);
    return button;
  }

  if (!animate) {
    for (const item of items) addCard(item).textContent = item.label;
  } else {
    let itemIndex = 0;
    function nextCard() {
      if (stopped || itemIndex >= items.length) return;
      const item = items[itemIndex++];
      const letters = Array.from(item.label);
      const button = addCard(item);
      let letterIndex = 0;
      function nextLetter() {
        if (stopped) return;
        button.textContent += letters[letterIndex++];
        if (letterIndex < letters.length) {
          timer = setTimeout(nextLetter, letterDelay);
        } else {
          timer = setTimeout(nextCard, 95);
        }
      }
      if (letters.length) nextLetter();
      else timer = setTimeout(nextCard, 95);
    }
    nextCard();
  }

  return () => {
    stopped = true;
    clearTimeout(timer);
  };
}
"""

_STREAM_CARDS = st.components.v2.component(
    "qc_stream_cards",
    html=_CARDS_HTML,
    css=_CARDS_CSS,
    js=_CARDS_JS,
)


def render_stream_cards(
    items: list[dict[str, Any]], *, key: str, label: str, animate: bool
) -> str | None:
    """Return the clicked item id; animate only on its first reveal."""
    result = _STREAM_CARDS(
        data={"items": items, "label": label, "animate": animate},
        key=key,
        on_selected_change=lambda: None,
    )
    return getattr(result, "selected", None)
