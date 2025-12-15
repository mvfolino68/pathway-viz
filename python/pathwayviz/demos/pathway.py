#!/usr/bin/env python3
"""PathwayViz Demo - Real E-Commerce Analytics

Production-like demo using:
- Kafka/Redpanda for streaming
- Pathway for stream processing with windowed aggregations
- Real business metrics
- Alert thresholds

Usage:
    python -m pathway_viz
"""

import json
import random
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pathwayviz as pv


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


def _find_compose_file() -> tuple[Path | None, Path | None]:
    """Find docker-compose.yml. Returns (compose_file, compose_dir) or (None, None)."""
    if (Path.cwd() / "docker-compose.yml").exists():
        return Path.cwd() / "docker-compose.yml", Path.cwd()

    from pathwayviz.docker import get_compose_file

    try:
        compose_file = get_compose_file()
        return compose_file, compose_file.parent
    except FileNotFoundError:
        return None, None


def is_kafka_running() -> bool:
    """Check if Kafka/Redpanda container is running."""
    try:
        compose_file, compose_dir = _find_compose_file()
        if not compose_file:
            return False

        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=compose_dir,
        )
        if result.returncode != 0:
            return False

        output = result.stdout.strip()
        if not output:
            return False

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


def start_kafka() -> bool:
    """Start Kafka/Redpanda via docker compose."""
    compose_file, compose_dir = _find_compose_file()
    if not compose_file:
        print("  Error: docker-compose.yml not found")
        return False

    print("  Starting Kafka (Redpanda)...")
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        cwd=compose_dir,
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
    compose_file, compose_dir = _find_compose_file()
    if compose_file:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down"],
            cwd=compose_dir,
            capture_output=True,
        )


def serve_portal(pathwayviz_port: int, portal_port: int):
    """Serve the e-commerce portal HTML page."""
    import http.server
    import socketserver

    # Load and template the HTML
    html_path = Path(__file__).parent / "portal.html"
    html_content = html_path.read_text()
    html_content = html_content.replace("{{PORT}}", str(pathwayviz_port))

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


def run_producer(stop_event: threading.Event):
    """Run the Kafka producer in a thread."""
    try:
        from kafka import KafkaProducer
    except ImportError:
        print("  Error: kafka-python-ng not installed")
        print("  Run: pip install pathway-viz[demo]")
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

    while not stop_event.is_set():
        order = generate_order()
        producer.send("orders", order)
        time.sleep(random.uniform(0.2, 0.6))

    producer.close()


