# Getting Started

## Prerequisites

- Python 3.11+
- Docker (only required for the Kafka/Redpanda demo)

## Installation

```bash
# Basic package - simple demo only
pip install pathway-viz

# Full demo - includes Kafka/Redpanda + Pathway + DuckDB
pip install pathway-viz[demo]
```

## Run demos

```bash
# Simple demo - works immediately after basic install
pathway-viz demo --mode simple

# Full e-commerce demo - requires pathway-viz[demo] and Docker
pathway-viz demo
```

The simple demo shows:

- Live stat, chart, gauge, and table widgets
- Simulated metrics updating in real-time
- No external dependencies required

The full demo includes:

- Kafka/Redpanda message streaming
- Pathway data processing
- DuckDB persistence (data survives restarts)
- Embedded widget examples

## Scaffold a New Project

```bash
# Create a project with Docker files
pathway-viz init my-dashboard
cd my-dashboard

# Start with Docker
docker compose up -d

# Or run without Docker
python pipeline.py --mode simple
```

The e-commerce demo will:

1. Start Kafka (Redpanda) via Docker
2. Generate simulated e-commerce orders
3. Process them through Pathway
4. Display real-time dashboards

**URLs:**

- Dashboard: <http://localhost:3000>
- Portal (embedded widgets): <http://localhost:3001>

## What the Demo Shows

- **Today's Revenue** — Real business metric, resets at midnight
- **Today's Orders** — Order count for the current day
- **Revenue by Region** — Grouped aggregation
- **Orders/sec Chart** — Time series
- **DuckDB Persistence** — Data survives restarts

## Writing Your Own Pipeline

```python
import pathway as pw
import pathway_viz as pv

class OrderSchema(pw.Schema):
    order_id: str
    amount: float
    region: str

# Read from Kafka
orders = pw.io.kafka.read(
    rdkafka_settings={"bootstrap.servers": "localhost:9092"},
    topic="orders",
)

# Aggregations
totals = orders.reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

by_region = orders.groupby(pw.this.region).reduce(
    region=pw.this.region,
    revenue=pw.reducers.sum(pw.this.amount),
)

# Visualize
pv.stat(totals, "revenue", title="Revenue", unit="$")
pv.stat(totals, "count", title="Orders")
pv.table(by_region, title="By Region", columns=["region", "revenue"])

pv.start()
pw.run()
```

## Embedding Widgets

```python
pv.configure(embed=True)
pv.stat("revenue", title="Revenue")
pv.start()
```

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

## Next Steps

- **[Concepts](./concepts.md)** — How Pathway windowing works
- **[Widgets](./widgets.md)** — All widget types
- **[Persistence](./persistence.md)** — DuckDB for surviving restarts
- **[Deployment](./deployment.md)** — Docker, Kubernetes
