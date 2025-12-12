"""
StreamViz project templates.

These templates are used by `stream-viz init` to scaffold new projects.
"""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent


def get_template(name: str) -> str:
    """Get a template file's contents."""
    template_path = TEMPLATES_DIR / name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {name}")
    return template_path.read_text()


def list_templates() -> list[str]:
    """List all available templates."""
    return [f.name for f in TEMPLATES_DIR.iterdir() if f.is_file() and not f.name.startswith("_")]
