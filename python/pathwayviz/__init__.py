"""
PathwayViz - Embeddable real-time widgets for Pathway streaming pipelines.

Example:
    import pathway as pw
    import pathwayviz as pv

    orders = pw.io.kafka.read(...)
    revenue = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
    by_region = orders.groupby(pw.this.region).reduce(...)

    # Create server and register widgets
    server = pv.WidgetServer(port=3000)
    server.register(pv.Stat(revenue, "revenue", id="revenue", title="Revenue"))
    server.register(pv.Table(by_region, id="regions", title="By Region"))
    server.start()
    pw.run()

    # Embed via: <iframe src="http://localhost:3000/embed/revenue"></iframe>
"""

from __future__ import annotations

import json
from typing import Any

from ._pathwayviz import send_data as _send_data
from ._server import WidgetServer
from ._widgets import Chart, Gauge, Stat, Table, Widget

try:
    from importlib.metadata import version as _get_version

    __version__ = _get_version("pathway-viz")
except Exception:
    __version__ = "0.0.0"  # Fallback for development

__all__ = [
    "WidgetServer",
    "Widget",
    "Stat",
    "Chart",
    "Gauge",
    "Table",
    "send_json",
]


def send_json(data: dict[str, Any]) -> None:
    """
    Send arbitrary JSON to all connected clients.

    For standard widgets, use the widget API instead.
    """
    _send_data(json.dumps(data))
