#!/usr/bin/env python3
"""
StreamViz CLI

Usage:
    python -m stream_viz                       # Run the Pathway+Kafka demo
    python -m stream_viz --mode simple         # Run a no-Docker demo
    python -m stream_viz --port 8080           # Run on custom port
"""

import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="stream_viz",
        description="StreamViz - Real-time dashboards for streaming data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=3000,
        help="Server port (default: 3000)",
    )

    parser.add_argument(
        "--mode",
        choices=["pathway", "simple"],
        default="pathway",
        help=(
            "Which demo to run: 'pathway' (Kafka+Pathway, requires Docker) or "
            "'simple' (no Docker, manual send loop)"
        ),
    )

    args = parser.parse_args()

    if args.mode == "simple":
        import stream_viz as sv

        sv.run_demo(port=args.port)
        return

    from stream_viz.demos import run_demo

    run_demo(port=args.port)


if __name__ == "__main__":
    main()
