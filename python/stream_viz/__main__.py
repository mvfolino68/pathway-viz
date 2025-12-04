#!/usr/bin/env python3
"""
StreamViz CLI - Run demos with: python -m stream_viz

Examples:
    python -m stream_viz              # Built-in demo with all widgets
    python -m stream_viz simple       # Simple sine waves
    python -m stream_viz kafka        # Kafka consumer demo (requires Docker)
    python -m stream_viz ecommerce    # E-commerce with Pathway aggregations
"""

import argparse
import atexit
import signal
import subprocess
import sys
import time
from pathlib import Path

# Track background processes for cleanup
_procs: list[subprocess.Popen] = []


def _cleanup():
    """Kill all background processes on exit."""
    for p in _procs:
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def _signal_handler(sig, frame):
    print("\n\nShutting down...")
    _cleanup()
    sys.exit(0)


# =============================================================================
# Docker / Kafka Helpers
# =============================================================================


def _docker_running() -> bool:
    """Check if Redpanda/Kafka is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "redpanda" in result.stdout
    except Exception:
        return False


def _start_docker():
    """Start Redpanda via docker-compose."""
    compose = Path(__file__).parent.parent.parent / "docker-compose.yml"
    if not compose.exists():
        compose = Path.cwd() / "docker-compose.yml"
    if not compose.exists():
        print("❌ docker-compose.yml not found")
        return False

    print("Starting Redpanda...")
    subprocess.run(
        ["docker-compose", "-f", str(compose), "up", "-d"],
        capture_output=True,
    )
    time.sleep(3)
    return _docker_running()


def _ensure_topic(topic: str):
    """Create a Kafka topic if it doesn't exist."""
    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "redpanda",
                "rpk",
                "topic",
                "create",
                topic,
                "--brokers=localhost:9092",
            ],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def _start_producer(name: str) -> subprocess.Popen | None:
    """Start a producer script in the background."""
    examples = Path(__file__).parent.parent.parent / "examples"
    if not examples.exists():
        examples = Path.cwd() / "examples"

    scripts = {
        "metrics": examples / "producer.py",
        "ecommerce": examples / "ecommerce_producer.py",
    }

    script = scripts.get(name)
    if script and script.exists():
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _procs.append(proc)
        print(f"✓ Started {name} producer (PID: {proc.pid})")
        return proc
    return None


# =============================================================================
# Demo Commands
# =============================================================================


def run_default(port: int):
    """Run the built-in demo with all widget types."""
    import stream_viz as sv

    print("\n🚀 StreamViz Demo")
    print("=" * 40)
    sv.run_demo(port)


def run_simple(port: int):
    """Run a simple sine wave demo - no dependencies."""
    import math
    import random

    import stream_viz as sv

    print("\n🚀 StreamViz Simple Demo")
    print("=" * 40)

    sv.title("Simple Metrics")
    cpu = sv.metric("cpu", title="CPU Usage", unit="%")
    memory = sv.metric("memory", title="Memory", unit="%", color="#00ff88")
    latency = sv.metric("latency", title="Latency", unit="ms", color="#ff6b6b")

    sv.start(port)
    print("Press Ctrl+C to stop\n")

    i = 0
    base_mem = 50.0
    try:
        while True:
            cpu_val = 50 + 30 * math.sin(i * 0.05) + random.gauss(0, 5)
            cpu.send(max(0, min(100, cpu_val)))

            base_mem += random.gauss(0.01, 0.1)
            if base_mem > 85:
                base_mem = 50
            memory.send(max(0, min(100, base_mem)))

            if random.random() < 0.05:
                latency.send(random.uniform(100, 300))
            else:
                latency.send(15 + abs(random.gauss(0, 10)))

            time.sleep(0.05)
            i += 1
    except KeyboardInterrupt:
        print("\nStopped.")


