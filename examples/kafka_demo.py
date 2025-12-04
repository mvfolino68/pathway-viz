#!/usr/bin/env python3
"""
Kafka/Redpanda streaming demo for StreamViz.

This example connects to a Kafka-compatible broker (like Redpanda),
consumes messages from a topic, and visualizes them in real-time.

Usage:
    # Start the demo infrastructure
    docker compose up -d

    # Start the producer (in another terminal)
    python examples/producer.py

    # Run this script
    python examples/kafka_demo.py
"""

import json
import signal
import sys

import stream_viz as sv
from kafka import KafkaConsumer


def main():
    # Graceful shutdown
    def shutdown(sig, frame):
        print("\nShutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Define the dashboard
    sv.title("Kafka Metrics Dashboard")

    cpu = sv.metric("cpu", title="CPU Usage", unit="%")
    memory = sv.metric("memory", title="Memory Usage", unit="%")
    rps = sv.metric("rps", title="Requests/sec")
    latency = sv.metric("latency", title="Latency", unit="ms")

    # Start the visualization server
    sv.start(port=3000)

    # Connect to Kafka/Redpanda
    print("Connecting to Kafka...")
    consumer = KafkaConsumer(
        "metrics",
        bootstrap_servers=["localhost:9092"],
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="streamviz-demo",
    )

    print("Consuming from 'metrics' topic...")

    # Stream data to the dashboard
    for message in consumer:
        data = message.value
        metrics = data.get("metrics", {})

        # Send each metric to its chart
        if "cpu_percent" in metrics:
            cpu.send(metrics["cpu_percent"])
        if "memory_percent" in metrics:
            memory.send(metrics["memory_percent"])
        if "requests_per_second" in metrics:
            rps.send(metrics["requests_per_second"])
        if "latency_ms" in metrics:
            latency.send(metrics["latency_ms"])


if __name__ == "__main__":
    main()
