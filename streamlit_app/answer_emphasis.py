"""Render only inline bold emphasis in HTML-backed explanatory prose."""
from html import escape
import re


def emphasis_html(text: str) -> str:
    # Escape first: model text must never become arbitrary executable HTML.
    safe = escape(str(text))
    return re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", safe)
