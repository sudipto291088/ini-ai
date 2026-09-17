"""Interactive, scalable viewer for the Question Curriculum subject map."""

import streamlit as st


_MAP_HTML = """
<div class="qc-map-viewer">
  <div class="qc-map-toolbar" role="toolbar" aria-label="Subject map view controls">
    <button type="button" data-action="zoom-in" aria-label="Zoom in" title="Zoom in">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.7" cy="10.7" r="6.4"/><path d="m15.4 15.4 5.1 5.1M10.7 7.8v5.8M7.8 10.7h5.8"/></svg>
    </button>
    <button type="button" data-action="zoom-out" aria-label="Zoom out" title="Zoom out">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.7" cy="10.7" r="6.4"/><path d="m15.4 15.4 5.1 5.1M7.8 10.7h5.8"/></svg>
    </button>
    <button type="button" data-action="reset" aria-label="Reset zoom" title="Reset zoom">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11a8 8 0 1 1 2.3 6M4 5v6h6"/><circle cx="12" cy="11" r="2.4"/></svg>
    </button>
    <span class="qc-map-zoom" aria-live="polite">100%</span>
    <button type="button" data-action="expand" aria-label="Expand map" title="Expand map">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg>
    </button>
  </div>
  <div class="qc-map-viewport" aria-label="Zoomable subject map">
    <img alt="Subject map" draggable="false" />
  </div>
</div>
"""

_MAP_CSS = """
.qc-map-viewer {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 14px;
  background: #fff;
  font-family: Arial, sans-serif;
}
.qc-map-viewport {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  touch-action: auto;
  cursor: default;
}
.qc-map-viewport.is-zoomed { cursor: grab; touch-action: none; }
.qc-map-viewport.is-dragging { cursor: grabbing; }
.qc-map-viewport img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transform-origin: center center;
  user-select: none;
  -webkit-user-drag: none;
  will-change: transform;
}
.qc-map-toolbar {
  position: absolute;
  z-index: 2;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 5px;
  border: 1px solid rgba(194, 202, 213, .34);
  border-radius: 13px;
  background: rgba(255, 255, 255, .94);
  box-shadow: 0 6px 20px rgba(15, 23, 42, .08);
}
.qc-map-toolbar button {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 5px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #273240;
  cursor: pointer;
}
.qc-map-toolbar button:hover:not(:disabled),
.qc-map-toolbar button:focus-visible {
  outline: none;
  background: #fff0f2;
  color: #d92d4c;
}
.qc-map-toolbar button:disabled { opacity: .35; cursor: default; }
.qc-map-toolbar svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.qc-map-zoom {
  min-width: 39px;
  color: #65717d;
  font-size: 11px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.qc-map-viewer:fullscreen {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100dvh;
  border-radius: 0;
  background: #fff;
}
.qc-map-viewer:fullscreen .qc-map-viewport {
  flex: 1;
  min-height: 0;
  aspect-ratio: auto;
}
.qc-map-viewer:fullscreen .qc-map-toolbar { top: 18px; right: 18px; }
@media (max-width: 600px) {
  .qc-map-toolbar { top: 6px; right: 6px; gap: 0; padding: 3px; }
  .qc-map-toolbar button { width: 30px; height: 30px; }
}
"""

_MAP_JS = """
export default function ({ data, parentElement }) {
  const viewer = parentElement.querySelector('.qc-map-viewer');
  const viewport = viewer.querySelector('.qc-map-viewport');
  const image = viewport.querySelector('img');
  const zoomIn = viewer.querySelector('[data-action="zoom-in"]');
  const zoomOut = viewer.querySelector('[data-action="zoom-out"]');
  const reset = viewer.querySelector('[data-action="reset"]');
  const expand = viewer.querySelector('[data-action="expand"]');
  const zoomLabel = viewer.querySelector('.qc-map-zoom');
  image.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(data.svg);
  image.alt = data.label || 'Subject map';

  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let drag = null;
  const minScale = 1;
  const maxScale = 6;

  function clampOffset() {
    const base = Math.min(viewport.clientWidth, viewport.clientHeight);
    const maxX = Math.max(0, (base * scale - viewport.clientWidth) / 2);
    const maxY = Math.max(0, (base * scale - viewport.clientHeight) / 2);
    offsetX = Math.max(-maxX, Math.min(maxX, offsetX));
    offsetY = Math.max(-maxY, Math.min(maxY, offsetY));
  }

  function render() {
    clampOffset();
    image.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
    zoomLabel.textContent = `${Math.round(scale * 100)}%`;
    zoomOut.disabled = scale <= minScale;
    reset.disabled = scale <= minScale;
    zoomIn.disabled = scale >= maxScale;
    viewport.classList.toggle('is-zoomed', scale > minScale);
  }

  function setScale(next) {
    scale = Math.max(minScale, Math.min(maxScale, next));
    if (scale === minScale) { offsetX = 0; offsetY = 0; }
    render();
  }

  zoomIn.onclick = () => setScale(scale * 1.5);
  zoomOut.onclick = () => setScale(scale / 1.5);
  reset.onclick = () => setScale(1);
  function isExpanded() {
    // The document retargets fullscreenElement to the shadow host.
    return viewer.matches(':fullscreen');
  }
  expand.onclick = async () => {
    if (isExpanded()) {
      await document.exitFullscreen();
    } else {
      await viewer.requestFullscreen();
    }
    onFullscreenChange();
  };

  function onFullscreenChange() {
    const expanded = isExpanded();
    expand.setAttribute('aria-label', expanded ? 'Exit expanded map' : 'Expand map');
    expand.title = expanded ? 'Exit expanded map' : 'Expand map';
    expand.setAttribute('aria-pressed', String(expanded));
    render();
  }

  function onPointerDown(event) {
    if (scale <= minScale) return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY,
             offsetX, offsetY };
    viewport.setPointerCapture(event.pointerId);
    viewport.classList.add('is-dragging');
    event.preventDefault();
  }

  function onPointerMove(event) {
    if (!drag || drag.id !== event.pointerId) return;
    offsetX = drag.offsetX + event.clientX - drag.x;
    offsetY = drag.offsetY + event.clientY - drag.y;
    render();
  }

  function onPointerUp(event) {
    if (!drag || drag.id !== event.pointerId) return;
    drag = null;
    viewport.classList.remove('is-dragging');
  }

  document.addEventListener('fullscreenchange', onFullscreenChange);
  viewport.addEventListener('pointerdown', onPointerDown);
  viewport.addEventListener('pointermove', onPointerMove);
  viewport.addEventListener('pointerup', onPointerUp);
  viewport.addEventListener('pointercancel', onPointerUp);
  const resizeObserver = new ResizeObserver(render);
  resizeObserver.observe(viewport);
  render();

  return () => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    resizeObserver.disconnect();
    viewport.removeEventListener('pointerdown', onPointerDown);
    viewport.removeEventListener('pointermove', onPointerMove);
    viewport.removeEventListener('pointerup', onPointerUp);
    viewport.removeEventListener('pointercancel', onPointerUp);
  };
}
"""

_MAP_VIEWER = st.components.v2.component(
    "qc_subject_map_viewer",
    html=_MAP_HTML,
    css=_MAP_CSS,
    js=_MAP_JS,
)


def render_subject_map(svg: str, subject: str) -> None:
    """Keep the SVG crisp and zoomable in both normal and expanded views."""
    _MAP_VIEWER(
        data={"svg": svg, "label": f"Subject map for {subject}"},
        key="qc_subject_map_viewer",
    )
