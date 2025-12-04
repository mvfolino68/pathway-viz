"""
StreamViz - The visualization layer for Pathway.

Real-time dashboards and embeddable widgets for Pathway streaming pipelines.

Example (Dashboard):
    import pathway as pw
    import stream_viz as sv

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
import threading
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

from ._stream_viz import send_data as _send_data
from ._stream_viz import start_server as _start_server

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
    # Utilities
    "send_json",
    "run_demo",
]


# =============================================================================
# Type Definitions
# =============================================================================

# Pathway types (optional import)
try:
    import pathway as pw
    from pathway import Table as PathwayTable

    _PATHWAY_AVAILABLE = True
except ImportError:
    pw = None  # type: ignore
    PathwayTable = Any  # type: ignore
    _PATHWAY_AVAILABLE = False

T = TypeVar("T")


# =============================================================================
# Dashboard State
# =============================================================================


@dataclass
class Config:
    """Dashboard configuration."""

    title: str = "StreamViz"
    theme: str = "dark"
    port: int = 3000
    embed_enabled: bool = False


@dataclass
class DashboardState:
    """Global dashboard state."""

    config: Config = field(default_factory=Config)
    widgets: dict[str, dict] = field(default_factory=dict)
    layout: list = field(default_factory=list)
    started: bool = False
    _color_index: int = 0
    _subscriptions: list = field(default_factory=list)  # Track Pathway subscriptions


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
    """Get next color from palette."""
    color = _COLORS[_state._color_index % len(_COLORS)]
    _state._color_index += 1
    return color


def _send_config() -> None:
    """Broadcast dashboard config to all clients."""
    msg = {
        "type": "config",
        "title": _state.config.title,
        "theme": _state.config.theme,
        "widgets": _state.widgets,
        "layout": _state.layout,
        "embed_enabled": _state.config.embed_enabled,
    }
    _send_data(json.dumps(msg))


def _register_widget(widget_id: str, widget_config: dict) -> None:
    """Register a widget in the dashboard."""
    _state.widgets[widget_id] = widget_config
    if widget_id not in _state.layout:
        _state.layout.append(widget_id)
    if _state.started:
        _send_config()


# =============================================================================
# Configuration API
# =============================================================================


def configure(
    *,
    title: str | None = None,
    theme: str | None = None,
    port: int | None = None,
    embed: bool | None = None,
) -> None:
    """
    Configure the dashboard.

    Args:
        title: Dashboard title
        theme: Color theme ("dark" or "light")
        port: Server port (default: 3000)
        embed: Enable embeddable widget endpoints

    Example:
        sv.configure(title="Analytics", embed=True)
    """
    if title is not None:
        _state.config.title = title
    if theme is not None:
        _state.config.theme = theme
    if port is not None:
        _state.config.port = port
    if embed is not None:
        _state.config.embed_enabled = embed

    if _state.started:
        _send_config()


def title(text: str) -> None:
    """Set dashboard title."""
    _state.config.title = text
    if _state.started:
        _send_config()


# =============================================================================
# Core Widget API - Pathway First
# =============================================================================


def _is_pathway_table(obj: Any) -> bool:
    """Check if an object is a Pathway Table."""
    if not _PATHWAY_AVAILABLE:
        return False
    return hasattr(obj, "__class__") and "pathway" in str(type(obj).__module__)


def _get_table_columns(pw_table: Any) -> list[str]:
    """Extract column names from Pathway table schema."""
    schema = pw_table.schema
    return [name for name in schema.keys() if not name.startswith("_")]


def table(
    source: Any,
    *,
    id: str | None = None,
    title: str | None = None,
    columns: list[str] | None = None,
    column_labels: dict[str, str] | None = None,
    column_format: dict[str, str] | None = None,
    max_rows: int = 100,
    sort_by: str | None = None,
    sort_desc: bool = True,
    embed: bool = False,
) -> _ManualTable | None:
    """
    Display a table widget.

    Accepts either:
    - A Pathway Table (auto-subscribes and updates live)
    - A string ID (for manual .send() usage)

    Args:
        source: Pathway Table or widget ID string
        id: Widget identifier (auto-generated if not provided)
        title: Display title
        columns: Which columns to display (all if None)
        column_labels: Display labels for columns {"col_name": "Display Name"}
        column_format: Format strings for columns {"amount": "$,.2f"}
        max_rows: Maximum rows to show
        sort_by: Column to sort by
        sort_desc: Sort descending
        embed: Enable embeddable endpoint at /embed/{id}

    Returns:
        For manual mode (string source): _ManualTable with .send() method
        For Pathway mode: None (subscription is automatic)

    Example (Pathway):
        stats = orders.groupby(pw.this.region).reduce(...)
        sv.table(stats, title="By Region", columns=["region", "revenue"])

    Example (Manual):
        events = sv.table("events", title="Events", columns=["time", "msg"])
        events.send({"time": "12:00", "msg": "Started"})
    """
    # Pathway mode
    if _is_pathway_table(source):
        return _table_pathway(
            source,
            id=id,
            title=title,
            columns=columns,
            column_labels=column_labels,
            column_format=column_format,
            max_rows=max_rows,
            sort_by=sort_by,
            sort_desc=sort_desc,
            embed=embed,
        )

    # Manual mode (source is widget ID)
    if not isinstance(source, str):
        raise TypeError(
            f"table() expects a Pathway Table or string ID, got {type(source).__name__}"
        )

    return _table_manual(
        source,
        title=title,
        columns=columns,
        column_labels=column_labels,
        max_rows=max_rows,
        embed=embed,
    )


def _table_pathway(
    pw_table: Any,
    *,
    id: str | None,
    title: str | None,
    columns: list[str] | None,
    column_labels: dict[str, str] | None,
    column_format: dict[str, str] | None,
    max_rows: int,
    sort_by: str | None,
    sort_desc: bool,
    embed: bool,
) -> None:
    """Subscribe to a Pathway table and display as live-updating table."""
    if not _PATHWAY_AVAILABLE:
        raise ImportError("Pathway is required. Install with: pip install pathway")

    widget_id = id or f"pw_table_{len(_state.widgets)}"

    # Infer columns from schema
    if columns is None:
        columns = _get_table_columns(pw_table)

    # Build column config
    cols = []
    for col in columns:
        config = {
            "name": col,
            "label": (column_labels or {}).get(col, col),
        }
        if column_format and col in column_format:
            config["format"] = column_format[col]
        cols.append(config)

    _register_widget(
        widget_id,
        {
            "widget_type": "pathway_table",
            "title": title or "Table",
            "columns": cols,
            "max_rows": max_rows,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "embed": embed,
        },
    )

    # Subscribe to Pathway table changes
    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        filtered_row = {c: row.get(c) for c in columns}

        if is_addition:
            _send_data(
                json.dumps(
                    {
                        "type": "data",
                        "widget": widget_id,
                        "op": "upsert",
                        "key": str(key),
                        "row": filtered_row,
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

    pw.io.subscribe(pw_table, on_change=on_change)


@dataclass
class _ManualTable:
    """Manual table widget for non-Pathway use."""

    id: str
    columns: list[str]

    def send(self, row: dict[str, Any]) -> None:
        """Add a row to the table."""
        _send_data(
            json.dumps(
                {
                    "type": "data",
                    "widget": self.id,
                    "row": row,
                    "timestamp": int(time.time() * 1000),
                }
            )
        )


def _table_manual(
    widget_id: str,
    *,
    title: str | None,
    columns: list[str] | None,
    column_labels: dict[str, str] | None,
    max_rows: int,
    embed: bool,
) -> _ManualTable:
    """Create a manual table widget."""
    columns = columns or []
    cols = [{"name": c, "label": (column_labels or {}).get(c, c)} for c in columns]

    _register_widget(
        widget_id,
        {
            "widget_type": "table",
            "title": title or widget_id,
            "columns": cols,
            "max_rows": max_rows,
            "embed": embed,
        },
    )

    return _ManualTable(id=widget_id, columns=columns)


def stat(
    source: Any,
    column: str | None = None,
    *,
    id: str | None = None,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    format: str | None = None,
    delta: bool = True,
    embed: bool = False,
) -> _ManualStat | None:
    """
    Display a single value as a prominent statistic.

    For Pathway: Displays a column from a single-row table (e.g., from reduce()).
    For Manual: Returns an object with .send() method.

    Args:
        source: Pathway Table or widget ID string
        column: Column to display (required for Pathway mode)
        id: Widget identifier
        title: Display title
        unit: Unit suffix (e.g., "$", "%", "ms")
        color: Text color
        format: Python format string (e.g., ",.2f")
        delta: Show change from previous value
        embed: Enable embeddable endpoint

    Example (Pathway):
        totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
        sv.stat(totals, "revenue", title="Revenue", unit="$")

    Example (Manual):
        visitors = sv.stat("visitors", title="Active Visitors")
        visitors.send(1234)
    """
    if _is_pathway_table(source):
        if column is None:
            raise ValueError("column is required for Pathway tables")
        return _stat_pathway(
            source,
            column,
            id=id,
            title=title,
            unit=unit,
            color=color,
            format=format,
            delta=delta,
            embed=embed,
        )

    if not isinstance(source, str):
        raise TypeError(f"stat() expects Pathway Table or string ID, got {type(source).__name__}")

    return _stat_manual(
        source,
        title=title,
        unit=unit,
        color=color,
        delta=delta,
        embed=embed,
    )


def _stat_pathway(
    pw_table: Any,
    column: str,
    *,
    id: str | None,
    title: str | None,
    unit: str,
    color: str | None,
    format: str | None,
    delta: bool,
    embed: bool,
) -> None:
    """Display a Pathway column as a stat widget."""
    if not _PATHWAY_AVAILABLE:
        raise ImportError("Pathway required")

    widget_id = id or f"stat_{column}_{len(_state.widgets)}"
    color = color or _next_color()
    last_value: list[float | None] = [None]

    _register_widget(
        widget_id,
        {
            "widget_type": "stat",
            "title": title or column,
            "unit": unit,
            "color": color,
            "format": format,
            "embed": embed,
        },
    )

    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if not is_addition or column not in row:
            return

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

    pw.io.subscribe(pw_table, on_change=on_change)


@dataclass
class _ManualStat:
    """Manual stat widget."""

    id: str
    _last_value: float | None = None
    _show_delta: bool = True

    def send(self, value: float) -> None:
        """Update the stat value."""
        delta = None
        if self._show_delta and self._last_value is not None:
            delta = value - self._last_value
        self._last_value = value

        _send_data(
            json.dumps(
                {
                    "type": "data",
                    "widget": self.id,
                    "value": value,
                    "delta": delta,
                    "timestamp": int(time.time() * 1000),
                }
            )
        )


def _stat_manual(
    widget_id: str,
    *,
    title: str | None,
    unit: str,
    color: str | None,
    delta: bool,
    embed: bool,
) -> _ManualStat:
    """Create a manual stat widget."""
    _register_widget(
        widget_id,
        {
            "widget_type": "stat",
            "title": title or widget_id,
            "unit": unit,
            "color": color or _next_color(),
            "embed": embed,
        },
    )

    return _ManualStat(id=widget_id, _show_delta=delta)


def chart(
    source: Any,
    y_column: str | None = None,
    *,
    x_column: str | None = None,
    id: str | None = None,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    chart_type: str = "line",
    max_points: int = 200,
    embed: bool = False,
) -> _ManualChart | None:
    """
    Display a time series chart.

    For Pathway: Best with windowby() aggregations.
    For Manual: Returns object with .send() method.

    Args:
        source: Pathway Table or widget ID string
        y_column: Value column (required for Pathway)
        x_column: Time column (uses window_end or Pathway time if not specified)
        id: Widget identifier
        title: Display title
        unit: Y-axis unit
        color: Line/fill color
        chart_type: "line" or "area"
        max_points: Max points to display
        embed: Enable embeddable endpoint

    Example (Pathway windowed):
        per_minute = orders.windowby(
            pw.this.timestamp,
            window=pw.temporal.tumbling(duration=timedelta(minutes=1))
        ).reduce(count=pw.reducers.count())

        sv.chart(per_minute, "count", x_column="window_end", title="Orders/min")

    Example (Manual):
        cpu = sv.chart("cpu", title="CPU Usage", unit="%")
        cpu.send(72.5)
    """
    if _is_pathway_table(source):
        if y_column is None:
            raise ValueError("y_column is required for Pathway tables")
        return _chart_pathway(
            source,
            y_column,
            x_column=x_column,
            id=id,
            title=title,
            unit=unit,
            color=color,
            chart_type=chart_type,
            max_points=max_points,
            embed=embed,
        )

    if not isinstance(source, str):
        raise TypeError("chart() expects Pathway Table or string ID")

    return _chart_manual(
        source,
        title=title,
        unit=unit,
        color=color,
        max_points=max_points,
        embed=embed,
    )


def _chart_pathway(
    pw_table: Any,
    y_column: str,
    *,
    x_column: str | None,
    id: str | None,
    title: str | None,
    unit: str,
    color: str | None,
    chart_type: str,
    max_points: int,
    embed: bool,
) -> None:
    """Display Pathway data as a time series chart."""
    if not _PATHWAY_AVAILABLE:
        raise ImportError("Pathway required")

    widget_id = id or f"chart_{y_column}_{len(_state.widgets)}"

    _register_widget(
        widget_id,
        {
            "widget_type": "metric",  # frontend uses "metric" for charts
            "title": title or y_column,
            "unit": unit,
            "color": color or _next_color(),
            "chart_type": chart_type,
            "max_points": max_points,
            "embed": embed,
        },
    )

    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if not is_addition or y_column not in row:
            return

        value = row[y_column]

        # Determine timestamp
        if x_column and x_column in row:
            ts = row[x_column]
            if hasattr(ts, "timestamp"):
                ts = int(ts.timestamp() * 1000)
            elif isinstance(ts, (int, float)):
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

    pw.io.subscribe(pw_table, on_change=on_change)


@dataclass
class _ManualChart:
    """Manual chart widget."""

    id: str

    def send(self, value: float, timestamp: float | None = None) -> None:
        """Add a data point to the chart."""
        ts = int(timestamp * 1000) if timestamp else int(time.time() * 1000)
        _send_data(
            json.dumps(
                {
                    "type": "data",
                    "widget": self.id,
                    "value": value,
                    "timestamp": ts,
                }
            )
        )


def _chart_manual(
    widget_id: str,
    *,
    title: str | None,
    unit: str,
    color: str | None,
    max_points: int,
    embed: bool,
) -> _ManualChart:
    """Create a manual chart widget."""
    _register_widget(
        widget_id,
        {
            "widget_type": "metric",
            "title": title or widget_id,
            "unit": unit,
            "color": color or _next_color(),
            "max_points": max_points,
            "embed": embed,
        },
    )

    return _ManualChart(id=widget_id)


def gauge(
    source: Any,
    column: str | None = None,
    *,
    id: str | None = None,
    title: str | None = None,
    unit: str = "",
    min_val: float = 0,
    max_val: float = 100,
    color: str | None = None,
    thresholds: list[tuple[float, str]] | None = None,
    embed: bool = False,
) -> _ManualGauge | None:
    """
    Display a circular gauge for bounded values.

    Great for percentages, utilization metrics, or any bounded value.

    Args:
        source: Pathway Table or widget ID string
        column: Column to display (required for Pathway)
        id: Widget identifier
        title: Display title
        unit: Unit suffix
        min_val: Minimum scale value
        max_val: Maximum scale value
        color: Gauge color
        thresholds: Color zones as [(value, color), ...]
        embed: Enable embeddable endpoint

    Example (Pathway):
        system_stats = ...reduce(cpu=pw.reducers.avg(pw.this.cpu_pct))
        sv.gauge(system_stats, "cpu", title="CPU", max_val=100, unit="%",
                 thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])

    Example (Manual):
        cpu = sv.gauge("cpu", title="CPU", max_val=100, unit="%")
        cpu.send(72)
    """
    if _is_pathway_table(source):
        if column is None:
            raise ValueError("column is required for Pathway tables")
        return _gauge_pathway(
            source,
            column,
            id=id,
            title=title,
            unit=unit,
            min_val=min_val,
            max_val=max_val,
            color=color,
            thresholds=thresholds,
            embed=embed,
        )

    if not isinstance(source, str):
        raise TypeError("gauge() expects Pathway Table or string ID")

    return _gauge_manual(
        source,
        title=title,
        unit=unit,
        min_val=min_val,
        max_val=max_val,
        color=color,
        thresholds=thresholds,
        embed=embed,
    )


def _gauge_pathway(
    pw_table: Any,
    column: str,
    *,
    id: str | None,
    title: str | None,
    unit: str,
    min_val: float,
    max_val: float,
    color: str | None,
    thresholds: list[tuple[float, str]] | None,
    embed: bool,
) -> None:
    """Display Pathway column as a gauge."""
    if not _PATHWAY_AVAILABLE:
        raise ImportError("Pathway required")

    widget_id = id or f"gauge_{column}_{len(_state.widgets)}"
    color = color or _next_color()

    _register_widget(
        widget_id,
        {
            "widget_type": "gauge",
            "title": title or column,
            "unit": unit,
            "min": min_val,
            "max": max_val,
            "color": color,
            "thresholds": thresholds or [(max_val, color)],
            "embed": embed,
        },
    )

    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if not is_addition or column not in row:
            return

        _send_data(
            json.dumps(
                {
                    "type": "data",
                    "widget": widget_id,
                    "value": row[column],
                    "timestamp": int(time * 1000),
                }
            )
        )

    pw.io.subscribe(pw_table, on_change=on_change)


@dataclass
class _ManualGauge:
    """Manual gauge widget."""

    id: str

    def send(self, value: float) -> None:
        """Update the gauge value."""
        _send_data(
            json.dumps(
                {
                    "type": "data",
                    "widget": self.id,
                    "value": value,
                    "timestamp": int(time.time() * 1000),
                }
            )
        )


def _gauge_manual(
    widget_id: str,
    *,
    title: str | None,
    unit: str,
    min_val: float,
    max_val: float,
    color: str | None,
    thresholds: list[tuple[float, str]] | None,
    embed: bool,
) -> _ManualGauge:
    """Create a manual gauge widget."""
    color = color or _next_color()

    _register_widget(
        widget_id,
        {
            "widget_type": "gauge",
            "title": title or widget_id,
            "unit": unit,
            "min": min_val,
            "max": max_val,
            "color": color,
            "thresholds": thresholds or [(max_val, color)],
            "embed": embed,
        },
    )

    return _ManualGauge(id=widget_id)


# =============================================================================
# Server Control
# =============================================================================


def _config_broadcaster() -> None:
    """Periodically broadcast config to catch new connections."""
    while _state.started:
        time.sleep(2.0)
        if _state.widgets:
            _send_config()


def start(port: int | None = None) -> None:
    """
    Start the StreamViz server.

    Args:
        port: Port to listen on (default: 3000)

    After calling start(), data flows automatically from Pathway subscriptions.
    For manual widgets, use widget.send() to push data.

    Example:
        sv.table(my_pathway_table, title="Data")
        sv.start()
        pw.run()  # Pathway drives the data flow
    """
    if port is not None:
        _state.config.port = port

    _start_server(_state.config.port)
    _state.started = True
    time.sleep(0.3)  # Let server start

    _send_config()

    # Background broadcaster
    t = threading.Thread(target=_config_broadcaster, daemon=True)
    t.start()

    dashboard_url = f"http://localhost:{_state.config.port}"
    print(f"Dashboard: {dashboard_url}")

    if _state.config.embed_enabled:
        print(f"Embed widgets: {dashboard_url}/embed/{{widget_id}}")


# =============================================================================
# Demo
# =============================================================================


def run_demo(port: int = 3000) -> None:
    """
    Run a demo showing all widget types.

    This runs without Pathway, using manual .send() calls.
    """
    import math
    import random

    title("StreamViz Demo")

    # Gauges
    cpu_gauge = gauge(
        "cpu",
        title="CPU",
        unit="%",
        max_val=100,
        thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")],
    )
    mem_gauge = gauge(
        "memory",
        title="Memory",
        unit="%",
        max_val=100,
        thresholds=[(60, "#00ff88"), (85, "#ffd93d"), (100, "#ff6b6b")],
    )

    # Stats
    total_stat = stat("total", title="Total Requests")
    error_stat = stat("errors", title="Error Rate", unit="%")

    # Charts
    cpu_chart = chart("cpu_history", title="CPU History", unit="%")
    latency_chart = chart("latency", title="Latency", unit="ms")

    # Table
    events = table("events", title="Recent Events", columns=["time", "level", "message"])

    start(port)

    total = 0
    i = 0

    event_templates = [
        ("INFO", "Request processed"),
        ("INFO", "Cache hit"),
        ("DEBUG", "Query completed"),
        ("WARN", "High latency detected"),
        ("ERROR", "Connection failed"),
    ]

    try:
        while True:
            now_str = time.strftime("%H:%M:%S")

            # CPU oscillation
            cpu = 50 + 30 * math.sin(i * 0.05) + random.gauss(0, 5)
            cpu = max(0, min(100, cpu))
            cpu_gauge.send(cpu)
            cpu_chart.send(cpu)

            # Memory drift
            mem = 50 + 20 * math.sin(i * 0.02) + random.gauss(0, 3)
            mem = max(0, min(100, mem))
            mem_gauge.send(mem)

            # Latency
            if random.random() < 0.05:
                latency_chart.send(random.uniform(100, 300))
            else:
                latency_chart.send(15 + abs(random.gauss(0, 10)))

            # Stats
            total += random.randint(5, 15)
            if i % 10 == 0:
                total_stat.send(total)
                error_stat.send(random.uniform(0.1, 3.0))

            # Events
            if random.random() < 0.15:
                level, msg = random.choice(event_templates)
                events.send({"time": now_str, "level": level, "message": msg})

            time.sleep(0.1)
            i += 1

    except KeyboardInterrupt:
        print("\nDemo stopped.")


# =============================================================================
# Low-Level API
# =============================================================================


def send_json(data: dict[str, Any]) -> None:
    """
    Send arbitrary JSON to all connected clients.

    For standard widgets, use the widget API instead.
    """
    _send_data(json.dumps(data))


# =============================================================================
# Legacy Compatibility - Pathway-prefixed functions
# =============================================================================


def pathway_table(
    pw_table: Any,
    *,
    title: str | None = None,
    columns: list[str] | None = None,
    column_config: dict[str, dict] | None = None,
    max_rows: int = 100,
    sort_by: str | None = None,
    sort_desc: bool = True,
) -> None:
    """DEPRECATED: Use table() instead."""
    return table(
        pw_table,
        title=title,
        columns=columns,
        column_labels={k: v.get("label", k) for k, v in (column_config or {}).items()},
        max_rows=max_rows,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


def pathway_stat(
    pw_table: Any,
    column: str,
    *,
    title: str | None = None,
    unit: str = "",
    format_str: str | None = None,
    delta: bool = True,
    color: str | None = None,
) -> None:
    """DEPRECATED: Use stat() instead."""
    return stat(
        pw_table,
        column,
        title=title,
        unit=unit,
        format=format_str,
        delta=delta,
        color=color,
    )


def pathway_metric(
    pw_table: Any,
    value_column: str,
    *,
    time_column: str | None = None,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    max_points: int = 200,
) -> None:
    """DEPRECATED: Use chart() instead."""
    return chart(
        pw_table,
        value_column,
        x_column=time_column,
        title=title,
        unit=unit,
        color=color,
        max_points=max_points,
    )


# Legacy standalone widget functions (for backward compat)
def metric(
    id: str,
    *,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    max_points: int = 200,
    **kwargs,  # Ignore legacy window/aggregation args
) -> _ManualChart:
    """DEPRECATED: Use chart() instead."""
    return chart(id, title=title, unit=unit, color=color, max_points=max_points)
