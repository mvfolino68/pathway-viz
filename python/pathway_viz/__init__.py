"""
PathwayViz - The visualization layer for Pathway.

Real-time dashboards and embeddable widgets for Pathway streaming pipelines.

Example (Dashboard):
    import pathway as pw
    import pathway_viz as sv

    # Your Pathway pipeline
    orders = pw.io.kafka.read(...)
    by_region = orders.groupby(pw.this.region).reduce(
        revenue=pw.reducers.sum(pw.this.amount),
        count=pw.reducers.count(),
    )
    totals = orders.reduce(
        total=pw.reducers.sum(pw.this.amount),
    )

    # Visualize
    sv.title("Order Analytics")
    sv.table(by_region, title="By Region")
    sv.stat(totals, "total", title="Total Revenue", unit="$")
    sv.start()
    pw.run()

Example (Embeddable):
    # Add embed=True for embeddable single-widget endpoints
    sv.table(by_region, id="regions", embed=True)
    sv.start()
    # Access at: /embed/regions
"""

from __future__ import annotations

import json
from typing import Any

# Re-export public API
from ._config import configure, title
from ._demo import run_demo
from ._pathway_viz import send_data as _send_data
from ._server import start, stop
from ._widgets import chart, gauge, stat, table

__version__ = "0.1.0"
__all__ = [
    # Primary API (Pathway)
    "table",
    "stat",
    "chart",
    "gauge",
    # Dashboard
    "title",
    "configure",
    "start",
    "stop",
    # Utilities
    "send_json",
    "run_demo",
]


def send_json(data: dict[str, Any]) -> None:
    """
    Send arbitrary JSON to all connected clients.

    For standard widgets, use the widget API instead.
    """
    _send_data(json.dumps(data))
