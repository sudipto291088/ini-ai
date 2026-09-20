"""One-at-a-time, browser-local guidance for the New Chat landing page."""

import streamlit as st


_GUIDANCE_LINES = (
    "Begin with a topic, question, or idea.",
    "InI turns that thought into a learning path.",
    "No perfect terminology needed; curiosity is enough.",
    "Interrogate to explore questions and connections.",
    "Illustrate to see an idea more clearly.",
    "Follow one question naturally into the next.",
)


_GUIDANCE = st.components.v2.component(
    "ini_new_chat_landing_guidance_v1",
    html='<div class="ini-landing-guidance" aria-label="InI guidance"><span class="ini-landing-guidance__copy"></span></div>',
    css="""
    .ini-landing-guidance {
      box-sizing: border-box;
      width: min(calc(100% - 24px), 1120px);
      min-height: 1.4em;
      margin: 18px auto 30px;
      color: #171717;
      font: 430 23px/1.4 Aptos, "Segoe UI", system-ui, sans-serif;
      letter-spacing: .006em;
      text-align: center;
      overflow-wrap: break-word;
    }
    .ini-landing-guidance__copy { display: block; }
    @media (max-width: 720px) {
      .ini-landing-guidance {
        width: 92%;
        min-height: 3.4em;
        margin-bottom: 22px;
        font-size: clamp(15px, 4.2vw, 17px);
      }
    }
    """,
    js="""
    export default function ({ parentElement, data }) {
      const copy = parentElement.querySelector('.ini-landing-guidance__copy');
      const lines = data.lines;
      if (!copy || !Array.isArray(lines) || !lines.length) return;

      // One text node and one timer: independent CSS animation clocks could
      // show two sentences in the same line after a Streamlit rerender.
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        copy.textContent = lines[0];
        return;
      }

      let timer;
      let stopped = false;
      let lineIndex = 0;
      let charIndex = 0;
      let characters = Array.from(lines[0]);
      copy.textContent = '';

      const step = () => {
        if (stopped) return;
        if (charIndex < characters.length) {
          copy.textContent += characters[charIndex++];
          timer = window.setTimeout(step, 42);
          return;
        }
        timer = window.setTimeout(() => {
          if (stopped) return;
          lineIndex = (lineIndex + 1) % lines.length;
          characters = Array.from(lines[lineIndex]);
          charIndex = 0;
          copy.textContent = '';
          step();
        }, 2100);
      };
      step();

      return () => {
        stopped = true;
        window.clearTimeout(timer);
      };
    }
    """,
)


def render_landing_guidance() -> None:
    _GUIDANCE(key="nc_landing_guidance", data={"lines": _GUIDANCE_LINES})
