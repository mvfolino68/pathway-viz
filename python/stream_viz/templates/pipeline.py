#!/usr/bin/env python3
"""
StreamViz Pipeline Template

This is a starter template for building real-time dashboards with Pathway and StreamViz.

Run locally (no Docker):
    python pipeline.py --mode simple

Run with Kafka (requires Docker):
    docker compose up -d
    python pipeline.py
"""

import argparse
import os


def run_simple_demo(port: int = 3000):
    """Run a simple demo without Kafka - good for testing."""
    import math
    import random
    import time

    import stream_viz as sv

    sv.title("My Dashboard")

    # Create widgets
    counter = sv.stat("requests", title="Total Requests")
    latency = sv.chart("latency", title="Latency", unit="ms")
    cpu = sv.gauge("cpu", title="CPU", unit="%", max_val=100)
    events = sv.table("events", title="Recent Events", columns=["time", "message"])

    sv.start(port)
    print(f"Dashboard running at http://localhost:{port}")

    total = 0
    i = 0
    try:
        while True:
            # Simulate metrics
            total += random.randint(1, 10)
            counter.send(total)

            latency.send(20 + random.gauss(0, 5))
            cpu.send(50 + 30 * math.sin(i * 0.1) + random.gauss(0, 5))

            if random.random() < 0.1:
                events.send(
                    {
                        "time": time.strftime("%H:%M:%S"),
                        "message": random.choice(
                            ["Request processed", "Cache hit", "Query completed"]
                        ),
                    }
                )

            time.sleep(0.1)
            i += 1
    except KeyboardInterrupt:
        print("\nStopped.")


def run_pathway_pipeline(port: int = 3000):
    """Run a Pathway pipeline with Kafka - production mode."""
    import pathway as pw

    import stream_viz as sv

    kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    # Read from Kafka
    events = pw.io.kafka.read(
        rdkafka_settings={"bootstrap.servers": kafka_servers, "group.id": "streamviz"},
        topic="events",
        format="json",
        autocommit_duration_ms=1000,
    )

    # Aggregations
    totals = events.reduce(
        count=pw.reducers.count(),
    )

    # Dashboard
    sv.title("Event Analytics")
    sv.stat(totals, "count", title="Total Events")
    sv.start(port)

    print(f"Dashboard at http://localhost:{port}")
    print(f"Connected to Kafka at {kafka_servers}")
    pw.run()


def main():
    parser = argparse.ArgumentParser(description="StreamViz Pipeline")
    parser.add_argument("--port", "-p", type=int, default=3000, help="Server port")
    parser.add_argument(
        "--mode",
        choices=["pathway", "simple"],
        default="pathway",
        help="'simple' for no-Kafka demo, 'pathway' for production",
    )
    args = parser.parse_args()

    if args.mode == "simple":
        run_simple_demo(args.port)
    else:
        run_pathway_pipeline(args.port)


if __name__ == "__main__":
    main()
