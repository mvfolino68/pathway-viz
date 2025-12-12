#!/usr/bin/env python3
"""
PathwayViz Pipeline Template

This is a starter template for building real-time dashboards with Pathway and PathwayViz.

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

    import pathway_viz as pv

    pv.title("My Dashboard")

    # Create widgets
    counter = pv.stat("requests", title="Total Requests")
    latency = pv.chart("latency", title="Latency", unit="ms")
    cpu = pv.gauge("cpu", title="CPU", unit="%", max_val=100)
    events = pv.table("events", title="Recent Events", columns=["time", "message"])

    pv.start(port)
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

    import pathway_viz as pv

    kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    # Read from Kafka
    events = pw.io.kafka.read(
        rdkafka_settings={"bootstrap.servers": kafka_servers, "group.id": "pathwayviz"},
        topic="events",
        format="json",
        autocommit_duration_ms=1000,
    )

    # Aggregations
    totals = events.reduce(
        count=pw.reducers.count(),
    )

    # Dashboard
    pv.title("Event Analytics")
    pv.stat(totals, "count", title="Total Events")
    pv.start(port)

    print(f"Dashboard at http://localhost:{port}")
    print(f"Connected to Kafka at {kafka_servers}")
    pw.run()


def main():
    parser = argparse.ArgumentParser(description="PathwayViz Pipeline")
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
