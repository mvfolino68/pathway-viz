#!/usr/bin/env python3
"""
StreamViz - Run with: python -m stream_viz

This is the quickest way to see StreamViz in action!
"""

import argparse
import atexit
import signal
import subprocess
import sys
import time
from pathlib import Path

# Track background processes for cleanup
_background_processes: list[subprocess.Popen] = []


def _cleanup():
    """Kill all background processes on exit."""
    for proc in _background_processes:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down...")
    _cleanup()
    sys.exit(0)


def _get_examples_dir() -> Path:
    """Get the examples directory, works both in dev and installed mode."""
    # Try relative to this file (development mode)
    dev_path = Path(__file__).parent.parent.parent / "examples"
    if dev_path.exists():
        return dev_path

    # Try current working directory
    cwd_path = Path.cwd() / "examples"
    if cwd_path.exists():
        return cwd_path

    raise FileNotFoundError(
        "Could not find examples directory. Run from the stream-viz project root or clone the repo."
    )


def _ensure_docker_running():
    """Check if Docker/Redpanda is running, start if not."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "redpanda" in result.stdout:
            print("✓ Redpanda already running")
            return True
    except Exception:
        pass

    print("Starting Redpanda...")
    try:
        # Find docker-compose.yml
        compose_file = Path.cwd() / "docker-compose.yml"
        if not compose_file.exists():
            compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"

        if not compose_file.exists():
            print("❌ Could not find docker-compose.yml")
            print("   Run from the stream-viz project root")
            return False

        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            check=True,
            capture_output=True,
        )
        print("✓ Redpanda started")
        print("  Waiting for Redpanda to be ready...")
        time.sleep(3)  # Give it time to start
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Redpanda: {e}")
        return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False


def _start_background_process(cmd: list[str], name: str) -> subprocess.Popen | None:
    """Start a background process and track it for cleanup."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _background_processes.append(proc)
        print(f"✓ Started {name} (PID: {proc.pid})")
        return proc
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="StreamViz - Real-time streaming data visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m stream_viz              # Run the built-in demo
  python -m stream_viz simple       # Simple sine waves
  python -m stream_viz kafka        # Full Kafka demo (auto-starts everything!)
  python -m stream_viz ecommerce    # E-commerce with Pathway
  python -m stream_viz --port 8080  # Use a different port
