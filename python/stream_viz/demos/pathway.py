#!/usr/bin/env python3
"""
StreamViz Demo - Real E-Commerce Analytics

Production-like demo using:
- Kafka/Redpanda for streaming
- Pathway for stream processing
- DuckDB for persistence (survives restarts)
- Real business metrics (today's orders, hourly breakdown)

Usage:
    python -m stream_viz
"""

import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import stream_viz as sv

# Optional DuckDB for persistence
try:
    import duckdb

    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None


def check_docker() -> bool:
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def check_docker_compose() -> bool:
    """Check if docker compose is available."""
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_kafka_running() -> bool:
    """Check if Kafka/Redpanda container is running."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=get_project_root(),
        )
        if result.returncode != 0:
            return False
        # Check if redpanda service is running
        output = result.stdout.strip()
        if not output:
            return False
        # docker compose ps --format json returns one JSON object per line
        for line in output.split("\n"):
            if line.strip():
                try:
                    container = json.loads(line)
                    if "redpanda" in container.get("Name", "").lower():
                        return container.get("State") == "running"
                except json.JSONDecodeError:
                    continue
        return False
    except Exception:
        return False


def get_project_root() -> Path:
    """Get the project root directory (where docker-compose.yml is)."""
    # Walk up from this file to find docker-compose.yml
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docker-compose.yml").exists():
            return parent
    # Fallback to cwd
    return Path.cwd()


def start_kafka() -> bool:
    """Start Kafka/Redpanda via docker compose."""
    project_root = get_project_root()
    compose_file = project_root / "docker-compose.yml"

    if not compose_file.exists():
        print("  Error: docker-compose.yml not found")
        return False

    print("  Starting Kafka (Redpanda)...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"  Error starting Docker: {result.stderr}")
        return False

    # Wait for Kafka to be ready
    print("  Waiting for Kafka to be ready...", end="", flush=True)
    for _ in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        if is_kafka_running():
            print(" ready!")
            return True

    print(" timeout!")
    return False


def stop_kafka():
    """Stop Kafka/Redpanda containers."""
    project_root = get_project_root()
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=project_root,
        capture_output=True,
    )


# =============================================================================
# DuckDB Persistence (Optional but recommended for production)
# =============================================================================

DATA_DIR = Path(os.getenv("STREAMVIZ_DATA_DIR", "./data"))
db = None


def init_database():
    """Initialize DuckDB for persistence."""
    global db
    if not DUCKDB_AVAILABLE:
        return None

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect(str(DATA_DIR / "streamviz.duckdb"))

    # Orders table
    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR PRIMARY KEY,
            total DOUBLE,
            region VARCHAR,
            category VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index for time queries
    db.execute("CREATE INDEX IF NOT EXISTS idx_orders_time ON orders(created_at)")

    return db


def get_today_start() -> datetime:
    """Get midnight of today."""
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_todays_totals() -> dict:
    """Get today's totals from DuckDB."""
    if not db:
        return {"orders": 0, "revenue": 0}
    today = get_today_start()
    result = db.execute(
        """
        SELECT COUNT(*) as orders, COALESCE(SUM(total), 0) as revenue
        FROM orders WHERE created_at >= ?
    """,
        [today],
    ).fetchone()
    return {"orders": result[0], "revenue": result[1]}


def get_hourly_breakdown(hours: int = 24) -> list:
    """Get hourly aggregates for charts."""
    if not db:
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    return db.execute(
        """
        SELECT
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as orders,
            SUM(total) as revenue
        FROM orders
        WHERE created_at >= ?
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour
    """,
        [cutoff],
    ).fetchall()


def get_region_breakdown() -> list:
    """Get today's revenue by region."""
    if not db:
        return []
    today = get_today_start()
    return db.execute(
        """
        SELECT region, COUNT(*) as orders, SUM(total) as revenue
        FROM orders
        WHERE created_at >= ?
        GROUP BY region
        ORDER BY revenue DESC
    """,
        [today],
    ).fetchall()


