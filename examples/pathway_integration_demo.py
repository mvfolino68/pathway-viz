#!/usr/bin/env python3
"""
StreamViz + Pathway Integration Demo

This demo showcases the native Pathway integration:
- sv.pathway_table() - visualize a Pathway table with live updates
- sv.pathway_stat() - display a single value from a Pathway reduction
- sv.pathway_metric() - time series from windowed Pathway aggregations

Requirements:
    pip install stream-viz[pathway]

Usage:
    # Terminal 1: Start Redpanda
    docker compose up -d

    # Terminal 2: Start order producer
    python examples/ecommerce_producer.py

    # Terminal 3: Run this demo
    python examples/pathway_integration_demo.py

    # Open http://localhost:3000
"""

import threading
import time

import pathway as pw

import stream_viz as sv


def main():
    # =========================================================================
    # Dashboard Setup
    # =========================================================================
    sv.title("E-Commerce Analytics (Pathway)")

    # Kafka settings
    rdkafka_settings = {
        "bootstrap.servers": "localhost:9092",
        "security.protocol": "plaintext",
        "group.id": "streamviz-pathway-demo",
        "session.timeout.ms": "6000",
        "auto.offset.reset": "latest",
    }

    # Order schema
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
    # Pathway Aggregations
    # =========================================================================

    # 1. Global totals (single row) - for stats
    totals = orders.reduce(
        total_revenue=pw.reducers.sum(pw.this.total),
        order_count=pw.reducers.count(),
    )

    # 2. By region breakdown - for table
    by_region = orders.groupby(pw.this.region).reduce(
        region=pw.this.region,
        revenue=pw.reducers.sum(pw.this.total),
        orders=pw.reducers.count(),
        avg_order=pw.reducers.avg(pw.this.total),
    )

    # 3. By category breakdown - for table
    by_category = orders.groupby(pw.this.category).reduce(
        category=pw.this.category,
        revenue=pw.reducers.sum(pw.this.total),
        orders=pw.reducers.count(),
    )

    # =========================================================================
    # StreamViz Visualization - Native Pathway Integration
    # =========================================================================

    # Stats from global totals
    sv.pathway_stat(totals, column="total_revenue", title="Total Revenue", unit="$")
    sv.pathway_stat(totals, column="order_count", title="Total Orders")

    # Live-updating tables from groupby aggregations
    sv.pathway_table(
        by_region,
        title="Revenue by Region",
        columns=["region", "revenue", "orders", "avg_order"],
    )

    sv.pathway_table(
        by_category,
        title="Revenue by Category",
        columns=["category", "revenue", "orders"],
    )

    # Start the dashboard server
    sv.start(port=3000)

    print("Dashboard: http://localhost:3000")
    print("\nShowing:")
    print("  - Total Revenue & Orders (stats)")
    print("  - Revenue by Region (live table)")
    print("  - Revenue by Category (live table)")
    print("\nPress Ctrl+C to stop\n")

    # Run Pathway in background thread
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
