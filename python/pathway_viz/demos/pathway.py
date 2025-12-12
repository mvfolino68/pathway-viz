#!/usr/bin/env python3
"""
PathwayViz Demo - Real E-Commerce Analytics

Production-like demo using:
- Kafka/Redpanda for streaming
- Pathway for stream processing with windowed aggregations
- DuckDB for persistence (survives restarts)
- Real business metrics with historical context
- Comparison metrics (vs previous period)
- Alert thresholds

Usage:
    python -m pathway_viz
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

import pathway_viz as pv

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

DATA_DIR = Path(os.getenv("PATHWAYVIZ_DATA_DIR", "./data"))
db = None


def init_database():
    """Initialize DuckDB for persistence."""
    global db
    if not DUCKDB_AVAILABLE:
        return None

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect(str(DATA_DIR / "pathwayviz.duckdb"))

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

    # Snapshots table for time-travel queries
    db.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id VARCHAR PRIMARY KEY,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metric_name VARCHAR,
            metric_value DOUBLE,
            window_start TIMESTAMP,
            window_end TIMESTAMP
        )
    """)

    # Create indexes for time queries
    db.execute("CREATE INDEX IF NOT EXISTS idx_orders_time ON orders(created_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(snapshot_time)")

    return db


def get_today_start() -> datetime:
    """Get midnight of today."""
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_period_start(period_minutes: int) -> datetime:
    """Get start of current period (e.g., current 5-minute window)."""
    now = datetime.now()
    # Align to period boundary
    minutes = (now.hour * 60 + now.minute) // period_minutes * period_minutes
    return now.replace(hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0)


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


def get_previous_period_totals(period_minutes: int = 60) -> dict:
    """Get totals from the previous period for comparison."""
    if not db:
        return {"orders": 0, "revenue": 0}
    period_end = get_period_start(period_minutes)
    period_start = period_end - timedelta(minutes=period_minutes)
    result = db.execute(
        """
        SELECT COUNT(*) as orders, COALESCE(SUM(total), 0) as revenue
        FROM orders WHERE created_at >= ? AND created_at < ?
    """,
        [period_start, period_end],
    ).fetchone()
    return {"orders": result[0], "revenue": result[1]}


def get_current_period_totals(period_minutes: int = 60) -> dict:
    """Get totals from the current period."""
    if not db:
        return {"orders": 0, "revenue": 0}
    period_start = get_period_start(period_minutes)
    result = db.execute(
        """
        SELECT COUNT(*) as orders, COALESCE(SUM(total), 0) as revenue
        FROM orders WHERE created_at >= ?
    """,
        [period_start],
    ).fetchone()
    return {"orders": result[0], "revenue": result[1]}


def get_windowed_aggregates(window_minutes: int = 5, lookback_hours: int = 1) -> list:
    """Get aggregates per window for the last N hours."""
    if not db:
        return []
    cutoff = datetime.now() - timedelta(hours=lookback_hours)
    return db.execute(
        f"""
        SELECT
            DATE_TRUNC('minute', created_at) -
            INTERVAL (EXTRACT(MINUTE FROM created_at)::INT % {window_minutes}) MINUTE as window_start,
            COUNT(*) as orders,
            SUM(total) as revenue
        FROM orders
        WHERE created_at >= ?
        GROUP BY window_start
        ORDER BY window_start
    """,
        [cutoff],
    ).fetchall()


def save_snapshot(
    metric_name: str, value: float, window_start: datetime = None, window_end: datetime = None
):
    """Save a metric snapshot for time-travel queries."""
    if not db:
        return
    snapshot_id = f"{metric_name}_{datetime.now().isoformat()}"
    db.execute(
        """
        INSERT INTO snapshots (snapshot_id, metric_name, metric_value, window_start, window_end)
        VALUES (?, ?, ?, ?, ?)
    """,
        [snapshot_id, metric_name, value, window_start, window_end],
    )


