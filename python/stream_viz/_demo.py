"""
Built-in demo for StreamViz.

Demonstrates all widget types without requiring Pathway or external dependencies.
"""

from __future__ import annotations

import math
import random
import time

from ._state import get_state
from ._widgets import chart, gauge, stat, table


def run_demo(port: int = 3000) -> None:
    """
    Run a demo showing all widget types.

    This runs without Pathway, using manual .send() calls.
    """
    from ._server import start

    state = get_state()
    state.config.title = "StreamViz Demo"

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
