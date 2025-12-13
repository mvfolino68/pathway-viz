"""
Basic tests for PathwayViz.
"""

import pathway as pw
import pathway_viz as pv


def test_version():
    """Version should be defined."""
    assert hasattr(pv, "__version__")
    # Version is read from package metadata, just check it's a valid semver-like string
    assert pv.__version__
    assert "." in pv.__version__


def test_title():
    """Title should be settable."""
    pv.title("Test Dashboard")


def test_chart_creation():
    """Charts should be creatable with a Pathway table."""
    t = pw.debug.table_from_markdown(
        """
        | value
        | 10
        """
    )
    pv.chart(t, "value", id="test_chart", title="Test", unit="%")


def test_stat_creation():
    """Stats should be creatable with a Pathway table."""
    t = pw.debug.table_from_markdown(
        """
        | total
        | 100
        """
    )
    pv.stat(t, "total", id="test_stat", title="Test Stat", unit="$")


def test_gauge_creation():
    """Gauges should be creatable with a Pathway table."""
    t = pw.debug.table_from_markdown(
        """
        | pct
        | 75
        """
    )
    pv.gauge(t, "pct", id="test_gauge", title="Test Gauge", max_val=100)


def test_table_creation():
    """Tables should be creatable with a Pathway table."""
    t = pw.debug.table_from_markdown(
        """
        | a | b
        | 1 | 2
        """
    )
    pv.table(t, id="test_table", title="Test Table", columns=["a", "b"])
