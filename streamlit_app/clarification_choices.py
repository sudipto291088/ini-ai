"""Meaning confirmation using the same rows as the Learning trail."""
import importlib
from api.abbreviation_clarification import clarification_choices

CLARIFICATION_CHOICES_VERSION = 2

learning_trail = importlib.import_module("streamlit_app.learning_trail")
if not hasattr(learning_trail, "render_trail_rows"):
    learning_trail = importlib.reload(learning_trail)

MEANING_DETAILS = {
    "Machine learning": ("Models that learn patterns from data.", "model_training"),
    "Maximum likelihood": ("Estimating parameters from observed data.", "query_stats"),
    "Millilitres": ("A unit for measuring volume.", "water_drop"),
    "Artificial intelligence": ("Intelligent systems and their capabilities.", "neurology"),
    "Artificial insemination": ("The reproductive procedure.", "biotech"),
    "Operating system": ("Software that manages a computer’s resources.", "computer"),
    "Computer vision": ("Understanding images and visual information.", "visibility"),
    "Curriculum vitae": ("An academic or professional record.", "description"),
    "Cross-validation": ("Evaluating a model across data splits.", "fact_check"),
    "Reinforcement learning": ("Learning through actions and rewards.", "route"),
}


def render_clarification_choices(prompt: str, key: str, *, disabled: bool = False) -> str | None:
    actions = []
    for index, choice in enumerate(clarification_choices(prompt)):
        description, icon = MEANING_DETAILS.get(choice, ("Continue with this meaning.", "arrow_forward"))
        actions.append(dict(action=str(index), title=choice, description=description, icon=icon))
    selected = learning_trail.render_trail_rows(
        actions, f"meaning-{key}", heading="Choose the meaning", disabled=disabled,
    )
    return selected["title"] if selected else None
