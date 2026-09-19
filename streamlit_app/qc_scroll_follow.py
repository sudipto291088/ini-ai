"""Keep the growing Question Curriculum response visible while it streams."""

import streamlit as st


_FOLLOW_JS = """
export default function ({ data }) {
  const card = document.querySelector(data.selector);
  if (!card) return;

  const win = document.defaultView;
  const scrollables = [];
  for (let element = card.parentElement; element; element = element.parentElement) {
    const overflow = win.getComputedStyle(element).overflowY;
    if (overflow === 'auto' || overflow === 'scroll' || overflow === 'overlay') {
      scrollables.push(element);
    }
  }
  if (document.scrollingElement && !scrollables.includes(document.scrollingElement)) {
    scrollables.push(document.scrollingElement);
  }

  let following = true;
  let frame = 0;
  let ignoreScrollUntil = 0;
  let userScrollUntil = 0;
  let lastDistance = 0;
  let touchY = null;

  function activeScrollers() {
    const nested = scrollables.filter(element =>
      element !== document.scrollingElement &&
      element.scrollHeight > element.clientHeight + 8
    );
    if (nested.length) return nested;
    const page = document.scrollingElement;
    return page && page.scrollHeight > page.clientHeight + 8 ? [page] : [];
  }

  function distanceFromEnd() {
    const active = activeScrollers();
    if (!active.length) return 0;
    return Math.max(...active.map(element =>
      element.scrollHeight - element.scrollTop - element.clientHeight
    ));
  }

  function follow() {
    frame = 0;
    if (!following || !card.isConnected) return;
    const reserve = Math.min(120, Math.max(72, win.innerHeight * 0.12));
    for (const element of activeScrollers()) {
      const viewportBottom = element === document.scrollingElement
        ? win.innerHeight
        : element.getBoundingClientRect().bottom;
      const delta = card.getBoundingClientRect().bottom - viewportBottom + reserve;
      if (delta > 4) {
        ignoreScrollUntil = win.performance.now() + 140;
        element.scrollTop += delta;
      }
    }
    lastDistance = distanceFromEnd();
  }

  function schedule() {
    if (!frame && following) frame = win.requestAnimationFrame(follow);
  }

  function onScroll() {
    const now = win.performance.now();
    if (now < ignoreScrollUntil || now > userScrollUntil) return;
    const distance = distanceFromEnd();
    if (distance > lastDistance + 5) following = false;
    if (distance < 32 && distance < lastDistance) {
      following = true;
      schedule();
    }
    lastDistance = distance;
  }

  function onWheel(event) {
    userScrollUntil = win.performance.now() + 900;
    if (event.deltaY < 0) following = false;
  }

  function onTouchStart(event) {
    touchY = event.touches[0]?.clientY ?? null;
  }

  function onTouchMove(event) {
    userScrollUntil = win.performance.now() + 900;
    const nextY = event.touches[0]?.clientY;
    if (touchY !== null && nextY !== undefined && nextY > touchY + 3) {
      following = false;
    }
    touchY = nextY ?? null;
  }

  function onKeyDown(event) {
    if (['ArrowUp', 'PageUp', 'Home', 'ArrowDown', 'PageDown', 'End'].includes(event.key)) {
      userScrollUntil = win.performance.now() + 900;
    }
    if (['ArrowUp', 'PageUp', 'Home'].includes(event.key)) following = false;
  }

  function onPointerDown(event) {
    if (scrollables.some(element => element === event.target)) {
      userScrollUntil = win.performance.now() + 1200;
    }
  }

  const mutation = new MutationObserver(schedule);
  mutation.observe(card, { childList: true, subtree: true, characterData: true });
  const resize = new ResizeObserver(schedule);
  resize.observe(card);
  for (const element of scrollables) element.addEventListener('scroll', onScroll, { passive: true });
  document.addEventListener('scroll', onScroll, { passive: true, capture: true });
  document.addEventListener('wheel', onWheel, { passive: true, capture: true });
  document.addEventListener('touchstart', onTouchStart, { passive: true, capture: true });
  document.addEventListener('touchmove', onTouchMove, { passive: true, capture: true });
  document.addEventListener('keydown', onKeyDown, true);
  document.addEventListener('pointerdown', onPointerDown, true);
  schedule();

  return () => {
    mutation.disconnect();
    resize.disconnect();
    if (frame) win.cancelAnimationFrame(frame);
    for (const element of scrollables) element.removeEventListener('scroll', onScroll);
    document.removeEventListener('scroll', onScroll, true);
    document.removeEventListener('wheel', onWheel, true);
    document.removeEventListener('touchstart', onTouchStart, true);
    document.removeEventListener('touchmove', onTouchMove, true);
    document.removeEventListener('keydown', onKeyDown, true);
    document.removeEventListener('pointerdown', onPointerDown, true);
  };
}
"""


_FOLLOW_COMPONENT = st.components.v2.component("qc_scroll_follow", js=_FOLLOW_JS)


def follow_qc_stream() -> None:
    """Mount a zero-height follower before the first streamed response element."""
    _FOLLOW_COMPONENT(
        data={"selector": ".st-key-qc_primary_response"},
        key="qc_stream_follow",
        height=0,
    )
