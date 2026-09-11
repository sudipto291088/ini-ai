from pathlib import Path


APP_SOURCE = (
    Path(__file__).resolve().parents[1] / "streamlit_app" / "app.py"
).read_text(encoding="utf-8")


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
