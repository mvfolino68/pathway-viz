#!/usr/bin/env python3
"""
PathwayViz CLI

Usage:
    pathway-viz demo                  # Run demo with Kafka (requires Docker)
    pathway-viz demo --port 8080      # Custom port
"""

import argparse
import importlib.util
import sys


def cmd_demo(args):
    """Run the demo."""
    # Check for demo dependencies
    missing = []
    if not importlib.util.find_spec("kafka"):
        missing.append("kafka-python-ng")

    if missing:
        print(f"\n  Error: {', '.join(missing)} not installed")
        print("  Run: pip install pathway-viz[all]\n")
        sys.exit(1)

    from pathwayviz.demos import run_demo

    run_demo(port=args.port)


def main():
    parser = argparse.ArgumentParser(
        prog="pathway-viz",
        description="PathwayViz - Real-time dashboards for streaming data",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run the demo")
    demo_parser.add_argument(
        "--port", "-p", type=int, default=3000, help="Server port (default: 3000)"
    )
    demo_parser.set_defaults(func=cmd_demo)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
