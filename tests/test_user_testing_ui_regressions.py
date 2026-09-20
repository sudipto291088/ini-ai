from pathlib import Path


APP_SOURCE = (
    Path(__file__).resolve().parents[1] / "streamlit_app" / "app.py"
).read_text(encoding="utf-8")
FCE_CONTENT_SOURCE = (
    Path(__file__).resolve().parents[1] / "streamlit_app" / "fce_content.py"
).read_text(encoding="utf-8")
FCE_COMPONENT_SOURCE = (
    Path(__file__).resolve().parents[1] / "streamlit_app" / "fce_component.py"
).read_text(encoding="utf-8")


def test_sidebar_clock_does_not_force_periodic_app_rerenders() -> None:
    assert "_render_clock_tile()" in APP_SOURCE
    assert 'run_every="1s"' not in APP_SOURCE
    assert "st_autorefresh" not in APP_SOURCE


def test_saved_chat_dialog_uses_plain_language_and_clear_resume_action() -> None:
    assert '@st.dialog("Resume saved conversation")' in APP_SOURCE
    assert "Resume conversation:" in APP_SOURCE
    assert "#### Follow-up questions" in APP_SOURCE
    assert "#### Suggested actions" in APP_SOURCE
    assert "Session Branches" not in APP_SOURCE
    assert "#### FUQs" not in APP_SOURCE
    assert "#### CTAs" not in APP_SOURCE


def test_projects_are_marked_unavailable_before_navigation() -> None:
    assert '<span class="ini-sidebar-nav-title">New Project</span>' in APP_SOURCE
    assert '<small class="ini-sidebar-nav-status">Coming soon</small>' in APP_SOURCE
    assert "Projects are coming soon" in APP_SOURCE
    assert "Project creation is not available in this release." in APP_SOURCE
    assert "No active projects yet" not in APP_SOURCE
    assert "Created projects will appear here." not in APP_SOURCE


def test_my_new_learning_is_marked_unavailable_everywhere() -> None:
    assert '<span class="ini-sidebar-nav-title">My New Learning</span>' in APP_SOURCE
    assert '<small class="ini-sidebar-nav-status">Not available</small>' in APP_SOURCE
    assert "Learning is not available yet" in APP_SOURCE
    assert "This area is not ready for testing." in APP_SOURCE
    assert "My New Learning has not entered development yet" in APP_SOURCE
    assert "No active learning yet" not in APP_SOURCE
    assert "Saved learning paths will appear here." not in APP_SOURCE
    assert "not MNL_AVAILABLE" in APP_SOURCE
    assert 'placeholder="Ask InI anything to learn..."' in APP_SOURCE


def test_new_chat_mobile_styles_wrap_copy_and_clear_hosting_overlay() -> None:
    assert "white-space: normal !important;" in APP_SOURCE
    assert "word-break: normal !important;" in APP_SOURCE
    assert "bottom: calc(58px + env(safe-area-inset-bottom));" in APP_SOURCE
    assert "padding-bottom: calc(196px + env(safe-area-inset-bottom))" in APP_SOURCE


def test_learning_flow_import_recovers_from_a_stale_streamlit_module() -> None:
    assert "import streamlit_app.learning_flow as learning_flow" in APP_SOURCE
    assert 'if not hasattr(learning_flow, "resolve_generation_status"):' in APP_SOURCE
    assert "learning_flow = importlib.reload(learning_flow)" in APP_SOURCE


def test_explore_direction_cards_have_borderless_quiet_surfaces() -> None:
    assert ".st-key-nc_explore_grid div.stButton > button {{" in APP_SOURCE
    assert "border: 0 !important;" in APP_SOURCE
    assert "background: rgba(255, 255, 255, 0.98) !important;" in APP_SOURCE
    assert "0 14px 34px rgba(15, 23, 42, 0.065)" in APP_SOURCE
    assert "0 3px 10px rgba(15, 23, 42, 0.035)" in APP_SOURCE
    assert "font-weight: 560 !important;" in APP_SOURCE
    assert ".st-key-nc_explore_grid div.stButton > button:focus-visible" in APP_SOURCE


def test_first_visit_introduction_is_shorter_and_visually_demonstrates_features() -> None:
    assert FCE_CONTENT_SOURCE.count('"text":') == 6
    assert FCE_CONTENT_SOURCE.count('"visual":') == 3
    assert "Most AI systems answer your question" not in FCE_CONTENT_SOURCE
    assert "My New Learning is also evolving" not in FCE_CONTENT_SOURCE
    assert "const visualMarkup = (visual)" in FCE_COMPONENT_SOURCE
    assert "From one thought to a learning path" in FCE_COMPONENT_SOURCE
    assert "Two ways to read an answer" in FCE_COMPONENT_SOURCE
    assert "A connected knowledge structure" in FCE_COMPONENT_SOURCE
