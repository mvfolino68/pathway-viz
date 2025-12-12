"""
Basic tests for PathwayViz.
"""

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
    """Charts should be creatable."""
    chart = pv.chart("test_chart", title="Test", unit="%")
    assert chart.id == "test_chart"


def test_stat_creation():
    """Stats should be creatable."""
    stat = pv.stat("test_stat", title="Test Stat", unit="$")
    assert stat.id == "test_stat"


def test_gauge_creation():
    """Gauges should be creatable."""
    gauge = pv.gauge("test_gauge", title="Test Gauge", max_val=100)
    assert gauge.id == "test_gauge"


def test_table_creation():
    """Tables should be creatable."""
    table = pv.table("test_table", title="Test Table", columns=["a", "b"])
    assert table.id == "test_table"
