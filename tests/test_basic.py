"""
Basic tests for StreamViz.
"""

import stream_viz as sv


def test_version():
    """Version should be defined."""
    assert hasattr(sv, "__version__")
    assert sv.__version__ == "0.1.0"


def test_metric_creation():
    """Metrics should be creatable."""
    metric = sv.metric("test_metric", title="Test", unit="%")
    assert metric.id == "test_metric"
    assert metric.title == "Test"
    assert metric.unit == "%"


def test_title():
    """Title should be settable."""
    sv.title("Test Dashboard")
    # No assertion - just checking it doesn't crash


def test_metric_defaults():
    """Metrics should have sensible defaults."""
    metric = sv.metric("cpu")
    assert metric.id == "cpu"
    assert metric.title == "cpu"  # Defaults to id
    assert metric.unit == ""
    assert metric.max_points == 200