""",
    )
    parser.add_argument(
        "demo",
        nargs="?",
        default="default",
        choices=["default", "simple", "kafka", "ecommerce"],
        help="Which demo to run (default: built-in demo)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=3000,
        help="Port to listen on (default: 3000)",
    )

    args = parser.parse_args()

    # Setup cleanup handlers
    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if args.demo == "default":
        from stream_viz import run_demo

        print("\n🚀 StreamViz Demo")
        print("=" * 40)
        print(f"Dashboard: http://localhost:{args.port}")
        print("Press Ctrl+C to stop\n")
        run_demo(port=args.port)

    elif args.demo == "simple":
        import math

        import stream_viz as sv

        print("\n🚀 StreamViz Simple Demo")
        print("=" * 40)

        sv.title("Simple Demo")
        sine = sv.metric("sine", title="Sine Wave")
        cosine = sv.metric("cosine", title="Cosine Wave")
        combined = sv.metric("combined", title="Combined")
        pulse = sv.metric("pulse", title="Pulse")

        sv.start(port=args.port)
        print("Press Ctrl+C to stop\n")

        i = 0
        try:
            while True:
                t = i * 0.05
                sine.send(50 + 40 * math.sin(t))
                cosine.send(50 + 40 * math.cos(t))
                combined.send(50 + 30 * math.sin(t) + 20 * math.cos(t * 2))
                pulse.send(50 + 40 * abs(math.sin(t * 0.5)))
                time.sleep(0.05)
                i += 1
        except KeyboardInterrupt:
            print("\nDone!")

    elif args.demo == "kafka":
        print("\n🚀 StreamViz Kafka Demo")
        print("=" * 40)

        # Check for kafka-python-ng
        import importlib.util

        if importlib.util.find_spec("kafka") is None:
            print("❌ kafka-python-ng not installed.")
            print("   Install with: pip install stream-viz[kafka]")
            sys.exit(1)

        # Ensure Docker/Redpanda is running
        if not _ensure_docker_running():
            sys.exit(1)

        # Start the producer in background
        examples_dir = _get_examples_dir()
        producer_path = examples_dir / "producer.py"

        print("\nStarting producer...")
        producer_proc = _start_background_process(
            [sys.executable, str(producer_path)], "metrics producer"
        )
        if not producer_proc:
            sys.exit(1)

        time.sleep(1)  # Let producer connect

        # Now run the Kafka dashboard
        print("\nStarting dashboard...\n")

        import json

        from kafka import KafkaConsumer

        import stream_viz as sv

        sv.title("Kafka Metrics Dashboard")
        cpu = sv.metric("cpu", title="CPU Usage", unit="%")
        memory = sv.metric("memory", title="Memory Usage", unit="%")
        rps = sv.metric("rps", title="Requests/sec")
        latency = sv.metric("latency", title="Latency", unit="ms")

        sv.start(port=args.port)

        print("Connecting to Kafka...")
        try:
            consumer = KafkaConsumer(
                "metrics",
                bootstrap_servers=["localhost:9092"],
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                group_id="streamviz-cli",
                consumer_timeout_ms=60000,
            )
            print("Consuming from 'metrics' topic...")
            print("Press Ctrl+C to stop\n")

            for message in consumer:
                data = message.value
                metrics = data.get("metrics", {})
                if "cpu_percent" in metrics:
                    cpu.send(metrics["cpu_percent"])
                if "memory_percent" in metrics:
                    memory.send(metrics["memory_percent"])
                if "requests_per_second" in metrics:
                    rps.send(metrics["requests_per_second"])
                if "latency_ms" in metrics:
                    latency.send(metrics["latency_ms"])

        except Exception as e:
            print(f"❌ Kafka error: {e}")
            sys.exit(1)

    elif args.demo == "ecommerce":
        print("\n🚀 StreamViz E-Commerce Demo (with Pathway)")
        print("=" * 40)

        # Check for pathway
        import importlib.util

        if importlib.util.find_spec("pathway") is None:
            print("❌ pathway not installed.")
            print("   Install with: pip install stream-viz[pathway]")
            print("   Note: Requires Python 3.11-3.13")
            sys.exit(1)

        # Check for kafka too
        if importlib.util.find_spec("kafka") is None:
            print("❌ kafka-python-ng not installed.")
            print("   Install with: pip install stream-viz[all]")
            sys.exit(1)

        # Ensure Docker/Redpanda is running
        if not _ensure_docker_running():
            sys.exit(1)

        # Start the e-commerce producer in background
        examples_dir = _get_examples_dir()
        producer_path = examples_dir / "ecommerce_producer.py"

        print("\nStarting e-commerce order producer...")
        producer_proc = _start_background_process(
            [sys.executable, str(producer_path)], "order producer"
        )
        if not producer_proc:
            sys.exit(1)

        time.sleep(2)  # Let producer connect and start sending

        # Now run the Pathway demo inline
        print("\nStarting Pathway aggregations...\n")

        import threading

        import pathway as pw

        import stream_viz as sv

        sv.title("E-Commerce Metrics (Pathway)")
        revenue_total = sv.metric("revenue", title="Total Revenue", unit="$", color="#00ff88")
        order_count = sv.metric("orders", title="Order Count", color="#00d4ff")
        avg_order = sv.metric("avg_order", title="Avg Order Value", unit="$", color="#ffd93d")
        electronics = sv.metric(
            "electronics", title="Electronics Revenue", unit="$", color="#c44dff"
        )

        sv.start(port=args.port)

        # Kafka settings for Pathway
        rdkafka_settings = {
            "bootstrap.servers": "localhost:9092",
            "security.protocol": "plaintext",
            "group.id": "streamviz-pathway-cli",
            "session.timeout.ms": "6000",
            "auto.offset.reset": "latest",
        }

        # Schema
        class OrderSchema(pw.Schema):
            order_id: str
            timestamp: int
            product: str
            category: str
            quantity: int
            unit_price: float
            discount_percent: int
            total: float
            region: str
            payment_method: str

        print("Connecting to Kafka...")

        orders = pw.io.kafka.read(
            rdkafka_settings,
            topic="orders",
            format="json",
            schema=OrderSchema,
            autocommit_duration_ms=1000,
        )

        # Running aggregations
        totals = orders.reduce(
            total_revenue=pw.reducers.sum(pw.this.total),
            order_count=pw.reducers.count(),
        )

        electronics_orders = orders.filter(pw.this.category == "electronics")
        electronics_totals = electronics_orders.reduce(
            electronics_revenue=pw.reducers.sum(pw.this.total),
        )

        def send_totals(key, row, time, is_addition):
            if is_addition and row["order_count"] > 0:
                revenue_total.send(row["total_revenue"])
                order_count.send(row["order_count"])
                avg_order.send(row["total_revenue"] / row["order_count"])

        def send_electronics(key, row, time, is_addition):
            if is_addition:
                electronics.send(row["electronics_revenue"])

        pw.io.subscribe(totals, send_totals)
        pw.io.subscribe(electronics_totals, send_electronics)

        print("Processing orders...")
        print(f"Dashboard: http://localhost:{args.port}")
        print("\nMetrics:")
        print("  • Total Revenue - Running sum of all orders")
        print("  • Order Count - Total orders processed")
        print("  • Avg Order Value - Running average")
        print("  • Electronics Revenue - Electronics category only")
        print("\nPress Ctrl+C to stop\n")

        # Run Pathway
        def run_pathway():
            pw.run()

        pathway_thread = threading.Thread(target=run_pathway, daemon=True)
        pathway_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
