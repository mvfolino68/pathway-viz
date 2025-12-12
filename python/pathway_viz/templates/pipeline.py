#!/usr/bin/env python3
"""
PathwayViz Pipeline Template

Run without Docker:
    python pipeline.py --mode simple

Run with Kafka (requires Docker):
    docker compose up -d
    python pipeline.py
"""

import argparse
import math
import random
import time

import pathway_viz as pv


def run_simple_demo(port: int = 3000):
    """Run a simple demo without Kafka."""
    pv.title("My Dashboard")

    counter = pv.stat("requests", title="Total Requests")
    latency = pv.chart("latency", title="Latency", unit="ms")
    cpu = pv.gauge(
        "cpu",
        title="CPU",
        max_val=100,
        unit="%",
        thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")],
    )
    events = pv.table("events", title="Recent Events", columns=["time", "message"])

    pv.start(port=port)
    print(f"Dashboard running at http://localhost:{port}")

    count = 0
    try:
        while True:
            count += 1
            t = time.time()

            counter.send(count)
            latency.send(50 + 30 * math.sin(t / 5) + random.uniform(-10, 10))
            cpu.send(40 + 20 * math.sin(t / 10) + random.uniform(-5, 5))
            events.send({"time": time.strftime("%H:%M:%S"), "message": f"Event {count}"})

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        pv.stop()


def run_kafka_demo(port: int = 3000):
    """Run with Kafka - add your Pathway pipeline here."""
    try:
        import pathway as pw
    except ImportError:
        print("Pathway not installed. Run: pip install pathway-viz[demo]")
        return

    # TODO: Add your Pathway pipeline here
    # Example:
    # orders = pw.io.kafka.read(...)
    # totals = orders.reduce(...)
    # pv.stat(totals, "revenue", title="Revenue")

    print("Add your Pathway pipeline to this file!")
    print("See: https://github.com/mvfolino68/pathway-viz")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="My PathwayViz Dashboard")
    parser.add_argument("--port", "-p", type=int, default=3000)
    parser.add_argument("--mode", choices=["simple", "kafka"], default="simple")
    args = parser.parse_args()

    if args.mode == "simple":
        run_simple_demo(port=args.port)
    else:
        run_kafka_demo(port=args.port)
