"""
Widget classes for PathwayViz.

Provides Stat, Chart, Table, and Gauge widget classes for Pathway tables.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import pathway as pw

from ._pathwayviz import send_data as _send_data

if TYPE_CHECKING:
    from ._server import WidgetServer


def _get_table_columns(pw_table: Any) -> list[str]:
    """Extract column names from Pathway table schema."""
    schema = pw_table.schema
    return [name for name in schema.keys() if not name.startswith("_")]


# =============================================================================
# Widget Base Class
# =============================================================================


class Widget(ABC):
    """
    Base class for all PathwayViz widgets.

    Widgets are registered with a WidgetServer and automatically stream
    data from Pathway tables to connected browsers.
    """

    _counter: int = 0

    def __init__(
        self,
        pw_table: Any,
        *,
        id: str | None = None,
        title: str | None = None,
        color: str | None = None,
    ) -> None:
        """
        Initialize a widget.

        Args:
            pw_table: Pathway table to subscribe to
            id: Widget identifier (auto-generated if not provided)
            title: Display title
            color: Widget color (auto-assigned if not provided)
        """
        self.pw_table = pw_table
        self.id = id or self._generate_id()
        self.title = title
        self.color = color
        self._server: WidgetServer | None = None

    @classmethod
    def _generate_id(cls) -> str:
        """Generate a unique widget ID."""
        cls._counter += 1
        return f"widget_{cls._counter}"

    @abstractmethod
    def _get_config(self) -> dict:
        """Get widget configuration for the frontend."""
        pass

    @abstractmethod
    def _activate(self, server: WidgetServer) -> None:
        """Activate the widget's data subscription."""
        pass


# =============================================================================
# Stat Widget
# =============================================================================


class Stat(Widget):
    """
    A prominent single-value display with optional delta tracking.

    Best used with single-row tables (e.g., from reduce()).

    Example:
        totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
        server.register(pv.Stat(totals, "revenue", title="Revenue", unit="$"))
    """

    def __init__(
        self,
        pw_table: Any,
        column: str,
        *,
        id: str | None = None,
        title: str | None = None,
        unit: str = "",
        color: str | None = None,
        format: str | None = None,
        delta: bool = True,
    ) -> None:
        """
        Create a stat widget.

        Args:
            pw_table: Pathway table to display
            column: Column to display
            id: Widget identifier
            title: Display title
            unit: Unit suffix (e.g., "$", "%", "ms")
            color: Text color
            format: Python format string (e.g., ",.2f")
            delta: Show change from previous value
        """
        super().__init__(pw_table, id=id, title=title or column, color=color)
        self.column = column
        self.unit = unit
        self.format = format
        self.delta = delta
        self._last_value: float | None = None

    def _get_config(self) -> dict:
        return {
            "widget_type": "stat",
            "title": self.title,
            "unit": self.unit,
            "color": self.color,
            "format": self.format,
            "embed": True,
        }

    def _activate(self, server: WidgetServer) -> None:
        self._server = server
        widget_id = self.id
        column = self.column
        delta_enabled = self.delta

        def on_change(key: Any, row: dict, time: int, is_addition: bool) -> None:
            if not is_addition or column not in row:
                return

            value = row[column]
            delta_val = None
            if delta_enabled and self._last_value is not None:
                delta_val = value - self._last_value
            self._last_value = value

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

        pw.io.subscribe(self.pw_table, on_change=on_change)


# =============================================================================
# Chart Widget
# =============================================================================


