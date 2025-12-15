"""
PathwayViz Demo

Run with: python -m pathway_viz

Demonstrates real-time streaming with Pathway + Kafka and embeddable widgets.
"""

from .pathway import run_pathway_demo


def run_demo(port: int = 3000):
    """Run the PathwayViz demo."""
    run_pathway_demo(port=port)


__all__ = [
    "run_demo",
    "run_pathway_demo",
]
