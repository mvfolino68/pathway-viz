"""
PathwayViz - The visualization layer for Pathway.

Real-time dashboards and embeddable widgets for Pathway streaming pipelines.

Example (Dashboard):
    import pathway as pw
    import pathwayviz as pv

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
    pv.title("Order Analytics")
    pv.table(by_region, title="By Region")
    pv.stat(totals, "total", title="Total Revenue", unit="$")
    pv.start()
    pw.run()

Example (Embeddable):
    # Add embed=True for embeddable single-widget endpoints
    pv.table(by_region, id="regions", embed=True)
    pv.start()
    # Access at: /embed/regions
"""

from __future__ import annotations

import json
from typing import Any

# Re-export public API
from ._config import configure, title
from ._pathway_viz import send_data as _send_data
from ._server import start, stop
from ._widgets import chart, gauge, stat, table

try:
    from importlib.metadata import version as _get_version

    __version__ = _get_version("pathway-viz")
except Exception:
    __version__ = "0.0.0"  # Fallback for development
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
]


def send_json(data: dict[str, Any]) -> None:
    """
    Send arbitrary JSON to all connected clients.

    For standard widgets, use the widget API instead.
    """
    _send_data(json.dumps(data))
