"""
StreamViz - Real-time streaming data visualization.

A lightweight, Streamlit-like dashboard for visualizing streaming data
from Kafka, Redpanda, or any Python data source.

Quick Start:
    import stream_viz as sv

    # Define your dashboard
    sv.title("My Dashboard")
    cpu = sv.metric("cpu", title="CPU Usage", unit="%")

    sv.start(port=3000)

    while True:
        cpu.send(get_cpu_usage())

With Kafka:
    import stream_viz as sv
    from kafka import KafkaConsumer

    sv.title("Kafka Metrics")
    cpu = sv.metric("cpu", title="CPU %")
    mem = sv.metric("memory", title="Memory %")

    sv.start(port=3000)

    for msg in KafkaConsumer("metrics", bootstrap_servers=["localhost:9092"]):
        data = json.loads(msg.value)
        cpu.send(data["cpu"])
        mem.send(data["memory"])
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from ._stream_viz import (
    send_data as _send_data,
)
from ._stream_viz import (
    start_demo as _start_demo,
)
from ._stream_viz import (
    start_server as _start_server,
)

__version__ = "0.1.0"
__all__ = [
    # High-level API (Streamlit-like)
    "title",
    "metric",
    "start",
    "run_demo",
    # Classes
    "Metric",
    "Dashboard",
    # Low-level API
    "send_json",
]


# =============================================================================
# Dashboard State (Module-level singleton like Streamlit)
# =============================================================================


@dataclass
class DashboardConfig:
    """Configuration for the dashboard."""

    title: str = "StreamViz"
    metrics: dict[str, Metric] = field(default_factory=dict)
    started: bool = False


_dashboard = DashboardConfig()


def _get_dashboard() -> DashboardConfig:
    """Get the global dashboard configuration."""
    return _dashboard


def _send_config() -> None:
    """Send the current dashboard configuration to all clients."""
    config = {
        "type": "config",
        "title": _dashboard.title,
        "metrics": {
            name: {
                "id": m.id,
                "title": m.title,
                "unit": m.unit,
                "color": m.color,
                "max_points": m.max_points,
            }
            for name, m in _dashboard.metrics.items()
        },
    }
    _send_data(json.dumps(config))


# =============================================================================
# High-Level API
# =============================================================================


def title(text: str) -> None:
    """
    Set the dashboard title.

    Args:
        text: The title to display at the top of the dashboard.

    Example:
        >>> import stream_viz as sv
        >>> sv.title("Production Metrics")
    """
    _dashboard.title = text
    if _dashboard.started:
        _send_config()


@dataclass
class Metric:
    """
    A metric that can be streamed to the dashboard.

    Each metric gets its own chart. Create metrics using sv.metric().
    """

    id: str
    title: str
    unit: str
    color: str
    max_points: int

    def send(self, value: float, timestamp: float | int | None = None) -> None:
        """
        Send a data point for this metric.

        Args:
            value: The numeric value to display.
            timestamp: Unix timestamp in milliseconds. If None, uses current time.

        Example:
            >>> cpu = sv.metric("cpu", title="CPU Usage")
            >>> cpu.send(75.5)
        """
        if timestamp is None:
            timestamp = time.time() * 1000

        msg = {
            "type": "data",
            "metric": self.id,
            "timestamp": int(timestamp),
            "value": float(value),
        }
        _send_data(json.dumps(msg))


# Color palette for auto-assignment
_COLORS = [
    "#00d4ff",  # cyan
    "#00ff88",  # green
    "#ff6b6b",  # red
    "#ffd93d",  # yellow
    "#c44dff",  # purple
    "#ff8c42",  # orange
    "#6bceff",  # light blue
    "#95e1a3",  # light green
]
_color_index = 0


def metric(
    id: str,
    *,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    max_points: int = 200,
) -> Metric:
    """
    Create a metric to stream to the dashboard.

    Each metric gets its own chart. You can create multiple metrics
    to build a multi-chart dashboard.

    Args:
        id: Unique identifier for this metric (e.g., "cpu", "memory").
        title: Display title for the chart. Defaults to the id.
        unit: Unit label (e.g., "%", "ms", "req/s").
        color: Chart line color. Auto-assigned if not specified.
        max_points: Maximum points to show (older points scroll off).

    Returns:
        A Metric object with a .send() method.

    Example:
        >>> import stream_viz as sv
        >>>
        >>> cpu = sv.metric("cpu", title="CPU Usage", unit="%")
        >>> memory = sv.metric("memory", title="Memory", unit="%", color="#00ff88")
        >>> latency = sv.metric("latency", title="Latency", unit="ms")
        >>>
        >>> sv.start()
        >>> cpu.send(75.5)
        >>> memory.send(60.2)
    """
    global _color_index

    if id in _dashboard.metrics:
        return _dashboard.metrics[id]

    if color is None:
        color = _COLORS[_color_index % len(_COLORS)]
        _color_index += 1

    m = Metric(
        id=id,
        title=title or id,
        unit=unit,
        color=color,
        max_points=max_points,
    )
    _dashboard.metrics[id] = m

    if _dashboard.started:
        _send_config()

    return m


def _config_broadcaster() -> None:
    """Background thread that periodically re-sends config."""
    while _dashboard.started:
        time.sleep(2.0)
        if _dashboard.metrics:
            _send_config()


def start(port: int = 3000) -> None:
    """
    Start the StreamViz server.

    The server runs in a background thread, so your Python code continues
    executing. After calling this, use metric.send() to push data.

    Args:
        port: The port to listen on. Default is 3000.

    Example:
        >>> import stream_viz as sv
        >>>
        >>> sv.title("My Dashboard")
        >>> cpu = sv.metric("cpu", title="CPU %")
        >>>
        >>> sv.start(port=3000)
        >>>
        >>> while True:
        ...     cpu.send(get_cpu())
        ...     time.sleep(0.1)
    """
    import threading
    
    _start_server(port)
    _dashboard.started = True
    time.sleep(0.3)  # Give server time to start

    # Send config immediately
    _send_config()
    
    # Start background thread to periodically re-send config
    # This ensures new clients always get config
    config_thread = threading.Thread(target=_config_broadcaster, daemon=True)
    config_thread.start()

    print(f"Dashboard: http://localhost:{port}")


def run_demo(port: int = 3000) -> None:
    """
    Run the built-in demo with sample metrics.

    This starts the server and generates fake CPU, memory, and latency data.
    Useful for testing that everything works.

    Note: This function blocks forever.

    Args:
        port: The port to listen on. Default is 3000.
    """
    import math
    import random

    title("StreamViz Demo")
    cpu = metric("cpu", title="CPU Usage", unit="%")
    memory = metric("memory", title="Memory", unit="%", color="#00ff88")
    latency = metric("latency", title="Latency", unit="ms", color="#ff6b6b")
    rps = metric("rps", title="Requests/sec", color="#ffd93d")

    start(port)

    i = 0
    base_memory = 50.0

    try:
        while True:
            t = time.time()

            # CPU: sine wave with noise
            cpu_val = 50 + 30 * math.sin(i * 0.05) + random.gauss(0, 5)
            cpu.send(max(0, min(100, cpu_val)))

            # Memory: slowly trending up with resets
            base_memory += random.gauss(0.01, 0.1)
            if base_memory > 85:
                base_memory = 50  # "garbage collection"
            memory.send(max(0, min(100, base_memory + random.gauss(0, 2))))

            # Latency: mostly low, occasional spikes
            if random.random() < 0.05:
                lat = random.uniform(100, 300)
            else:
                lat = 15 + abs(random.gauss(0, 10))
            latency.send(lat)

            # RPS: traffic pattern
            base_rps = 500 + 200 * math.sin(i * 0.02)
            if random.random() < 0.1:
                base_rps *= random.uniform(1.5, 2.5)  # traffic spike
            rps.send(max(0, base_rps + random.gauss(0, 50)))

            time.sleep(0.05)
            i += 1

    except KeyboardInterrupt:
        print("\nDemo stopped.")


# =============================================================================
# Low-Level API
# =============================================================================


def send_json(data: dict[str, Any]) -> None:
    """
    Send arbitrary JSON data to all connected clients (low-level).

    For the charts to work, use the metric API instead.
    This is useful for custom frontend implementations.

    Args:
        data: A dictionary to serialize and send as JSON.
    """
    _send_data(json.dumps(data))
