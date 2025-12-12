"""
Basic tests for PathwayViz.
"""

import pathway_viz as sv


def test_version():
    """Version should be defined."""
    assert hasattr(sv, "__version__")
    assert sv.__version__ == "0.1.0"


def test_title():
    """Title should be settable."""
    sv.title("Test Dashboard")


def test_chart_creation():
    """Charts should be creatable."""
    chart = sv.chart("test_chart", title="Test", unit="%")
    assert chart.id == "test_chart"


def test_stat_creation():
    """Stats should be creatable."""
    stat = sv.stat("test_stat", title="Test Stat", unit="$")
    assert stat.id == "test_stat"


def test_gauge_creation():
    """Gauges should be creatable."""
    gauge = sv.gauge("test_gauge", title="Test Gauge", max_val=100)
    assert gauge.id == "test_gauge"


def test_table_creation():
    """Tables should be creatable."""
    table = sv.table("test_table", title="Test Table", columns=["a", "b"])
    assert table.id == "test_table"
