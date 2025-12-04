#!/usr/bin/env python3
"""
Real-time business metrics with Pathway stream processing.

This demo shows how to use Pathway to compute streaming aggregations
on e-commerce data and visualize them with StreamViz.

Pathway computes running totals across all orders:
- Total Revenue (running sum)
- Order Count
- Average Order Value
- Electronics Revenue (category filter)

Requirements:
    pip install stream-viz[pathway]

Usage:
    # Terminal 1: Start Redpanda
    docker compose up -d

    # Terminal 2: Start order producer
    python examples/ecommerce_producer.py

    # Terminal 3: Run this demo
    python examples/pathway_demo.py

    # Open http://localhost:3000 to see the dashboard
"""

import threading
import time

import pathway as pw
import stream_viz as sv


def main():
    # Define the dashboard layout
    sv.title("E-Commerce Metrics (Pathway)")

    revenue_total = sv.metric("revenue", title="Total Revenue", unit="$", color="#00ff88")
    order_count = sv.metric("orders", title="Order Count", color="#00d4ff")
    avg_order = sv.metric("avg_order", title="Avg Order Value", unit="$", color="#ffd93d")
    electronics = sv.metric("electronics", title="Electronics Revenue", unit="$", color="#c44dff")

    # Start the visualization server
    sv.start(port=3000)

    # Kafka settings for Pathway
    rdkafka_settings = {
        "bootstrap.servers": "localhost:9092",
        "security.protocol": "plaintext",
        "group.id": "streamviz-pathway",
        "session.timeout.ms": "6000",
        "auto.offset.reset": "latest",
    }

    # Define schema for incoming orders
    class OrderSchema(pw.Schema):
        order_id: str
        timestamp: int  # milliseconds
        product: str
        category: str
        quantity: int
        unit_price: float
        discount_percent: int
        total: float
        region: str
        payment_method: str

    print("Connecting to Kafka...")

    # Read orders from Kafka
    orders = pw.io.kafka.read(
        rdkafka_settings,
        topic="orders",
        format="json",
        schema=OrderSchema,
        autocommit_duration_ms=1000,
    )

    # =========================================================================
    # Running aggregations - simple and robust
    # These update in real-time as new orders arrive
    # =========================================================================

    # Total revenue and order count across ALL orders
    totals = orders.reduce(
        total_revenue=pw.reducers.sum(pw.this.total),
        order_count=pw.reducers.count(),
    )

    # Electronics category only
    electronics_orders = orders.filter(pw.this.category == "electronics")
    electronics_totals = electronics_orders.reduce(
        electronics_revenue=pw.reducers.sum(pw.this.total),
    )

    # =========================================================================
    # Subscribe to results and send to StreamViz
    # =========================================================================
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

    print("Processing orders with Pathway...")
    print("Dashboard: http://localhost:3000")
    print("\nMetrics shown:")
    print("  - Total Revenue: Running sum of all orders")
    print("  - Order Count: Total orders processed")
    print("  - Avg Order Value: Running average")
    print("  - Electronics Revenue: Electronics category total")
    print("\nPress Ctrl+C to stop\n")

    # Run Pathway in a background thread
    def run_pathway():
        pw.run()

    pathway_thread = threading.Thread(target=run_pathway, daemon=True)
    pathway_thread.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
