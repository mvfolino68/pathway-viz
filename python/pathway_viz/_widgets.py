"""
Widget implementations for PathwayViz.

Provides table, stat, chart, and gauge widgets for Pathway tables.
"""

from __future__ import annotations

import json
from typing import Any

import pathway as pw

from ._pathway_viz import send_data as _send_data
from ._state import get_state, next_color


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


def _get_table_columns(pw_table: Any) -> list[str]:
    """Extract column names from Pathway table schema."""
    schema = pw_table.schema
    return [name for name in schema.keys() if not name.startswith("_")]


# =============================================================================
# Table Widget
# =============================================================================


def table(
    pw_table: Any,
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
) -> None:
    """
    Display a Pathway table as a live-updating table widget.

    Args:
        pw_table: Pathway Table to display
        id: Widget identifier (auto-generated if not provided)
        title: Display title
        columns: Which columns to display (all if None)
        column_labels: Display labels for columns {"col_name": "Display Name"}
        column_format: Format strings for columns {"amount": "$,.2f"}
        max_rows: Maximum rows to show
        sort_by: Column to sort by
        sort_desc: Sort descending
        embed: Enable embeddable endpoint at /embed/{id}

    Example:
        stats = orders.groupby(pw.this.region).reduce(...)
        pv.table(stats, title="By Region", columns=["region", "revenue"])
    """
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


# =============================================================================
# Stat Widget
# =============================================================================


def stat(
    pw_table: Any,
    column: str,
    *,
    id: str | None = None,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    format: str | None = None,
    delta: bool = True,
    embed: bool = False,
) -> None:
    """
    Display a column from a Pathway table as a prominent statistic.

    Best used with single-row tables (e.g., from reduce()).

    Args:
        pw_table: Pathway Table to display
        column: Column to display
        id: Widget identifier
        title: Display title
        unit: Unit suffix (e.g., "$", "%", "ms")
        color: Text color
        format: Python format string (e.g., ",.2f")
        delta: Show change from previous value
        embed: Enable embeddable endpoint

    Example:
        totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
        pv.stat(totals, "revenue", title="Revenue", unit="$")
    """
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


# =============================================================================
# Chart Widget
# =============================================================================


def chart(
    pw_table: Any,
    y_column: str,
    *,
    x_column: str | None = None,
    id: str | None = None,
    title: str | None = None,
    unit: str = "",
    color: str | None = None,
    chart_type: str = "line",
    max_points: int = 200,
    height: int | None = None,
    time_window: int | None = None,
    embed: bool = False,
) -> None:
    """
    Display Pathway data as a time series chart.

    Best with windowby() aggregations.

    Args:
        pw_table: Pathway Table to display
        y_column: Value column
        x_column: Time column (uses window_end or Pathway time if not specified)
        id: Widget identifier
        title: Display title
        unit: Y-axis unit
        color: Line/fill color
        chart_type: "line" or "area"
        max_points: Max points to display
        height: Chart height in pixels (default: 140 dashboard, 200 embed)
        time_window: Rolling time window in seconds (default: 120, None for unlimited)
        embed: Enable embeddable endpoint

    Example:
        per_minute = orders.windowby(
            pw.this.timestamp,
            window=pw.temporal.tumbling(duration=timedelta(minutes=1))
        ).reduce(count=pw.reducers.count())

        pv.chart(per_minute, "count", x_column="window_end", title="Orders/min")
    """
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
            "time_window": time_window if time_window is not None else 120,
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
            # Use wall-clock time for charts without explicit x_column
            import time as time_module

            ts = int(time_module.time() * 1000)

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


# =============================================================================
# Gauge Widget
# =============================================================================


def gauge(
    pw_table: Any,
    column: str,
    *,
    id: str | None = None,
    title: str | None = None,
    unit: str = "",
    min_val: float = 0,
    max_val: float = 100,
    color: str | None = None,
    thresholds: list[tuple[float, str]] | None = None,
    embed: bool = False,
) -> None:
    """
    Display a Pathway column as a circular gauge.

    Great for percentages, utilization metrics, or any bounded value.

    Args:
        pw_table: Pathway Table to display
        column: Column to display
        id: Widget identifier
        title: Display title
        unit: Unit suffix
        min_val: Minimum scale value
        max_val: Maximum scale value
        color: Gauge color
        thresholds: Color zones as [(value, color), ...]
        embed: Enable embeddable endpoint

    Example:
        system_stats = ...reduce(cpu=pw.reducers.avg(pw.this.cpu_pct))
        pv.gauge(system_stats, "cpu", title="CPU", max_val=100, unit="%",
                 thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])
    """
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
