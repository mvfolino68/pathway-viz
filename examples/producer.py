#!/usr/bin/env python3
"""
Fake data producer for the StreamViz demo.

Generates realistic-looking metrics and publishes them to Kafka/Redpanda.
This simulates what you might see from a real application sending telemetry.

Usage:
    python examples/producer.py
"""

import json
import math
import random
import time
from datetime import datetime

from kafka import KafkaProducer


def generate_metrics() -> dict:
    """Generate realistic-looking application metrics."""
    now = datetime.now()
    base_time = time.time() * 1000  # milliseconds

    # Simulate daily patterns with some noise
    hour_factor = math.sin(now.hour * math.pi / 12)  # Peak at noon

    # CPU: 20-80% with daily pattern and noise
    cpu = 50 + (hour_factor * 20) + random.gauss(0, 5)
    cpu = max(0, min(100, cpu))

    # Memory: slowly trending up with small variations
    memory = 45 + (now.minute / 60 * 10) + random.gauss(0, 2)
    memory = max(0, min(100, memory))

    # Requests per second: bursty traffic
    if random.random() < 0.1:  # 10% chance of traffic spike
        rps = random.uniform(800, 1500)
    else:
        rps = 200 + (hour_factor * 150) + random.gauss(0, 30)
    rps = max(0, rps)

    # Latency: usually low, occasional spikes
    if random.random() < 0.05:  # 5% chance of latency spike
        latency = random.uniform(200, 500)
    else:
        latency = 15 + random.expovariate(0.1)
    latency = max(1, latency)

    return {
        "timestamp": int(base_time),
        "value": cpu,  # Primary metric for the chart
        "metrics": {
            "cpu_percent": round(cpu, 2),
            "memory_percent": round(memory, 2),
            "requests_per_second": round(rps, 2),
            "latency_ms": round(latency, 2),
        },
    }


def main():
    print("Connecting to Redpanda...")

    producer = KafkaProducer(
        bootstrap_servers=["localhost:9092"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("Publishing metrics to 'metrics' topic (Ctrl+C to stop)...")

    try:
        while True:
            metrics = generate_metrics()
            producer.send("metrics", metrics)

            # Print a sample every 20 messages
            if random.random() < 0.05:
                print(
                    f"  → cpu={metrics['metrics']['cpu_percent']:.1f}% "
                    f"mem={metrics['metrics']['memory_percent']:.1f}% "
                    f"rps={metrics['metrics']['requests_per_second']:.0f}"
                )

            time.sleep(0.25)  # 4 messages per second (slower, more readable)

    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
