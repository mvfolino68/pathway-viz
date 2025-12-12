"""
Widget implementations for PathwayViz.

Provides table, stat, chart, and gauge widgets with both Pathway and manual modes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from ._pathway_viz import send_data as _send_data
from ._state import get_state, next_color

# Pathway types (optional import)
try:
    import pathway as pw
    from pathway import Table as PathwayTable

    _PATHWAY_AVAILABLE = True
except ImportError:
    pw = None  # type: ignore
    PathwayTable = Any  # type: ignore
    _PATHWAY_AVAILABLE = False


def _send_config() -> None:
    """Broadcast dashboard config to all clients."""
    state = get_state()
    msg = {
        "type": "config",
        "title": state.config.title,
        "theme": state.config.theme,
        "widgets": state.widgets,
        "layout": state.layout,
        "embed_enabled": state.config.embed_enabled,
    }
    _send_data(json.dumps(msg))


def _register_widget(widget_id: str, widget_config: dict) -> None:
    """Register a widget in the dashboard."""
    state = get_state()
    state.widgets[widget_id] = widget_config
    if widget_id not in state.layout:
        state.layout.append(widget_id)
    if state.started:
        _send_config()


def _is_pathway_table(obj: Any) -> bool:
    """Check if an object is a Pathway Table."""
    if not _PATHWAY_AVAILABLE:
        return False
    return hasattr(obj, "__class__") and "pathway" in str(type(obj).__module__)


def _get_table_columns(pw_table: Any) -> list[str]:
    """Extract column names from Pathway table schema."""
    schema = pw_table.schema
    return [name for name in schema.keys() if not name.startswith("_")]


# =============================================================================
# Table Widget
# =============================================================================


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
        pv.table(stats, title="By Region", columns=["region", "revenue"])

    Example (Manual):
        events = pv.table("events", title="Events", columns=["time", "msg"])
        events.send({"time": "12:00", "msg": "Started"})
    """
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

    state = get_state()
    widget_id = id or f"pw_table_{len(state.widgets)}"

    if columns is None:
        columns = _get_table_columns(pw_table)

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


# =============================================================================
# Stat Widget
# =============================================================================


@dataclass
class _ManualStat:
    """Manual stat widget."""

    id: str
    _last_value: float | None = None
    _show_delta: bool = True
    _alert_below: float | None = None
    _alert_above: float | None = None

    def send(self, value: float) -> None:
        """Update the stat value."""
        delta = None
        if self._show_delta and self._last_value is not None:
            delta = value - self._last_value
        self._last_value = value

        # Determine alert status based on thresholds
        alert = None
        if self._alert_below is not None and value < self._alert_below:
            alert = "low"
        elif self._alert_above is not None and value > self._alert_above:
            alert = "high"

        _send_data(
            json.dumps(
                {
                    "type": "data",
                    "widget": self.id,
                    "value": value,
                    "delta": delta,
                    "alert": alert,
                    "timestamp": int(time.time() * 1000),
                }
            )
        )


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
    alert_below: float | None = None,
    alert_above: float | None = None,
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
        alert_below: Trigger alert when value drops below this threshold
        alert_above: Trigger alert when value exceeds this threshold
        embed: Enable embeddable endpoint

    Example (Pathway):
        totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
        pv.stat(totals, "revenue", title="Revenue", unit="$")

    Example (Manual with alerts):
        opm = pv.stat("orders_per_min", title="Orders/Min", alert_below=2)
        opm.send(1.5)  # Will trigger "low" alert
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
        alert_below=alert_below,
        alert_above=alert_above,
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

    state = get_state()
    widget_id = id or f"stat_{column}_{len(state.widgets)}"
    color = color or next_color()
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


def _stat_manual(
    widget_id: str,
    *,
    title: str | None,
    unit: str,
    color: str | None,
    delta: bool,
    alert_below: float | None,
    alert_above: float | None,
    embed: bool,
) -> _ManualStat:
    """Create a manual stat widget."""
    _register_widget(
        widget_id,
        {
            "widget_type": "stat",
            "title": title or widget_id,
            "unit": unit,
            "color": color or next_color(),
            "alert_below": alert_below,
            "alert_above": alert_above,
            "embed": embed,
        },
    )

    return _ManualStat(
        id=widget_id,
        _show_delta=delta,
        _alert_below=alert_below,
        _alert_above=alert_above,
    )


# =============================================================================
# Chart Widget
# =============================================================================


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
    height: int | None = None,
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
        height: Chart height in pixels (default: 140 dashboard, 200 embed)
        embed: Enable embeddable endpoint

    Example (Pathway windowed):
        per_minute = orders.windowby(
            pw.this.timestamp,
            window=pw.temporal.tumbling(duration=timedelta(minutes=1))
        ).reduce(count=pw.reducers.count())

        pv.chart(per_minute, "count", x_column="window_end", title="Orders/min")

    Example (Manual):
        cpu = pv.chart("cpu", title="CPU Usage", unit="%")
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
            height=height,
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
        height=height,
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
    height: int | None,
    embed: bool,
) -> None:
    """Display Pathway data as a time series chart."""
    if not _PATHWAY_AVAILABLE:
        raise ImportError("Pathway required")

    state = get_state()
    widget_id = id or f"chart_{y_column}_{len(state.widgets)}"

    _register_widget(
        widget_id,
        {
            "widget_type": "metric",
            "title": title or y_column,
            "unit": unit,
            "color": color or next_color(),
            "chart_type": chart_type,
            "max_points": max_points,
            "height": height,
            "embed": embed,
        },
    )

    def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
        if not is_addition or y_column not in row:
            return

        value = row[y_column]

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


def _chart_manual(
    widget_id: str,
    *,
    title: str | None,
    unit: str,
    color: str | None,
    max_points: int,
    height: int | None,
    embed: bool,
) -> _ManualChart:
    """Create a manual chart widget."""
    _register_widget(
        widget_id,
        {
            "widget_type": "metric",
            "title": title or widget_id,
            "unit": unit,
            "color": color or next_color(),
            "max_points": max_points,
            "height": height,
            "embed": embed,
        },
    )

    return _ManualChart(id=widget_id)


# =============================================================================
# Gauge Widget
# =============================================================================


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
        pv.gauge(system_stats, "cpu", title="CPU", max_val=100, unit="%",
                 thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])

    Example (Manual):
        cpu = pv.gauge("cpu", title="CPU", max_val=100, unit="%")
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

    state = get_state()
    widget_id = id or f"gauge_{column}_{len(state.widgets)}"
    color = color or next_color()

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
    color = color or next_color()

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
