"""
StreamViz CLI commands for project scaffolding and templates.
"""

from __future__ import annotations

import shutil
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def init_project(
    target_dir: str,
    include_k8s: bool = False,
    force: bool = False,
) -> None:
    """
    Initialize a new StreamViz project with deployment files.

    Args:
        target_dir: Directory to create the project in
        include_k8s: Include Kubernetes manifests
        force: Overwrite existing files
    """
    target = Path(target_dir)

    if target.exists() and not force:
        if any(target.iterdir()):
            raise FileExistsError(f"Directory '{target}' is not empty. Use --force to overwrite.")

    target.mkdir(parents=True, exist_ok=True)

    # Core files
    files_to_copy = [
        "docker-compose.yml",
        "Dockerfile",
        "pipeline.py",
        "README.md",
    ]

    for filename in files_to_copy:
        src = TEMPLATES_DIR / filename
        dst = target / filename
        if src.exists():
            shutil.copy(src, dst)
            print(f"  Created {filename}")

    # Kubernetes files
    if include_k8s:
        k8s_dir = target / "k8s"
        k8s_dir.mkdir(exist_ok=True)

        k8s_files = [
            ("k8s-deployment.yaml", "deployment.yaml"),
            ("k8s-service.yaml", "service.yaml"),
            ("k8s-ingress.yaml", "ingress.yaml"),
        ]

        for src_name, dst_name in k8s_files:
            src = TEMPLATES_DIR / src_name
            dst = k8s_dir / dst_name
            if src.exists():
                shutil.copy(src, dst)
                print(f"  Created k8s/{dst_name}")

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
        "k8s-deployment": "k8s-deployment.yaml",
        "k8s-service": "k8s-service.yaml",
        "k8s-ingress": "k8s-ingress.yaml",
        "deployment": "k8s-deployment.yaml",
        "service": "k8s-service.yaml",
        "ingress": "k8s-ingress.yaml",
    }

    filename = name_map.get(name.lower(), name)
    template_path = TEMPLATES_DIR / filename

    if not template_path.exists():
        available = [f.name for f in TEMPLATES_DIR.iterdir() if not f.name.startswith("_")]
        raise FileNotFoundError(
            f"Template '{name}' not found.\nAvailable templates: {', '.join(sorted(available))}"
        )

    print(template_path.read_text())


def list_templates() -> None:
    """List all available templates."""
    print("Available templates:\n")

    categories = {
        "Docker": ["Dockerfile", "docker-compose.yml"],
        "Pipeline": ["pipeline.py", "README.md"],
        "Kubernetes": ["k8s-deployment.yaml", "k8s-service.yaml", "k8s-ingress.yaml"],
    }

    for category, files in categories.items():
        print(f"  {category}:")
        for f in files:
            if (TEMPLATES_DIR / f).exists():
                print(f"    - {f}")
        print()

    print("Usage:")
    print("  stream-viz show docker-compose    # Print to stdout")
    print("  stream-viz init my-project        # Create project directory")
