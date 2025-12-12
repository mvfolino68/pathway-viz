"""
PathwayViz project templates.

These templates are used by `pathway-viz init` to scaffold new projects.
All templates are stored as actual files for better maintainability.
"""

from pathlib import Path

# Directories containing templates
TEMPLATES_DIR = Path(__file__).parent
DOCKER_DIR = Path(__file__).parent.parent / "docker"


def get_template(name: str) -> str:
    """Get a template's contents."""
    # Check templates directory first
    template_file = TEMPLATES_DIR / name
    if template_file.exists():
        return template_file.read_text()

    # Check docker directory
    docker_file = DOCKER_DIR / name
    if docker_file.exists():
        return docker_file.read_text()

    raise FileNotFoundError(f"Template not found: {name}")


def list_templates() -> list[str]:
    """List all available templates."""
    templates = []

    # Add template files
    if TEMPLATES_DIR.exists():
        templates.extend(
            f.name for f in TEMPLATES_DIR.iterdir() if f.is_file() and not f.name.startswith("_")
        )

    # Add docker files
    if DOCKER_DIR.exists():
        templates.extend(
            f.name for f in DOCKER_DIR.iterdir() if f.is_file() and not f.name.startswith("_")
        )

    return sorted(set(templates))
