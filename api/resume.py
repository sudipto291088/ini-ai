# api/resume.py

from __future__ import annotations
from typing import Dict, List


def resume() -> Dict[str, object]:
    """
    v0 Resume intelligence.
    Guides a user on how to continue work after a pause.
    This is deterministic and project-aware (not user-aware yet).
    """

    steps: List[str] = [
        "Open the project folder in VS Code.",
        "Start the FastAPI backend using uvicorn.",
        "Start the Streamlit app in a separate terminal.",
        "Verify backend health at /docs.",
        "Continue working inside the api/ directory (not UI).",
    ]

    commands: List[str] = [
        "python -m uvicorn api.main:app --reload --port 8000",
        "python -m streamlit run streamlit_app/app.py",
    ]

    common_checks: List[str] = [
        "If import errors occur, confirm file names and function names match.",
        "If ports are busy, change the port number.",
        "If UI errors appear, confirm API response shape hasn’t changed.",
    ]

    next_tasks: List[str] = [
        "Improve interrogation intelligence (topic-type detection).",
        "Refine illustration structure.",
        "Add persistence (remember last topic or state).",
    ]

    return {
        "status": "resume-ready",
        "steps": steps,
        "commands": commands,
        "checks": common_checks,
        "next_tasks": next_tasks,
        "notes": [
            "v0 resume logic is generic.",
            "Later versions can be user-specific and state-aware.",
        ],
    }
