#!/usr/bin/env python3
"""
Simple demo without Kafka - just sends data directly.

This is the quickest way to see StreamViz in action.

Usage:
    python examples/simple_demo.py

Then open http://localhost:3000 in your browser.
"""

import math
import time

import stream_viz as sv


def main():
    # Define the dashboard
    sv.title("Simple Demo")

    sine = sv.metric("sine", title="Sine Wave", unit="")
    cosine = sv.metric("cosine", title="Cosine Wave", unit="")
    combined = sv.metric("combined", title="Combined", unit="")
    pulse = sv.metric("pulse", title="Pulse", unit="")

    # Start the server (non-blocking)
    sv.start(port=3000)
    print("Dashboard running at http://localhost:3000")
    print("Streaming data... (Ctrl+C to stop)")

    i = 0
    try:
        while True:
            t = i * 0.05

            sine.send(50 + 40 * math.sin(t))
            cosine.send(50 + 40 * math.cos(t))
            combined.send(50 + 30 * math.sin(t) + 20 * math.cos(t * 2))
            # Smooth pulse that rises and falls
            pulse.send(50 + 40 * abs(math.sin(t * 0.5)))

            time.sleep(0.05)
            i += 1

    except KeyboardInterrupt:
        print("\nDone!")


if __name__ == "__main__":
    main()
