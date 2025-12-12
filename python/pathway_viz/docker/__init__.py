"""
PathwayViz Docker files.

These files are used by the demo and can be copied for new projects.
"""

from pathlib import Path

DOCKER_DIR = Path(__file__).parent


def get_docker_file(name: str) -> Path:
    """Get path to a Docker file."""
    path = DOCKER_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Docker file not found: {name}")
    return path


def get_compose_file() -> Path:
    """Get path to docker-compose.yml."""
    return get_docker_file("docker-compose.yml")


def get_dockerfile() -> Path:
    """Get path to Dockerfile."""
    return get_docker_file("Dockerfile")