def setup_pathway_pipeline(port: int):
    """Build the Pathway pipeline and register widgets. Returns a function to run the pipeline."""
    import pathway as pw

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
        "group.id": "pathwayviz-demo-" + str(int(time.time())),
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
    session_totals = orders.reduce(
        revenue=pw.reducers.sum(pw.this.total),
        order_count=pw.reducers.count(),
        avg_order=pw.reducers.avg(pw.this.total),
    )

    # Windowed aggregations for orders/sec chart (1-second windows for smoother line)
    # timestamp is INT (unix ms), so use INT duration
    WINDOW_MS = 1000  # 1 second windows
    windowed = orders.windowby(
        pw.this.timestamp,
        window=pw.temporal.tumbling(duration=WINDOW_MS),
    ).reduce(
        window_end=pw.this._pw_window_end,
        order_count=pw.reducers.count(),
        window_revenue=pw.reducers.sum(pw.this.total),
    )

    # By region breakdown table
    by_region = orders.groupby(pw.this.region).reduce(
        region=pw.this.region,
        revenue=pw.reducers.sum(pw.this.total),
        orders=pw.reducers.count(),
    )

    # By category breakdown table
    by_category = orders.groupby(pw.this.category).reduce(
        category=pw.this.category,
        revenue=pw.reducers.sum(pw.this.total),
        orders=pw.reducers.count(),
    )

    # By region - create individual tables for each region
    us_east = orders.filter(pw.this.region == "US-East").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )
    us_west = orders.filter(pw.this.region == "US-West").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )
    europe = orders.filter(pw.this.region == "Europe").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )
    asia = orders.filter(pw.this.region == "Asia").reduce(revenue=pw.reducers.sum(pw.this.total))

    # By category - create individual tables for each category
    electronics = orders.filter(pw.this.category == "Electronics").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )
    apparel = orders.filter(pw.this.category == "Apparel").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )
    books = orders.filter(pw.this.category == "Books").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )
    grocery = orders.filter(pw.this.category == "Grocery").reduce(
        revenue=pw.reducers.sum(pw.this.total)
    )

    # === REGISTER WIDGETS WITH PATHWAY TABLES ===
    # Widget IDs must match what portal.html expects

    pv.title("E-Commerce Analytics")
    pv.configure(embed=True)

    # Key metrics (IDs: revenue, orders, avg_order)
    pv.stat(session_totals, "revenue", id="revenue", title="Today's Revenue", unit="$", embed=True)
    pv.stat(session_totals, "order_count", id="orders", title="Today's Orders", embed=True)
    pv.stat(session_totals, "avg_order", id="avg_order", title="Avg Order", unit="$", embed=True)

    # Charts (IDs: revenue_chart, orders_chart)
    # Revenue: use session_totals for cumulative (keeps increasing over time)
    pv.chart(
        session_totals,
        "revenue",
        id="revenue_chart",
        title="Cumulative Revenue",
        unit="$",
        color="#00ff88",
        embed=True,
    )
    # Orders/sec: 1-second windows means order_count = orders per second
    pv.chart(
        windowed,
        "order_count",
        x_column="window_end",
        id="orders_chart",
        title="Orders/sec",
        color="#00d4ff",
        embed=True,
    )

    # Breakdown tables (more useful for business analytics)
    pv.table(by_region, title="Revenue by Region", columns=["region", "revenue", "orders"])
    pv.table(by_category, title="Revenue by Category", columns=["category", "revenue", "orders"])

    # Region stats (IDs: us_east, us_west, europe, asia)
    pv.stat(us_east, "revenue", id="us_east", title="US-East", unit="$", embed=True)
    pv.stat(us_west, "revenue", id="us_west", title="US-West", unit="$", embed=True)
    pv.stat(europe, "revenue", id="europe", title="Europe", unit="$", embed=True)
    pv.stat(asia, "revenue", id="asia", title="Asia", unit="$", embed=True)

    # Category stats (IDs: electronics, apparel, books, grocery)
    pv.stat(electronics, "revenue", id="electronics", title="Electronics", unit="$", embed=True)
    pv.stat(apparel, "revenue", id="apparel", title="Apparel", unit="$", embed=True)
    pv.stat(books, "revenue", id="books", title="Books", unit="$", embed=True)
    pv.stat(grocery, "revenue", id="grocery", title="Grocery", unit="$", embed=True)

    # Start server
    pv.start(port)

    # Return runner function
    def run():
        pw.run(monitoring_level=pw.MonitoringLevel.NONE)

    return run


def run_pathway_demo(port: int = 3000):
    """
    Production-like demo with real Kafka/Redpanda streaming.

    Features:
    - Auto-starts Docker containers
    - Real business metrics
    """
    print()
    print("  ╔═══════════════════════════════════════════════════════╗")
    print("  ║    PathwayViz - Real-Time E-Commerce Analytics        ║")
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
        print("  Run: pip install pathway-viz[demo]")
        sys.exit(1)

    try:
        from kafka import KafkaProducer  # noqa: F401
    except ImportError:
        print("  Error: kafka-python-ng not installed")
        print("  Run: pip install pathway-viz[demo]")
        sys.exit(1)

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

    # Setup Pathway pipeline and widgets (this also starts the server)
    try:
        run_pipeline = setup_pathway_pipeline(port)
    except ImportError:
        print("  Error: pathway not installed")
        print("  Run: pip install pathway-viz[demo]")
        sys.exit(1)

    stop_event = threading.Event()

    # Start producer thread
    producer_thread = threading.Thread(target=run_producer, args=(stop_event,), daemon=True)
    producer_thread.start()

    # Start Pathway in background thread
    pathway_thread = threading.Thread(target=run_pipeline, daemon=True)
    pathway_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopping...")
        stop_event.set()

        pv.stop()

        # Only stop Kafka if we started it
        if not kafka_was_running:
            print("  Stopping Kafka containers...")
            stop_kafka()

        print("  Done.")


if __name__ == "__main__":
    run_pathway_demo()