def get_snapshot_at_time(metric_name: str, target_time: datetime) -> float | None:
    """Get the metric value closest to a specific time (time-travel query)."""
    if not db:
        return None
    result = db.execute(
        """
        SELECT metric_value
        FROM snapshots
        WHERE metric_name = ? AND snapshot_time <= ?
        ORDER BY snapshot_time DESC
        LIMIT 1
    """,
        [metric_name, target_time],
    ).fetchone()
    return result[0] if result else None


def get_orders_per_minute(lookback_minutes: int = 5) -> float:
    """Get average orders per minute over lookback period."""
    if not db:
        return 0
    cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
    result = db.execute(
        """
        SELECT COUNT(*) as orders
        FROM orders WHERE created_at >= ?
    """,
        [cutoff],
    ).fetchone()
    return result[0] / lookback_minutes if result else 0


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


def get_category_breakdown() -> list:
    """Get today's revenue by category."""
    if not db:
        return []
    today = get_today_start()
    return db.execute(
        """
        SELECT category, COUNT(*) as orders, SUM(total) as revenue
        FROM orders
        WHERE created_at >= ?
        GROUP BY category
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


def run_producer(stop_event: threading.Event, orders_chart):
    """Run the Kafka producer in a thread."""
    try:
        from kafka import KafkaProducer
    except ImportError:
        print("  Error: kafka-python-ng not installed")
        print("  Run: pip install pathway-viz[kafka]")
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


def run_pathway(stop_event: threading.Event, port: int, widgets: dict, historical_baseline: dict):
    """
    Run the Pathway pipeline in a thread.

    The key insight: Pathway aggregations start from 0, but we need to ADD to
    the historical baseline from DuckDB, not replace it.
    """
    try:
        import pathway as pw
    except ImportError:
        print("  Error: pathway not installed")
        print("  Run: pip install pathway-viz[pathway]")
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

    # Global totals (single row, updates in place) - this is SESSION totals
    session_totals = orders.reduce(
        session_revenue=pw.reducers.sum(pw.this.total),
        session_count=pw.reducers.count(),
        session_avg=pw.reducers.avg(pw.this.total),
    )

    # 5-minute tumbling window for windowed metrics
    # Convert timestamp (ms) to datetime for windowing
    orders_with_time = orders.with_columns(
        event_time=pw.this.timestamp // 1000  # Convert ms to seconds
    )

    windowed_stats = orders_with_time.windowby(
        pw.this.event_time,
        window=pw.temporal.tumbling(duration=300),  # 5 minutes = 300 seconds
    ).reduce(
        window_end=pw.this._pw_window_end,
        window_revenue=pw.reducers.sum(pw.this.total),
        window_count=pw.reducers.count(),
    )

    # By region breakdown (session-only, we'll add to historical)
    by_region = orders.groupby(pw.this.region).reduce(
        region=pw.this.region,
        session_revenue=pw.reducers.sum(pw.this.total),
        session_orders=pw.reducers.count(),
    )

    # By category breakdown
    by_category = orders.groupby(pw.this.category).reduce(
        category=pw.this.category,
        session_revenue=pw.reducers.sum(pw.this.total),
        session_orders=pw.reducers.count(),
    )

    # === SUBSCRIBE TO PATHWAY TABLES AND SEND TO PATHWAYVIZ ===
    # KEY: Add session values to historical baseline!

    # Get widget references
    revenue_widget = widgets["revenue"]
    orders_widget = widgets["orders"]
    avg_order_widget = widgets["avg_order"]
    revenue_chart = widgets["revenue_chart"]
    window_revenue_widget = widgets.get("window_revenue")
    orders_per_min_widget = widgets.get("orders_per_min")
    vs_last_hour_widget = widgets.get("vs_last_hour")

    # Historical baseline values (from DuckDB)
    base_revenue = historical_baseline.get("revenue", 0)
    base_orders = historical_baseline.get("orders", 0)
    base_regions = historical_baseline.get("regions", {})
    base_categories = historical_baseline.get("categories", {})
    prev_hour = historical_baseline.get("prev_hour", {"revenue": 0, "orders": 0})

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

    # Track session values for comparison calculations
    session_state = {"revenue": 0, "orders": 0}

    # Subscribe to session totals - ADD to historical baseline
    def on_totals(key, row, time, is_addition):
        if is_addition and row:
            session_rev = row.get("session_revenue", 0)
            session_cnt = row.get("session_count", 0)

            # Update session state
            session_state["revenue"] = session_rev
            session_state["orders"] = session_cnt

            # Total = historical baseline + session
            total_revenue = base_revenue + session_rev
            total_orders = base_orders + session_cnt

            revenue_widget.send(round(total_revenue, 2))
            orders_widget.send(total_orders)

            # Average is weighted: (base_total + session_total) / (base_count + session_count)
            if total_orders > 0:
                avg = total_revenue / total_orders
                avg_order_widget.send(round(avg, 2))

            # Calculate "vs last hour" comparison
            if vs_last_hour_widget and prev_hour["revenue"] > 0:
                current_hour_rev = session_rev  # Current hour = session since we just started
                pct_change = (
                    (current_hour_rev - prev_hour["revenue"]) / prev_hour["revenue"]
                ) * 100
                vs_last_hour_widget.send(round(pct_change, 1))

            # Save snapshot for time-travel
            save_snapshot("total_revenue", total_revenue)

    pw.io.subscribe(session_totals, on_totals)

    # Subscribe to windowed stats - this shows real stream processing power
    def on_window(key, row, time, is_addition):
        if is_addition and row:
            window_rev = row.get("window_revenue", 0)
            window_cnt = row.get("window_count", 0)
            window_end = row.get("window_end", 0)

            if window_revenue_widget:
                window_revenue_widget.send(round(window_rev, 2))

            # Orders per minute (5-min window / 5)
            if orders_per_min_widget:
                opm = window_cnt / 5.0
                orders_per_min_widget.send(round(opm, 1))

            # Add to revenue chart with proper timestamp
            if window_end:
                revenue_chart.send(round(window_rev, 2), timestamp=float(window_end))

    pw.io.subscribe(windowed_stats, on_window)

    # Subscribe to region breakdown - ADD to historical baseline
    def on_region(key, row, time, is_addition):
        if is_addition and row:
            region = row.get("region", "")
            if region in region_widgets:
                session_rev = row.get("session_revenue", 0)
                base_rev = base_regions.get(region, 0)
                total_rev = base_rev + session_rev
                region_widgets[region].send(round(total_rev, 2))

    pw.io.subscribe(by_region, on_region)

    # Subscribe to category breakdown - ADD to historical baseline
    def on_category(key, row, time, is_addition):
        if is_addition and row:
            category = row.get("category", "")
            if category in category_widgets:
                session_rev = row.get("session_revenue", 0)
                base_rev = base_categories.get(category, 0)
                total_rev = base_rev + session_rev
                category_widgets[category].send(round(total_rev, 2))

    pw.io.subscribe(by_category, on_category)

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
        print("  Run: pip install pathway-viz[pathway]")
        sys.exit(1)

    try:
        from kafka import KafkaProducer  # noqa: F401
    except ImportError:
        print("  Error: kafka-python-ng not installed")
        print("  Run: pip install pathway-viz[kafka]")
        sys.exit(1)

    # Initialize DuckDB for persistence
    init_database()
    if DUCKDB_AVAILABLE:
        print(f"  DuckDB: {DATA_DIR}/pathwayviz.duckdb (data persists across restarts)")
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

    pv.title("E-Commerce Analytics")
    pv.configure(embed=True)

    # Create widgets with real business metric names
    widgets = {
        # Today's metrics (what businesses actually care about)
        "revenue": pv.stat("revenue", title="Today's Revenue", unit="$"),
        "orders": pv.stat("orders", title="Today's Orders"),
        "avg_order": pv.stat("avg_order", title="Avg Order", unit="$"),
        # NEW: Windowed metrics (demonstrates stream processing)
        "window_revenue": pv.stat("window_revenue", title="5-Min Window", unit="$"),
        "orders_per_min": pv.stat("orders_per_min", title="Orders/Min", alert_below=2.0),
        # NEW: Comparison metric (vs previous period)
        "vs_last_hour": pv.stat("vs_last_hour", title="vs Last Hour", unit="%", alert_below=-20.0),
        # Charts
        "revenue_chart": pv.chart(
            "revenue_chart", title="Revenue (5-min windows)", unit="$", color="#00ff88"
        ),
        "orders_chart": pv.chart("orders_chart", title="Orders/sec", color="#00d4ff"),
        # Region stats (one per region)
        "us_east": pv.stat("us_east", title="US-East", unit="$"),
        "us_west": pv.stat("us_west", title="US-West", unit="$"),
        "europe": pv.stat("europe", title="Europe", unit="$"),
        "asia": pv.stat("asia", title="Asia", unit="$"),
        # Category stats
        "electronics": pv.stat("electronics", title="Electronics", unit="$"),
        "apparel": pv.stat("apparel", title="Apparel", unit="$"),
        "books": pv.stat("books", title="Books", unit="$"),
        "grocery": pv.stat("grocery", title="Grocery", unit="$"),
    }

    pv.start(port)

    # Build historical baseline from DuckDB
    # This is the KEY fix: we track historical totals separately and ADD Pathway's
    # session aggregations to them, rather than letting Pathway overwrite them.
    historical_baseline = {
        "revenue": 0,
        "orders": 0,
        "regions": {},
        "categories": {},
        "prev_hour": {"revenue": 0, "orders": 0},
    }

    if DUCKDB_AVAILABLE:
        print("  Loading historical data...")
        today = get_todays_totals()

        # Store baseline for Pathway to add to
        historical_baseline["revenue"] = today["revenue"]
        historical_baseline["orders"] = today["orders"]

        if today["orders"] > 0:
            # Send initial values to widgets
            widgets["revenue"].send(round(today["revenue"], 2))
            widgets["orders"].send(today["orders"])
            widgets["avg_order"].send(round(today["revenue"] / today["orders"], 2))
            print(f"    Today: {today['orders']} orders, ${today['revenue']:.2f} revenue")

        # Load previous hour for comparison
        prev_hour = get_previous_period_totals(60)
        historical_baseline["prev_hour"] = prev_hour
        if prev_hour["revenue"] > 0:
            print(f"    Last hour: ${prev_hour['revenue']:.2f} revenue")

        # Load windowed data for charts
        for window_start, _, revenue in get_windowed_aggregates(5, 1):
            widgets["revenue_chart"].send(round(revenue, 2), timestamp=window_start.timestamp())

        # Load region breakdown and store baseline
        for region, _, revenue in get_region_breakdown():
            region_key = region.lower().replace("-", "_")
            historical_baseline["regions"][region] = revenue
            if region_key in widgets:
                widgets[region_key].send(round(revenue, 2))

        # Load category breakdown and store baseline
        for cat, _, revenue in get_category_breakdown():
            historical_baseline["categories"][cat] = revenue
            cat_key = cat.lower()
            if cat_key in widgets:
                widgets[cat_key].send(round(revenue, 2))

        print("  Historical data loaded!")
        print(
            f"    Baseline: ${historical_baseline['revenue']:.2f} revenue, {historical_baseline['orders']} orders"
        )

    stop_event = threading.Event()

    # Start producer thread (pass orders_chart widget for orders/sec tracking)
    producer_thread = threading.Thread(
        target=run_producer, args=(stop_event, widgets["orders_chart"]), daemon=True
    )
    producer_thread.start()

    # Start Pathway thread with widget references AND historical baseline
    pathway_thread = threading.Thread(
        target=run_pathway, args=(stop_event, port, widgets, historical_baseline), daemon=True
    )
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
