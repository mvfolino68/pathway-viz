# State Persistence

By default, StreamViz is ephemeral—restart the app and all data is lost. This page covers strategies for production persistence.

## The Problem

```python
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
sv.stat(totals, "revenue", title="Revenue")
```

This accumulates revenue **since app start**. If you restart:

- Pathway resets its internal state
- StreamViz shows $0
- Historical data is gone

## Solution Overview

| Approach                   | Best For                                             | Complexity |
| -------------------------- | ---------------------------------------------------- | ---------- |
| **Pathway Persistence**    | Checkpointing aggregation state                      | Low        |
| **DuckDB**                 | Historical queries, dashboards that survive restarts | Medium     |
| **Redis**                  | Distributed state, multiple instances                | Medium     |
| **PostgreSQL/TimescaleDB** | Enterprise, time-series analytics                    | High       |

---

## Pathway Persistence (Recommended)

Pathway can checkpoint its internal state and restore on restart.

### Enable Checkpointing

```python
import pathway as pw

# Configure Kafka with persistent consumer ID
orders = pw.io.kafka.read(
    rdkafka_settings={
        "bootstrap.servers": "localhost:9092",
        "group.id": "streamviz-orders",  # Consistent group ID
    },
    topic="orders",
    format="json",
    schema=OrderSchema,
    persistent_id="orders-source",  # Enables offset tracking
)

# Your aggregations
totals = orders.reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

# StreamViz
sv.stat(totals, "revenue", title="Revenue")
sv.start()

# Run with persistence
pw.run(
    monitoring_level=pw.MonitoringLevel.NONE,
    persistence_config=pw.PersistenceConfig.simple_config(
        pw.PersistentStorageConfig.filesystem("./pathway_state"),
        persistence_mode=pw.PersistenceMode.PERSISTING,
    ),
)
```

### How It Works

1. Pathway saves state snapshots to `./pathway_state/`
2. On restart, Pathway restores from the last checkpoint
3. Kafka consumer resumes from last committed offset
4. Aggregations continue from where they left off

### Limitations

- Only restores Pathway's internal state
- StreamViz ring buffers (chart history) still reset
- Requires consistent `persistent_id` on sources

---

## DuckDB Persistence

DuckDB is a lightweight embedded database perfect for:

- Storing historical metrics
- Loading last known values on startup
- Querying historical data for dashboards

### Basic Setup

```python
import duckdb
from datetime import datetime
from pathlib import Path

# Initialize database
db_path = Path("./data/streamviz.duckdb")
db_path.parent.mkdir(exist_ok=True)
db = duckdb.connect(str(db_path))

# Create tables
db.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        widget_id VARCHAR,
        value DOUBLE,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSON
    )
""")

db.execute("""
    CREATE TABLE IF NOT EXISTS chart_points (
        widget_id VARCHAR,
        value DOUBLE,
        timestamp TIMESTAMP,
        PRIMARY KEY (widget_id, timestamp)
    )
""")
```

### Persistent Widgets

Wrap StreamViz widgets to also persist to DuckDB:

```python
import stream_viz as sv
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PersistentStat:
    """Stat widget that persists to DuckDB."""
    widget: object
    widget_id: str
    db: duckdb.DuckDBPyConnection

    def send(self, value: float, metadata: dict = None):
        # Send to StreamViz
        self.widget.send(value)

        # Persist to DuckDB
        self.db.execute(
            "INSERT INTO metrics (widget_id, value, timestamp, metadata) VALUES (?, ?, ?, ?)",
            [self.widget_id, value, datetime.now(), json.dumps(metadata or {})]
        )

@dataclass
class PersistentChart:
    """Chart widget that persists to DuckDB."""
    widget: object
    widget_id: str
    db: duckdb.DuckDBPyConnection

    def send(self, value: float, timestamp: float = None):
        ts = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()

        # Send to StreamViz
        self.widget.send(value, timestamp)

        # Persist to DuckDB (upsert)
        self.db.execute("""
            INSERT OR REPLACE INTO chart_points (widget_id, value, timestamp)
            VALUES (?, ?, ?)
        """, [self.widget_id, value, ts])


def persistent_stat(widget_id: str, db: duckdb.DuckDBPyConnection, **kwargs):
    """Create a stat widget with DuckDB persistence."""
    widget = sv.stat(widget_id, **kwargs)
    return PersistentStat(widget=widget, widget_id=widget_id, db=db)

def persistent_chart(widget_id: str, db: duckdb.DuckDBPyConnection, **kwargs):
    """Create a chart widget with DuckDB persistence."""
    widget = sv.chart(widget_id, **kwargs)
    return PersistentChart(widget=widget, widget_id=widget_id, db=db)
```

