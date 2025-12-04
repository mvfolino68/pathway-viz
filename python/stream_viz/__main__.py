#!/usr/bin/env python3
"""
StreamViz CLI - Run demos and manage dashboards.

Usage:
    python -m stream_viz              # Interactive demo with all widgets
    python -m stream_viz demo         # Same as above
    python -m stream_viz simple       # Simple charts demo
    python -m stream_viz --port 8080  # Run on a different port
"""

import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="stream_viz",
        description="StreamViz - The visualization layer for Pathway",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="demo",
        choices=["demo", "simple"],
        help="Which demo to run (default: demo)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=3000,
        help="Port to run server on (default: 3000)",
    )

    args = parser.parse_args()

    if args.command == "demo":
        run_demo(args.port)
    elif args.command == "simple":
        run_simple(args.port)


def run_demo(port: int):
    """Run the full interactive demo."""
    import stream_viz as sv

    print("\n🚀 StreamViz Demo")
    print("=" * 40)
    print(f"Starting dashboard on http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    sv.run_demo(port)


def run_simple(port: int):
    """Run a minimal demo with just a few charts."""
    import math
    import random
    import time

    import stream_viz as sv

    print("\n🚀 StreamViz Simple Demo")
    print("=" * 40)
    print(f"Dashboard: http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    sv.title("Simple Metrics")

    cpu = sv.chart("cpu", title="CPU Usage", unit="%")
    memory = sv.chart("memory", title="Memory", unit="%", color="#00ff88")

    sv.start(port)

    i = 0
    base_mem = 50.0

    try:
        while True:
            # CPU oscillation
            cpu_val = 50 + 30 * math.sin(i * 0.05) + random.gauss(0, 5)
            cpu.send(max(0, min(100, cpu_val)))

            # Memory drift
            base_mem += random.gauss(0.01, 0.1)
            if base_mem > 85:
                base_mem = 50
            memory.send(max(0, min(100, base_mem)))

            time.sleep(0.05)
            i += 1
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