class Chart(Widget):
    """
    A time series line or area chart.

    Best with windowby() aggregations.

    Example:
        per_minute = orders.windowby(...).reduce(count=pw.reducers.count())
        server.register(pv.Chart(per_minute, "count", x_column="window_end"))
    """

    def __init__(
        self,
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
    ) -> None:
        """
        Create a chart widget.

        Args:
            pw_table: Pathway table to display
            y_column: Value column
            x_column: Time column (uses wall-clock time if not specified)
            id: Widget identifier
            title: Display title
            unit: Y-axis unit
            color: Line/fill color
            chart_type: "line" or "area"
            max_points: Max points to display
            height: Chart height in pixels
            time_window: Rolling time window in seconds (default: 120)
        """
        super().__init__(pw_table, id=id, title=title or y_column, color=color)
        self.y_column = y_column
        self.x_column = x_column
        self.unit = unit
        self.chart_type = chart_type
        self.max_points = max_points
        self.height = height
        self.time_window = time_window if time_window is not None else 120

    def _get_config(self) -> dict:
        return {
            "widget_type": "metric",
            "title": self.title,
            "unit": self.unit,
            "color": self.color,
            "chart_type": self.chart_type,
            "max_points": self.max_points,
            "height": self.height,
            "time_window": self.time_window,
            "embed": True,
        }

    def _activate(self, server: WidgetServer) -> None:
        self._server = server
        widget_id = self.id
        y_column = self.y_column
        x_column = self.x_column

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

        pw.io.subscribe(self.pw_table, on_change=on_change)


# =============================================================================
# Gauge Widget
# =============================================================================


class Gauge(Widget):
    """
    A circular gauge for bounded values.

    Great for percentages, utilization metrics, or any value with a known range.

    Example:
        system = ...reduce(cpu=pw.reducers.avg(pw.this.cpu_pct))
        server.register(pv.Gauge(system, "cpu", title="CPU", max_val=100, unit="%"))
    """

    def __init__(
        self,
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
    ) -> None:
        """
        Create a gauge widget.

        Args:
            pw_table: Pathway table to display
            column: Column to display
            id: Widget identifier
            title: Display title
            unit: Unit suffix
            min_val: Minimum scale value
            max_val: Maximum scale value
            color: Gauge color
            thresholds: Color zones as [(value, color), ...]
        """
        super().__init__(pw_table, id=id, title=title or column, color=color)
        self.column = column
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.thresholds = thresholds

    def _get_config(self) -> dict:
        return {
            "widget_type": "gauge",
            "title": self.title,
            "unit": self.unit,
            "min": self.min_val,
            "max": self.max_val,
            "color": self.color,
            "thresholds": self.thresholds or [(self.max_val, self.color)],
            "embed": True,
        }

    def _activate(self, server: WidgetServer) -> None:
        self._server = server
        widget_id = self.id
        column = self.column

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

        pw.io.subscribe(self.pw_table, on_change=on_change)


# =============================================================================
# Table Widget
# =============================================================================


class Table(Widget):
    """
    A live-updating table that syncs with Pathway table state.

    Rows are keyed by Pathway's internal row key and update in place.

    Example:
        by_region = orders.groupby(pw.this.region).reduce(...)
        server.register(pv.Table(by_region, title="By Region"))
    """

    def __init__(
        self,
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
    ) -> None:
        """
        Create a table widget.

        Args:
            pw_table: Pathway table to display
            id: Widget identifier
            title: Display title
            columns: Which columns to display (all if None)
            column_labels: Display labels {"col_name": "Display Name"}
            column_format: Format strings {"amount": "$,.2f"}
            max_rows: Maximum rows to show
            sort_by: Column to sort by
            sort_desc: Sort descending
        """
        super().__init__(pw_table, id=id, title=title or "Table", color=None)
        self.columns = columns or _get_table_columns(pw_table)
        self.column_labels = column_labels
        self.column_format = column_format
        self.max_rows = max_rows
        self.sort_by = sort_by
        self.sort_desc = sort_desc

    def _get_config(self) -> dict:
        cols = []
        for col in self.columns:
            config = {
                "name": col,
                "label": (self.column_labels or {}).get(col, col),
            }
            if self.column_format and col in self.column_format:
                config["format"] = self.column_format[col]
            cols.append(config)

        return {
            "widget_type": "pathway_table",
            "title": self.title,
            "columns": cols,
            "max_rows": self.max_rows,
            "sort_by": self.sort_by,
            "sort_desc": self.sort_desc,
            "embed": True,
        }

    def _activate(self, server: WidgetServer) -> None:
        self._server = server
        widget_id = self.id
        columns = self.columns

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

        pw.io.subscribe(self.pw_table, on_change=on_change)
