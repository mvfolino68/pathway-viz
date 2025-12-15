"""
Basic tests for PathwayViz.
"""

import pathway as pw
import pathwayviz as pv


def test_version():
    """Version should be defined."""
    assert hasattr(pv, "__version__")
    assert pv.__version__
    assert "." in pv.__version__


def test_widget_server_creation():
    """WidgetServer should be creatable."""
    server = pv.WidgetServer(port=3001, title="Test Server")
    assert server.port == 3001
    assert server.title == "Test Server"


def test_stat_widget_class():
    """Stat widget class should be creatable."""
    t = pw.debug.table_from_markdown(
        """
        | total
        | 100
        """
    )
    widget = pv.Stat(t, "total", id="test_stat", title="Test Stat", unit="$")
    assert widget.id == "test_stat"
    assert widget.title == "Test Stat"
    assert widget.unit == "$"
    assert widget.column == "total"


def test_chart_widget_class():
    """Chart widget class should be creatable."""
    t = pw.debug.table_from_markdown(
        """
        | value
        | 10
        """
    )
    widget = pv.Chart(t, "value", id="test_chart", title="Test Chart", unit="%")
    assert widget.id == "test_chart"
    assert widget.title == "Test Chart"
    assert widget.y_column == "value"


def test_gauge_widget_class():
    """Gauge widget class should be creatable."""
    t = pw.debug.table_from_markdown(
        """
        | pct
        | 75
        """
    )
    widget = pv.Gauge(t, "pct", id="test_gauge", title="Test Gauge", max_val=100)
    assert widget.id == "test_gauge"
    assert widget.max_val == 100


def test_table_widget_class():
    """Table widget class should be creatable."""
    t = pw.debug.table_from_markdown(
        """
        | a | b
        | 1 | 2
        """
    )
    widget = pv.Table(t, id="test_table", title="Test Table", columns=["a", "b"])
    assert widget.id == "test_table"
    assert widget.columns == ["a", "b"]