### Loading Historical Data on Startup

```python
def load_last_values(db: duckdb.DuckDBPyConnection) -> dict:
    """Load most recent value for each widget."""
    result = db.execute("""
        SELECT widget_id, value
        FROM metrics
        WHERE (widget_id, timestamp) IN (
            SELECT widget_id, MAX(timestamp)
            FROM metrics
            GROUP BY widget_id
        )
    """).fetchall()
    return {row[0]: row[1] for row in result}

def load_chart_history(db: duckdb.DuckDBPyConnection, widget_id: str, limit: int = 200) -> list:
    """Load recent chart points."""
    result = db.execute("""
        SELECT value, timestamp
        FROM chart_points
        WHERE widget_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, [widget_id, limit]).fetchall()
    return [(row[0], row[1].timestamp()) for row in reversed(result)]


# On startup
last_values = load_last_values(db)
if "revenue" in last_values:
    revenue_widget.send(last_values["revenue"])

# Load chart history
for value, ts in load_chart_history(db, "latency"):
    latency_widget.send(value, timestamp=ts)
```

### Full Example

See [E-commerce Example](./examples/ecommerce.md) for a complete implementation.

---

## Redis Persistence

For distributed deployments or when you need shared state across instances.

```python
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0)

class RedisBackedStat:
    def __init__(self, widget_id: str, widget):
        self.widget_id = widget_id
        self.widget = widget
        self.key = f"streamviz:{widget_id}"

    def send(self, value: float):
        # Send to StreamViz
        self.widget.send(value)

        # Persist to Redis
        r.set(f"{self.key}:latest", value)
        r.lpush(f"{self.key}:history", json.dumps({
            "value": value,
            "timestamp": datetime.now().isoformat()
        }))
        r.ltrim(f"{self.key}:history", 0, 999)  # Keep last 1000

    def load_latest(self) -> float | None:
        val = r.get(f"{self.key}:latest")
        return float(val) if val else None
```

---

## Combining Pathway + DuckDB

The most robust approach combines:

1. **Pathway persistence** for aggregation state recovery
2. **DuckDB** for historical queries and chart pre-loading

```python
import pathway as pw
import stream_viz as sv
import duckdb

# DuckDB for history
db = duckdb.connect("./data/streamviz.duckdb")

# Pathway pipeline
orders = pw.io.kafka.read(..., persistent_id="orders")

totals = orders.reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

# Subscribe to persist to DuckDB
def persist_totals(key, row, time, is_addition):
    if is_addition:
        db.execute(
            "INSERT INTO metrics (widget_id, value, timestamp) VALUES (?, ?, ?)",
            ["revenue", row.get("revenue", 0), datetime.now()]
        )

pw.io.subscribe(totals, on_change=persist_totals)

# StreamViz (also subscribes)
sv.stat(totals, "revenue", title="Revenue")
sv.start()

# Run with Pathway persistence
pw.run(
    persistence_config=pw.PersistenceConfig.simple_config(
        pw.PersistentStorageConfig.filesystem("./pathway_state"),
        persistence_mode=pw.PersistenceMode.PERSISTING,
    ),
)
```

---

## Docker Volume for Persistence

Mount a volume to preserve state across container restarts:

```yaml
services:
  streamviz:
    image: stream-viz
    volumes:
      - streamviz-data:/app/data # DuckDB, Pathway state
    environment:
      - STREAMVIZ_DATA_DIR=/app/data

volumes:
  streamviz-data:
```

```bash
docker run -p 3000:3000 \
  -v streamviz-data:/app/data \
  -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
  stream-viz python my_pipeline.py
```

---

## Best Practices

1. **Always use consistent IDs** — Widget IDs and Pathway `persistent_id` must be stable across restarts

2. **Separate hot and cold data** — Use DuckDB for recent data (hours/days), archive older data to S3/PostgreSQL

3. **Backup the state directory** — `./pathway_state/` and `./data/` contain your state

4. **Use transactions for DuckDB** — Batch writes for better performance:

   ```python
   db.execute("BEGIN TRANSACTION")
   # ... many inserts ...
   db.execute("COMMIT")
   ```

5. **Set retention policies** — Don't let tables grow unbounded:
   ```sql
   DELETE FROM metrics WHERE timestamp < NOW() - INTERVAL '7 days'
   ```
