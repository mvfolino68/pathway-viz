"""
StreamViz Demo

Run with: python -m stream_viz

Demonstrates real-time streaming with Pathway + Kafka and embeddable widgets.
"""

from .pathway import run_pathway_demo


def run_demo(port: int = 3000):
    """Run the StreamViz demo."""
    run_pathway_demo(port=port)


__all__ = [
    "run_demo",
    "run_pathway_demo",
]