def run_kafka(port: int):
    """Run the Kafka consumer demo with auto-start."""
    import json

    import stream_viz as sv

    print("\n🚀 StreamViz Kafka Demo")
    print("=" * 40)

    # Ensure Kafka is running
    if not _docker_running():
        if not _start_docker():
            print("❌ Could not start Kafka. Install Docker or run manually.")
            return
    else:
        print("✓ Redpanda already running")

    # Create topic and start producer
    _ensure_topic("metrics")
    _start_producer("metrics")
    time.sleep(1)

    # Set up dashboard
    sv.title("Kafka Metrics")
    cpu = sv.metric("cpu", title="CPU Usage", unit="%")
    memory = sv.metric("memory", title="Memory", unit="%", color="#00ff88")
    latency = sv.metric("latency", title="Latency", unit="ms", color="#ff6b6b")
    rps = sv.metric("rps", title="Requests/sec", color="#ffd93d")

    sv.start(port)
    print("Connecting to Kafka...")

    try:
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            "metrics",
            bootstrap_servers=["localhost:9092"],
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        print("Consuming from 'metrics' topic...")
        print("Press Ctrl+C to stop\n")

        for msg in consumer:
            data = msg.value
            if "cpu" in data:
                cpu.send(data["cpu"])
            if "memory" in data:
                memory.send(data["memory"])
            if "latency" in data:
                latency.send(data["latency"])
            if "rps" in data:
                rps.send(data["rps"])

    except ImportError:
        print("❌ kafka-python not installed. Run: pip install kafka-python-ng")
    except KeyboardInterrupt:
        print("\nStopped.")


def run_ecommerce(port: int):
    """Run the e-commerce demo with Pathway aggregations."""
    print("\n🚀 StreamViz E-commerce Demo (Pathway)")
    print("=" * 40)

    # Ensure Kafka is running
    if not _docker_running():
        if not _start_docker():
            print("❌ Could not start Kafka. Install Docker or run manually.")
            return
    else:
        print("✓ Redpanda already running")

    # Create topic and start producer
    _ensure_topic("orders")
    _start_producer("ecommerce")
    time.sleep(1)

    print("Starting Pathway aggregation pipeline...")

    try:
        import pathway as pw

        import stream_viz as sv

        sv.title("E-commerce Analytics (Pathway)")

        # Stats
        total_orders = sv.stat("total_orders", title="Total Orders")
        total_revenue = sv.stat("total_revenue", title="Total Revenue", unit="$")

        # Windowed aggregations
        orders_min = sv.metric(
            "orders_min",
            title="Orders/min",
            window="1m",
            aggregation="count",
            color="#00d4ff",
        )
        revenue_min = sv.metric(
            "revenue_min",
            title="Revenue/min",
            unit="$",
            window="1m",
            aggregation="sum",
            color="#00ff88",
        )
        avg_order = sv.metric(
            "avg_order",
            title="Avg Order Value",
            unit="$",
            window="30s",
            aggregation="avg",
            color="#ffd93d",
        )

        sv.start(port)

        # Read from Kafka
        orders = pw.io.kafka.read(
            rdkafka_settings={"bootstrap.servers": "localhost:9092"},
            topic="orders",
            format="json",
            schema=pw.schema_from_types(
                order_id=str, product=str, quantity=int, price=float, timestamp=str
            ),
            autocommit_duration_ms=100,
        )

        # Running totals
        stats = orders.reduce(
            count=pw.reducers.count(),
            revenue=pw.reducers.sum(pw.this.price * pw.this.quantity),
        )

        # Subscribe to updates
        def on_stats(key, row, time, is_addition):
            if is_addition:
                total_orders.send(row["count"])
                total_revenue.send(row["revenue"])

        def on_order(key, row, time, is_addition):
            if is_addition:
                amount = row["price"] * row["quantity"]
                orders_min.send(1)
                revenue_min.send(amount)
                avg_order.send(amount)

        pw.io.subscribe(stats, on_stats)
        pw.io.subscribe(orders, on_order)

        print("Press Ctrl+C to stop\n")
        pw.run()

    except ImportError:
        print("❌ pathway not installed. Run: pip install pathway")
    except KeyboardInterrupt:
        print("\nStopped.")


# =============================================================================
# Main
# =============================================================================


def main():
    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    parser = argparse.ArgumentParser(
        description="StreamViz - Real-time streaming data visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m stream_viz              # Built-in demo with all widgets
  python -m stream_viz simple       # Simple sine waves
  python -m stream_viz kafka        # Kafka consumer demo (auto-starts Docker)
  python -m stream_viz ecommerce    # E-commerce with Pathway
  python -m stream_viz --port 8080  # Use different port
""",
    )

    parser.add_argument(
        "demo",
        nargs="?",
        choices=["default", "simple", "kafka", "ecommerce"],
        default="default",
        help="Demo to run (default: built-in demo)",
    )
    parser.add_argument("--port", "-p", type=int, default=3000, help="Port (default: 3000)")

    args = parser.parse_args()

    demos = {
        "default": run_default,
        "simple": run_simple,
        "kafka": run_kafka,
        "ecommerce": run_ecommerce,
    }

    demos[args.demo](args.port)


if __name__ == "__main__":
    main()
