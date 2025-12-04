"""
StreamViz - The visualization layer for Pathway.

Real-time dashboards for streaming data pipelines. Purpose-built for
Pathway, but works with any Python data source.

Pathway Integration (Primary API):

    import pathway as pw
    import stream_viz as sv

    # Your Pathway pipeline
    orders = pw.io.kafka.read(...)
    stats = orders.groupby(pw.this.region).reduce(
        total=pw.reducers.sum(pw.this.amount),
        count=pw.reducers.count(),
    )

    # Visualize it
    sv.title("Order Analytics")
    sv.pathway_table(stats, title="Orders by Region")
    sv.start()
    pw.run()

Standalone Mode (No Pathway):

    import stream_viz as sv

    sv.title("My Dashboard")
    cpu = sv.gauge("cpu", title="CPU", unit="%", max_val=100)
    latency = sv.metric("latency", title="Latency", unit="ms")

    sv.start()

    while True:
        cpu.send(get_cpu_usage())
        latency.send(get_latency())
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ._stream_viz import send_data as _send_data
from ._stream_viz import start_server as _start_server

__version__ = "0.1.0"
__all__ = [
    # Pathway Integration (primary API)
    "pathway_table",
    "pathway_stat",
    "pathway_metric",
    # Core Widgets
    "title",
    "metric",
    "stat",
    "gauge",
    "table",
    "text",
    "start",
    "configure",
    # Layout
    "columns",
    "row",
    # Demo
    "run_demo",
    # Low-level
    "send_json",
]


# =============================================================================
# Aggregation System
# =============================================================================


class Aggregation(Enum):
    """Aggregation functions for windowed metrics."""

    NONE = "none"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"
    RATE = "rate"  # Events per second


def _parse_window(window: str | None) -> float | None:
    """Parse window string like '30s', '1m', '5m' into seconds."""
    if window is None:
        return None

    w = window.strip().lower()
    if w.endswith("ms"):
        return float(w[:-2]) / 1000
    elif w.endswith("s"):
        return float(w[:-1])
    elif w.endswith("m"):
        return float(w[:-1]) * 60
    elif w.endswith("h"):
        return float(w[:-1]) * 3600
    else:
        return float(w)


def _parse_aggregation(agg: str | Aggregation | None) -> Aggregation:
    """Parse aggregation string or enum."""
    if agg is None:
        return Aggregation.NONE
    if isinstance(agg, Aggregation):
        return agg
    return Aggregation(agg.lower())


class TumblingWindow:
    """
    Tumbling window aggregator.

    Collects values for a fixed time window, then emits the aggregate
    and resets. Used for metrics like "orders per minute" or "avg latency".
    """

    def __init__(self, window_seconds: float, aggregation: Aggregation):
        self.window_seconds = window_seconds
        self.aggregation = aggregation
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self._window_start = time.time()
        self._count = 0
        self._sum = 0.0
        self._min = float("inf")
        self._max = float("-inf")
        self._last = 0.0

    def add(self, value: float) -> tuple[float | None, float | None]:
        """
        Add a value. Returns (aggregate, timestamp_ms) if window completed, else (None, None).
        """
        now = time.time()

        with self._lock:
            elapsed = now - self._window_start
            result = None
            result_ts = None

            # Check if window expired
            if elapsed >= self.window_seconds and self._count > 0:
                result = self._compute()
                result_ts = self._window_start * 1000
                self._reset()

            # Add to current window
            self._count += 1
            self._sum += value
            self._min = min(self._min, value)
            self._max = max(self._max, value)
            self._last = value

            return result, result_ts

    def _compute(self) -> float:
        """Compute the aggregate for current window."""
        elapsed = time.time() - self._window_start

        if self._count == 0:
            return 0.0

        if self.aggregation == Aggregation.SUM:
            return self._sum
        elif self.aggregation == Aggregation.AVG:
            return self._sum / self._count
        elif self.aggregation == Aggregation.MIN:
            return self._min if self._min != float("inf") else 0.0
        elif self.aggregation == Aggregation.MAX:
            return self._max if self._max != float("-inf") else 0.0
        elif self.aggregation == Aggregation.COUNT:
            return float(self._count)
        elif self.aggregation == Aggregation.RATE:
            return self._count / elapsed if elapsed > 0 else 0.0
        else:  # LAST or NONE
            return self._last


# =============================================================================
# Dashboard State
# =============================================================================


@dataclass
class Config:
    """Global dashboard configuration."""

    title: str = "StreamViz"
    theme: str = "dark"
    port: int = 3000
    buffer_size: int = 1000  # Points to keep per widget


@dataclass
class DashboardState:
    """Global dashboard state (singleton)."""

    config: Config = field(default_factory=Config)
    widgets: dict[str, dict] = field(default_factory=dict)
    layout: list = field(default_factory=list)
    started: bool = False
    _windows: dict[str, TumblingWindow] = field(default_factory=dict)
    _color_index: int = 0


_state = DashboardState()

# Color palette
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


def _next_color() -> str:
    color = _COLORS[_state._color_index % len(_COLORS)]
    _state._color_index += 1
    return color


def _send_config() -> None:
    """Send dashboard config to all clients."""
    msg = {
        "type": "config",
        "title": _state.config.title,
        "theme": _state.config.theme,
        "widgets": _state.widgets,
        "layout": _state.layout,
    }
    _send_data(json.dumps(msg))


def _add_widget(widget_id: str, widget_config: dict) -> None:
    """Register a widget."""
    _state.widgets[widget_id] = widget_config
    if widget_id not in [w for w in _state.layout if isinstance(w, str)]:
        _state.layout.append(widget_id)
    if _state.started:
        _send_config()


# =============================================================================
# Widget Classes
# =============================================================================


@dataclass
class Metric:
    """
    A streaming time-series metric.

    Displays as a line chart with current value. Supports optional
    windowed aggregation for patterns like "sum per minute".
    """

    id: str
    title: str
    unit: str
    color: str
    max_points: int
    _has_window: bool = False

    def send(self, value: float, timestamp: float | None = None) -> None:
        """
        Send a data point.

        If windowed aggregation is configured, values are collected and
        the aggregate is emitted when the window completes.
        """
        if timestamp is None:
            timestamp = time.time() * 1000

        # Check for windowed aggregation
        if self.id in _state._windows:
            window = _state._windows[self.id]
            agg_value, agg_ts = window.add(value)
            if agg_value is not None:
                self._emit(agg_value, agg_ts)
        else:
            self._emit(value, timestamp)

    def _emit(self, value: float, timestamp: float) -> None:
        """Actually send the data point."""
        msg = {
            "type": "data",
            "widget": self.id,
            "timestamp": int(timestamp),
            "value": float(value),
        }
        _send_data(json.dumps(msg))


@dataclass
class Stat:
    """
    A big number display with optional delta.

    Shows a prominent number with change indicator.
    """

    id: str
    title: str
    unit: str
    color: str
    _last_value: float | None = None

    def send(self, value: float, timestamp: float | None = None) -> None:
        """Update the stat value."""
        if timestamp is None:
            timestamp = time.time() * 1000

        delta = None
        if self._last_value is not None:
            delta = value - self._last_value
        self._last_value = value

        msg = {
            "type": "data",
            "widget": self.id,
            "timestamp": int(timestamp),
            "value": float(value),
            "delta": delta,
        }
        _send_data(json.dumps(msg))


@dataclass
class Gauge:
    """
    A circular gauge for bounded values.

    Great for CPU %, memory %, or any 0-100 type metric.
    """

    id: str
    title: str
    unit: str
    min_val: float
    max_val: float
    color: str
    thresholds: list[tuple[float, str]]

    def send(self, value: float, timestamp: float | None = None) -> None:
        """Update the gauge value."""
        if timestamp is None:
            timestamp = time.time() * 1000

        msg = {
            "type": "data",
            "widget": self.id,
            "timestamp": int(timestamp),
            "value": float(value),
        }
        _send_data(json.dumps(msg))


@dataclass
class Table:
    """
    A streaming table showing recent rows.

    New rows appear at top, old rows scroll off.
    """

    id: str
    title: str
    columns: list[dict]
    max_rows: int

    def send(self, row: dict[str, Any], timestamp: float | None = None) -> None:
        """Add a row to the table."""
        if timestamp is None:
            timestamp = time.time() * 1000

        msg = {
            "type": "data",
            "widget": self.id,
            "timestamp": int(timestamp),
            "row": row,
        }
        _send_data(json.dumps(msg))


# =============================================================================
# Public API - Configuration
# =============================================================================


def configure(
    *,
    theme: str | None = None,
    title: str | None = None,
    buffer_size: int | None = None,
) -> None:
    """
    Configure the dashboard.

    Args:
        theme: Color theme - "dark" or "light"
        title: Dashboard title
        buffer_size: How many points to keep per widget (for history)

    Example:
        sv.configure(theme="dark", title="Production Metrics")
    """
    if theme is not None:
        _state.config.theme = theme
    if title is not None:
        _state.config.title = title
    if buffer_size is not None:
        _state.config.buffer_size = buffer_size

    if _state.started:
        _send_config()


def title(text: str) -> None:
    """Set the dashboard title."""
    _state.config.title = text
    if _state.started:
        _send_config()


# =============================================================================
# Public API - Widgets
# =============================================================================


def metric(
    id: str,
    *,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    max_points: int = 200,
    window: str | None = None,
    aggregation: str | Aggregation | None = None,
) -> Metric:
    """
    Create a streaming metric (time-series chart).

    Args:
        id: Unique identifier
        title: Display title (defaults to id)
        unit: Unit label (e.g., "%", "ms", "req/s")
        color: Line color (auto-assigned if not specified)
        max_points: Max points to display
        window: Aggregation window (e.g., "30s", "1m", "5m")
        aggregation: Aggregation function - "sum", "avg", "min", "max", "count", "rate"

    Returns:
        Metric object with .send() method

    Examples:
        # Simple metric - every value shown
        cpu = sv.metric("cpu", title="CPU Usage", unit="%")
        cpu.send(75.5)

        # Windowed count - count events per minute
        orders = sv.metric("orders", title="Orders/min", window="1m", aggregation="count")
        orders.send(1)  # Call for each order

        # Windowed average - average over window
        latency = sv.metric("latency", title="Avg Latency", window="30s", aggregation="avg")
        latency.send(42.5)

        # Rate - events per second
        rps = sv.metric("rps", title="Requests/sec", window="1s", aggregation="rate")
        rps.send(1)  # Call for each request
    """
    if id in _state.widgets:
        # Return existing widget
        if _state.widgets[id].get("widget_type") == "metric":
                return Metric(
                    id=id,
                    title=_state.widgets[id]["title"],
                    unit=_state.widgets[id]["unit"],
                    color=_state.widgets[id]["color"],
                    max_points=_state.widgets[id]["max_points"],
                )
        raise ValueError(f"Widget '{id}' exists with different type")

    if color is None:
        color = _next_color()

    # Set up windowed aggregation if specified
    window_secs = _parse_window(window)
    agg = _parse_aggregation(aggregation)
    has_window = False

    if window_secs is not None and agg != Aggregation.NONE:
        _state._windows[id] = TumblingWindow(window_secs, agg)
        has_window = True

    m = Metric(
        id=id,
        title=title or id,
        unit=unit,
        color=color,
        max_points=max_points,
        _has_window=has_window,
    )

    _add_widget(
        id,
        {
            "widget_type": "metric",
            "id": id,
            "title": m.title,
            "unit": unit,
            "color": color,
            "max_points": max_points,
            "window": window,
            "aggregation": agg.value if agg != Aggregation.NONE else None,
        },
    )

    return m


def stat(
    id: str,
    *,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    show_delta: bool = True,
) -> Stat:
    """
    Create a big number statistic display.

    Args:
        id: Unique identifier
        title: Display title
        unit: Unit label
        color: Text color
        show_delta: Show change from previous value

    Returns:
        Stat object with .send() method

    Example:
        total = sv.stat("total_orders", title="Total Orders")
        total.send(1523)  # Shows: 1523
        total.send(1547)  # Shows: 1547 (+24)
    """
    if id in _state.widgets:
        raise ValueError(f"Widget '{id}' already exists")

    if color is None:
        color = _next_color()

    s = Stat(id=id, title=title or id, unit=unit, color=color)

    _add_widget(
        id,
        {
            "widget_type": "stat",
            "id": id,
            "title": s.title,
            "unit": unit,
            "color": color,
            "show_delta": show_delta,
        },
    )

    return s


def gauge(
    id: str,
    *,
    title: str | None = None,
    unit: str = "",
    min_val: float = 0,
    max_val: float = 100,
    color: str | None = None,
    thresholds: list[tuple[float, str]] | None = None,
) -> Gauge:
    """
    Create a circular gauge for bounded values.

    Args:
        id: Unique identifier
        title: Display title
        unit: Unit label
        min_val: Minimum scale value
        max_val: Maximum scale value
        color: Default color
        thresholds: List of (value, color) for color zones

    Returns:
        Gauge object with .send() method

    Example:
        cpu = sv.gauge("cpu_gauge", title="CPU", max_val=100, unit="%",
                       thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])
        cpu.send(72)
    """
    if id in _state.widgets:
        raise ValueError(f"Widget '{id}' already exists")

    if color is None:
        color = _next_color()
    if thresholds is None:
        thresholds = [(max_val, color)]

    g = Gauge(
        id=id,
        title=title or id,
        unit=unit,
        min_val=min_val,
        max_val=max_val,
        color=color,
        thresholds=thresholds,
    )

    _add_widget(
        id,
        {
            "widget_type": "gauge",
            "id": id,
            "title": g.title,
            "unit": unit,
            "min": min_val,
            "max": max_val,
            "color": color,
            "thresholds": thresholds,
        },
    )

    return g


def table(
    id: str,
    *,
    title: str | None = None,
    columns: list[str] | list[dict] | None = None,
    max_rows: int = 50,
) -> Table:
    """
    Create a streaming table.

    Args:
        id: Unique identifier
        title: Table title
        columns: Column definitions - list of names or list of {name, label, type}
        max_rows: Maximum rows to display

    Returns:
        Table object with .send() method

    Example:
        logs = sv.table("logs", title="Recent Events",
                        columns=["timestamp", "level", "message"])
        logs.send({"timestamp": "12:34:56", "level": "ERROR", "message": "Failed"})
    """
    if id in _state.widgets:
        raise ValueError(f"Widget '{id}' already exists")

    # Normalize columns
    if columns is None:
        columns = []
    elif columns and isinstance(columns[0], str):
        columns = [{"name": c, "label": c} for c in columns]

    t = Table(id=id, title=title or id, columns=columns, max_rows=max_rows)

    _add_widget(
        id,
        {
            "widget_type": "table",
            "id": id,
            "title": t.title,
            "columns": columns,
            "max_rows": max_rows,
        },
    )

    return t


def text(id: str, initial: str = "", *, style: str = "body") -> Callable[[str], None]:
    """
    Create a text element.

    Args:
        id: Unique identifier
        initial: Initial text
        style: Text style - "title", "header", "body", "caption", "code"

    Returns:
        Function to update the text

    Example:
        status = sv.text("status", "Starting...", style="caption")
        status("Connected to Kafka")
    """
    if id in _state.widgets:
        raise ValueError(f"Widget '{id}' already exists")

    _add_widget(
        id,
        {
            "widget_type": "text",
            "id": id,
            "value": initial,
            "style": style,
        },
    )

    def update(new_text: str) -> None:
        msg = {
            "type": "data",
            "widget": id,
            "value": new_text,
        }
        _send_data(json.dumps(msg))
        _state.widgets[id]["value"] = new_text

    return update


# =============================================================================
# Public API - Layout
# =============================================================================


class _LayoutContext:
    """Context manager for layout containers."""

    def __init__(self, layout_type: str, options: dict):
        self.layout_type = layout_type
        self.options = options
        self.children: list = []
        self._original_layout: list = []

    def __enter__(self):
        # Save current layout to restore later
        self._original_layout = _state.layout.copy()
        _state.layout = self.children
        return self

    def __exit__(self, *args):
        # Restore layout and add this container
        container = {
            "type": self.layout_type,
            "children": self.children,
            **self.options,
        }
        _state.layout = self._original_layout
        _state.layout.append(container)

        if _state.started:
            _send_config()


def columns(count: int = 2) -> _LayoutContext:
    """
    Create a column layout.

    Widgets inside are arranged in columns.

    Example:
        with sv.columns(2):
            sv.metric("cpu")
            sv.metric("memory")
    """
    return _LayoutContext("columns", {"count": count})


def row() -> _LayoutContext:
    """
    Create a row layout.

    Widgets inside are arranged horizontally.

    Example:
        with sv.row():
            sv.stat("total")
            sv.stat("average")
    """
    return _LayoutContext("row", {})


# =============================================================================
# Public API - Server Control
# =============================================================================


def _config_broadcaster() -> None:
    """Background thread that periodically re-sends config."""
    while _state.started:
        time.sleep(2.0)
        if _state.widgets:
            _send_config()


def start(port: int = 3000) -> None:
    """
    Start the StreamViz server.

    The server runs in a background thread. After calling this,
    use widget.send() to push data.

    Args:
        port: Port to listen on (default: 3000)

    Example:
        sv.title("My Dashboard")
        cpu = sv.metric("cpu")

        sv.start()

        while True:
            cpu.send(get_cpu())
            time.sleep(0.1)
    """
    _state.config.port = port
    _start_server(port)
    _state.started = True
    time.sleep(0.3)  # Give server time to start

    _send_config()

    # Background config broadcaster
    t = threading.Thread(target=_config_broadcaster, daemon=True)
    t.start()

    print(f"Dashboard: http://localhost:{port}")


def run_demo(port: int = 3000) -> None:
    """
    Run the built-in demo showing various widget types.

    This blocks forever.
    """
    import math
    import random

    title("StreamViz Demo")

    # Gauges for at-a-glance status
    cpu_g = gauge(
        "cpu_gauge",
        title="CPU",
        unit="%",
        max_val=100,
        thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")],
    )
    mem_g = gauge(
        "mem_gauge",
        title="Memory",
        unit="%",
        max_val=100,
        thresholds=[(60, "#00ff88"), (85, "#ffd93d"), (100, "#ff6b6b")],
    )

    # Stats for key numbers
    total_reqs = stat("total_reqs", title="Total Requests")
    error_rate = stat("error_rate", title="Error Rate", unit="%")

    # Time series
    cpu_ts = metric("cpu_ts", title="CPU History", unit="%")

    # Windowed aggregations
    rps = metric("rps", title="Requests/sec", window="1s", aggregation="rate")
    latency_avg = metric(
        "latency_avg", title="Avg Latency (5s)", unit="ms", window="5s", aggregation="avg"
    )
    errors_min = metric(
        "errors_min", title="Errors/min", window="1m", aggregation="count", color="#ff6b6b"
    )

    # Table for events
    events = table(
        "events", title="Recent Events", columns=["time", "level", "message"], max_rows=10
    )

    start(port)

    i = 0
    total = 0
    base_mem = 50.0

    event_templates = [
        ("INFO", "Request processed"),
        ("INFO", "Cache hit"),
        ("DEBUG", "Query completed"),
        ("WARN", "High latency"),
        ("ERROR", "Connection failed"),
    ]

    try:
        while True:
            now_str = time.strftime("%H:%M:%S")

            # CPU oscillation
            cpu_val = 50 + 30 * math.sin(i * 0.05) + random.gauss(0, 5)
            cpu_val = max(0, min(100, cpu_val))
            cpu_ts.send(cpu_val)
            cpu_g.send(cpu_val)

            # Memory drift
            base_mem += random.gauss(0.01, 0.1)
            if base_mem > 85:
                base_mem = 50
            mem_g.send(max(0, min(100, base_mem + random.gauss(0, 2))))

            # Simulate requests (for rate calculation)
            for _ in range(random.randint(8, 15)):
                rps.send(1)
                total += 1

            # Latency samples
            for _ in range(random.randint(1, 5)):
                if random.random() < 0.05:
                    latency_avg.send(random.uniform(100, 300))
                else:
                    latency_avg.send(15 + abs(random.gauss(0, 10)))

            # Occasional errors
            if random.random() < 0.02:
                errors_min.send(1)

            # Update stats periodically
            if i % 20 == 0:
                total_reqs.send(total)
                error_rate.send(random.uniform(0.1, 2.0))

            # Random events
            if random.random() < 0.1:
                level, msg = random.choice(event_templates)
                events.send({"time": now_str, "level": level, "message": msg})

            time.sleep(0.05)
            i += 1

    except KeyboardInterrupt:
        print("\nDemo stopped.")


# =============================================================================
# Pathway Integration
# =============================================================================

# Type alias for Pathway table (optional import)
try:
    import pathway as pw

    _PATHWAY_AVAILABLE = True
except ImportError:
    pw = None  # type: ignore
    _PATHWAY_AVAILABLE = False


def pathway_table(
    table: Any,
    *,
    title: str | None = None,
    columns: list[str] | None = None,
    column_config: dict[str, dict] | None = None,
    max_rows: int = 100,
    sort_by: str | None = None,
    sort_desc: bool = True,
) -> None:
    """
    Visualize a Pathway table with live updates.

    As the Pathway table updates (inserts, updates, deletes), the dashboard
    table updates in real-time. Rows are keyed by Pathway's internal ID.

    Args:
        table: A Pathway Table object
        title: Display title
        columns: Which columns to show (None = all)
        column_config: Per-column formatting config
        max_rows: Maximum rows to display
        sort_by: Column to sort by
        sort_desc: Sort descending

    Example:
        stats = orders.groupby(pw.this.region).reduce(
            total=pw.reducers.sum(pw.this.amount),
            count=pw.reducers.count(),
        )
        sv.pathway_table(stats, title="Orders by Region")
    """
    if not _PATHWAY_AVAILABLE:
        raise ImportError(
            "Pathway is required for pathway_table(). "
            "Install with: pip install pathway"
        )

    widget_id = f"pw_table_{id(table)}"

    # Infer columns from table schema if not provided
    if columns is None:
        schema = table.schema
        columns = [name for name in schema.keys() if not name.startswith("_")]

    # Build column config
    cols = []
    for col in columns:
        config = {"name": col}
        if column_config and col in column_config:
            config.update(column_config[col])
        cols.append(config)

    # Register widget
    _state.widgets[widget_id] = {
        "widget_type": "pathway_table",
        "title": title or "Pathway Table",
        "columns": cols,
        "max_rows": max_rows,
        "sort_by": sort_by,
        "sort_desc": sort_desc,
    }
    if _state.started:
        _send_config()

    # Subscribe to table changes
    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if is_addition:
            # Filter to requested columns
            filtered = {c: row.get(c) for c in columns}
            _send_data(
                json.dumps(
                    {
                        "type": "data",
                        "widget": widget_id,
                        "op": "upsert",
                        "key": str(key),
                        "row": filtered,
                    }
                )
            )
        else:
            _send_data(
                json.dumps(
                    {
                        "type": "data",
                        "widget": widget_id,
                        "op": "delete",
                        "key": str(key),
                    }
                )
            )

    pw.io.subscribe(table, on_change=on_change)


def pathway_stat(
    table: Any,
    column: str,
    *,
    title: str | None = None,
    unit: str = "",
    format_str: str | None = None,
    delta: bool = True,
    color: str | None = None,
) -> None:
    """
    Display a single value from a Pathway table as a stat widget.

    Best used with single-row reductions:
        totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
        sv.pathway_stat(totals, column="revenue", title="Revenue", unit="$")

    Args:
        table: A Pathway Table (typically single-row)
        column: Which column to display
        title: Display title
        unit: Unit suffix
        format_str: Python format string for the value
        delta: Show change from previous value
        color: Hex color
    """
    if not _PATHWAY_AVAILABLE:
        raise ImportError(
            "Pathway is required for pathway_stat(). "
            "Install with: pip install pathway"
        )

    widget_id = f"pw_stat_{column}_{id(table)}"
    last_value: list[float | None] = [None]

    _state.widgets[widget_id] = {
        "widget_type": "stat",
        "title": title or column,
        "unit": unit,
        "color": color or _next_color(),
    }
    if _state.started:
        _send_config()

    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if is_addition and column in row:
            value = row[column]
            delta_val = None
            if delta and last_value[0] is not None:
                delta_val = value - last_value[0]
            last_value[0] = value

            _send_data(
                json.dumps(
                    {
                        "type": "data",
                        "widget": widget_id,
                        "value": value,
                        "delta": delta_val,
                        "timestamp": int(time * 1000),
                    }
                )
            )

    pw.io.subscribe(table, on_change=on_change)


def pathway_metric(
    table: Any,
    value_column: str,
    *,
    time_column: str | None = None,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    max_points: int = 200,
) -> None:
    """
    Display a Pathway windowed aggregation as a time series chart.

    Best used with windowby() aggregations:
        per_minute = events.windowby(
            pw.this.timestamp,
            window=pw.temporal.tumbling(duration=timedelta(minutes=1))
        ).reduce(count=pw.reducers.count())

        sv.pathway_metric(per_minute,
            time_column="window_end",
            value_column="count",
            title="Events/min"
        )

    Args:
        table: A Pathway Table with windowed data
        value_column: Column containing the metric value
        time_column: Column containing the timestamp (window_end recommended)
        title: Display title
        unit: Unit suffix
        color: Hex color
        max_points: Max points to display
    """
    if not _PATHWAY_AVAILABLE:
        raise ImportError(
            "Pathway is required for pathway_metric(). "
            "Install with: pip install pathway"
        )

    widget_id = f"pw_metric_{value_column}_{id(table)}"

    _state.widgets[widget_id] = {
        "widget_type": "metric",
        "title": title or value_column,
        "unit": unit,
        "color": color or _next_color(),
        "max_points": max_points,
    }
    if _state.started:
        _send_config()

    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if is_addition and value_column in row:
            value = row[value_column]

            # Use time_column if provided, otherwise use Pathway's time
            if time_column and time_column in row:
                ts = row[time_column]
                # Convert to milliseconds if it's a datetime
                if hasattr(ts, "timestamp"):
                    ts = int(ts.timestamp() * 1000)
                elif isinstance(ts, int | float):
                    # Assume already in appropriate format
                    ts = int(ts * 1000) if ts < 1e12 else int(ts)
            else:
                ts = int(time * 1000)

            _send_data(
                json.dumps(
                    {
                        "type": "data",
                        "widget": widget_id,
                        "value": value,
                        "timestamp": ts,
                    }
                )
            )

    pw.io.subscribe(table, on_change=on_change)


# =============================================================================
# Low-Level API
# =============================================================================


def send_json(data: dict[str, Any]) -> None:
    """
    Send arbitrary JSON to all clients.

    For standard widgets, use the widget API instead.
    """
    _send_data(json.dumps(data))
