"""
PathwayViz CLI commands for project scaffolding and templates.
"""

from __future__ import annotations

from pathlib import Path

from pathway_viz.templates import get_template


def init_project(
    target_dir: str,
    force: bool = False,
) -> None:
    """
    Initialize a new PathwayViz project with deployment files.

    Args:
        target_dir: Directory to create the project in
        force: Overwrite existing files
    """
    target = Path(target_dir)

    if target.exists() and not force:
        if any(target.iterdir()):
            raise FileExistsError(f"Directory '{target}' is not empty. Use --force to overwrite.")

    target.mkdir(parents=True, exist_ok=True)

    # Core files
    files_to_create = [
        "docker-compose.yml",
        "Dockerfile",
        "pipeline.py",
        "README.md",
    ]

    for filename in files_to_create:
        try:
            content = get_template(filename)
            dst = target / filename
            dst.write_text(content)
            print(f"  Created {filename}")
        except FileNotFoundError:
            print(f"  Warning: Template '{filename}' not found, skipping")

    print(f"\n✓ Project initialized in {target}/")
    print("\nNext steps:")
    print(f"  cd {target}")
    print("  docker compose up -d     # Start with Docker")
    print("  # OR")
    print("  python pipeline.py --mode simple  # Run without Docker")


def show_template(name: str) -> None:
    """
    Print a template file to stdout.

    Args:
        name: Template name (e.g., 'docker-compose.yml', 'Dockerfile')
    """
    # Map friendly names to actual files
    name_map = {
        "docker-compose": "docker-compose.yml",
        "compose": "docker-compose.yml",
        "dockerfile": "Dockerfile",
        "pipeline": "pipeline.py",
        "readme": "README.md",
    }

    filename = name_map.get(name.lower(), name)

    try:
        content = get_template(filename)
        print(content)
    except FileNotFoundError:
        from pathway_viz.templates import list_templates as get_all_templates

        available = get_all_templates()
        raise FileNotFoundError(
            f"Template '{name}' not found.\nAvailable templates: {', '.join(sorted(available))}"
        )


def list_templates() -> None:
    """List all available templates."""
    from pathway_viz.templates import list_templates as get_all_templates

    all_templates = get_all_templates()

    print("Available templates:\n")

    categories = {
        "Docker": ["Dockerfile", "docker-compose.yml"],
        "Pipeline": ["pipeline.py", "README.md"],
    }

    for category, files in categories.items():
        print(f"  {category}:")
        available_in_category = [f for f in files if f in all_templates]
        if available_in_category:
            for f in available_in_category:
                print(f"    - {f}")
        print()

    print("Usage:")
    print("  pathway-viz show docker-compose    # Print to stdout")
    print("  pathway-viz init my-project        # Create project directory")