def persist_order(order: dict):
    """Save order to DuckDB."""
    if not db:
        return
    db.execute(
        """
        INSERT OR REPLACE INTO orders (order_id, total, region, category, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        [order["order_id"], order["total"], order["region"], order["category"], datetime.now()],
    )


def serve_portal(streamviz_port: int, portal_port: int):
    """Serve the e-commerce portal HTML page."""
    import http.server
    import socketserver

    # Load and template the HTML
    html_path = Path(__file__).parent / "portal.html"
    html_content = html_path.read_text()
    html_content = html_content.replace("{{PORT}}", str(streamviz_port))

    class PortalHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html_content.encode())

        def log_message(self, format, *args):
            pass  # Suppress logging

    def run_server():
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", portal_port), PortalHandler) as httpd:
                httpd.serve_forever()
        except Exception as e:
            print(f"  Error starting portal server: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    # Give the server a moment to start
    time.sleep(0.5)


# Product catalog for order generation
PRODUCTS = {
    "laptop": {"price": 999.99, "category": "Electronics"},
    "phone": {"price": 699.99, "category": "Electronics"},
    "headphones": {"price": 149.99, "category": "Electronics"},
    "shirt": {"price": 29.99, "category": "Apparel"},
    "shoes": {"price": 89.99, "category": "Apparel"},
    "book": {"price": 19.99, "category": "Books"},
    "coffee": {"price": 12.99, "category": "Grocery"},
}

REGIONS = ["US-East", "US-West", "Europe", "Asia"]


def generate_order() -> dict:
    """Generate a random order."""
    product_name = random.choice(list(PRODUCTS.keys()))
    product = PRODUCTS[product_name]
    quantity = random.choices([1, 2, 3], weights=[70, 25, 5])[0]

    return {
        "order_id": str(uuid.uuid4())[:8],
        "timestamp": int(time.time() * 1000),
        "product": product_name,
        "category": product["category"],
        "quantity": quantity,
        "price": product["price"],
        "total": round(product["price"] * quantity, 2),
        "region": random.choice(REGIONS),
    }


def run_producer(stop_event: threading.Event, orders_chart):
    """Run the Kafka producer in a thread."""
    try:
        from kafka import KafkaProducer
    except ImportError:
        print("  Error: kafka-python-ng not installed")
        print("  Run: pip install stream-viz[kafka]")
        return

    # Wait a moment for Kafka to be fully ready
    time.sleep(2)

    try:
        producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    except Exception as e:
        print(f"  Error connecting to Kafka: {e}")
        return

    count = 0
    orders_this_second = 0
    last_second = int(time.time())

    while not stop_event.is_set():
        order = generate_order()
        producer.send("orders", order)

        # Persist to DuckDB for historical data
        persist_order(order)

        count += 1
        orders_this_second += 1

        # Track orders per second for the chart
        current_second = int(time.time())
        if current_second != last_second:
            orders_chart.send(orders_this_second)
            orders_this_second = 0
            last_second = current_second

        time.sleep(random.uniform(0.2, 0.6))

    producer.close()


def run_pathway(stop_event: threading.Event, port: int, widgets: dict):
    """Run the Pathway pipeline in a thread."""
    try:
        import pathway as pw
    except ImportError:
        print("  Error: pathway not installed")
        print("  Run: pip install stream-viz[pathway]")
        return

    class OrderSchema(pw.Schema):
        order_id: str
        timestamp: int
        product: str
        category: str
        quantity: int
        price: float
        total: float
        region: str

    kafka_settings = {
        "bootstrap.servers": "localhost:9092",
        "security.protocol": "plaintext",
        "group.id": "streamviz-demo-" + str(int(time.time())),
        "auto.offset.reset": "latest",
    }

    orders = pw.io.kafka.read(
        kafka_settings,
        topic="orders",
        format="json",
        schema=OrderSchema,
        autocommit_duration_ms=500,
    )

    # === AGGREGATIONS ===

    # Global totals (single row, updates in place)
    totals = orders.reduce(
        total_revenue=pw.reducers.sum(pw.this.total),
        order_count=pw.reducers.count(),
        avg_order=pw.reducers.avg(pw.this.total),
    )

    # By region breakdown
    by_region = orders.groupby(pw.this.region).reduce(
        region=pw.this.region,
        revenue=pw.reducers.sum(pw.this.total),
        orders=pw.reducers.count(),
    )

    # By category breakdown
    by_category = orders.groupby(pw.this.category).reduce(
        category=pw.this.category,
        revenue=pw.reducers.sum(pw.this.total),
        orders=pw.reducers.count(),
    )

    # === SUBSCRIBE TO PATHWAY TABLES AND SEND TO STREAMVIZ ===

    # Get widget references
    revenue_widget = widgets["revenue"]
    orders_widget = widgets["orders"]
    avg_order_widget = widgets["avg_order"]
    revenue_chart = widgets["revenue_chart"]

    # Region widgets
    region_widgets = {
        "US-East": widgets["us_east"],
        "US-West": widgets["us_west"],
        "Europe": widgets["europe"],
        "Asia": widgets["asia"],
    }

    # Category widgets
    category_widgets = {
        "Electronics": widgets["electronics"],
        "Apparel": widgets["apparel"],
        "Books": widgets["books"],
        "Grocery": widgets["grocery"],
    }

    # Subscribe to totals and send to stats
    def on_totals(key, row, time, is_addition):
        if is_addition and row:
            revenue_widget.send(round(row.get("total_revenue", 0), 2))
            orders_widget.send(row.get("order_count", 0))
            avg = row.get("avg_order", 0)
            if avg:
                avg_order_widget.send(round(avg, 2))

    pw.io.subscribe(totals, on_totals)

    # Subscribe to region breakdown - update individual stat widgets
    def on_region(key, row, time, is_addition):
        if is_addition and row:
            region = row.get("region", "")
            if region in region_widgets:
                region_widgets[region].send(round(row.get("revenue", 0), 2))

    pw.io.subscribe(by_region, on_region)

    # Subscribe to category breakdown - update individual stat widgets
    def on_category(key, row, time, is_addition):
        if is_addition and row:
            category = row.get("category", "")
            if category in category_widgets:
                category_widgets[category].send(round(row.get("revenue", 0), 2))

    pw.io.subscribe(by_category, on_category)

    # Subscribe to individual orders for the chart - accumulate revenue
    running_revenue = [0]  # Use list to allow mutation in closure

    def on_order(key, row, time, is_addition):
        if is_addition and row:
            running_revenue[0] += row.get("total", 0)
            revenue_chart.send(round(running_revenue[0], 2))

    pw.io.subscribe(orders, on_order)

    pw.run(monitoring_level=pw.MonitoringLevel.NONE)


def run_pathway_demo(port: int = 3000):
    """
    Production-like demo with real Kafka/Redpanda streaming.

    Features:
    - Auto-starts Docker containers
    - DuckDB persistence (survives restarts)
    - Real business metrics (today's totals)
    """
    print()
    print("  ╔═══════════════════════════════════════════════════════╗")
    print("  ║     StreamViz - Real-Time E-Commerce Analytics        ║")
    print("  ╚═══════════════════════════════════════════════════════╝")
    print()

    # Check prerequisites
    if not check_docker():
        print("  Error: Docker not found. Please install Docker.")
        sys.exit(1)

    if not check_docker_compose():
        print("  Error: docker compose not found.")
        sys.exit(1)

    # Check for required packages
    try:
        import pathway  # noqa: F401
    except ImportError:
        print("  Error: pathway not installed")
        print("  Run: pip install stream-viz[pathway]")
        sys.exit(1)

    try:
        from kafka import KafkaProducer  # noqa: F401
    except ImportError:
        print("  Error: kafka-python-ng not installed")
        print("  Run: pip install stream-viz[kafka]")
        sys.exit(1)

    # Initialize DuckDB for persistence
    init_database()
    if DUCKDB_AVAILABLE:
        print(f"  DuckDB: {DATA_DIR}/streamviz.duckdb (data persists across restarts)")
    else:
        print("  DuckDB not installed - data will not persist")
        print("  Install with: pip install duckdb")

    # Start Kafka if not running
    kafka_was_running = is_kafka_running()
    if not kafka_was_running:
        if not start_kafka():
            print("  Failed to start Kafka. Exiting.")
            sys.exit(1)
    else:
        print("  Kafka (Redpanda) already running")

    # Serve the portal HTML
    portal_port = port + 1
    serve_portal(port, portal_port)

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │                        URLS                             │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │  Portal:    http://localhost:{portal_port:<26}│")
    print(f"  │  Dashboard: http://localhost:{port:<26}│")
    print("  └─────────────────────────────────────────────────────────┘")
    print()
    print("  Press Ctrl+C to stop")
    print()

    sv.title("E-Commerce Analytics")
    sv.configure(embed=True)

    # Create widgets with real business metric names
    widgets = {
        # Today's metrics (what businesses actually care about)
        "revenue": sv.stat("revenue", title="Today's Revenue", unit="$"),
        "orders": sv.stat("orders", title="Today's Orders"),
        "avg_order": sv.stat("avg_order", title="Avg Order", unit="$"),
        # Charts
        "revenue_chart": sv.chart(
            "revenue_chart", title="Revenue (Last 24h)", unit="$", color="#00ff88"
        ),
        "orders_chart": sv.chart("orders_chart", title="Orders/sec", color="#00d4ff"),
        # Region stats (one per region)
        "us_east": sv.stat("us_east", title="US-East", unit="$"),
        "us_west": sv.stat("us_west", title="US-West", unit="$"),
        "europe": sv.stat("europe", title="Europe", unit="$"),
        "asia": sv.stat("asia", title="Asia", unit="$"),
        # Category stats
        "electronics": sv.stat("electronics", title="Electronics", unit="$"),
        "apparel": sv.stat("apparel", title="Apparel", unit="$"),
        "books": sv.stat("books", title="Books", unit="$"),
        "grocery": sv.stat("grocery", title="Grocery", unit="$"),
    }

    sv.start(port)

    # Load historical data from DuckDB (this is what makes restarts work!)
    if DUCKDB_AVAILABLE:
        print("  Loading historical data...")
        today = get_todays_totals()
        if today["orders"] > 0:
            widgets["revenue"].send(round(today["revenue"], 2))
            widgets["orders"].send(today["orders"])
            widgets["avg_order"].send(round(today["revenue"] / today["orders"], 2))
            print(f"    Today: {today['orders']} orders, ${today['revenue']:.2f} revenue")

        # Load hourly data for charts
        for hour, _, revenue in get_hourly_breakdown(24):
            widgets["revenue_chart"].send(round(revenue, 2), timestamp=hour.timestamp())

        # Load region breakdown
        for region, _, revenue in get_region_breakdown():
            region_key = region.lower().replace("-", "_")
            if region_key in widgets:
                widgets[region_key].send(round(revenue, 2))

        print("  Historical data loaded!")

    stop_event = threading.Event()

    # Start producer thread (pass orders_chart widget for orders/sec tracking)
    producer_thread = threading.Thread(
        target=run_producer, args=(stop_event, widgets["orders_chart"]), daemon=True
    )
    producer_thread.start()

    # Start Pathway thread with widget references
    pathway_thread = threading.Thread(
        target=run_pathway, args=(stop_event, port, widgets), daemon=True
    )
    pathway_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopping...")
        stop_event.set()

        sv.stop()

        # Only stop Kafka if we started it
        if not kafka_was_running:
            print("  Stopping Kafka containers...")
            stop_kafka()

        print("  Done.")


if __name__ == "__main__":
    run_pathway_demo()
