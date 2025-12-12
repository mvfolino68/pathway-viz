# My PathwayViz Dashboard

Real-time dashboard powered by [PathwayViz](https://github.com/mvfolino68/pathway-viz).

## Quick Start

### Option 1: Simple Demo (No Docker)

```bash
pip install pathway-viz
python pipeline.py --mode simple
```

Open <http://localhost:3000>

### Option 2: Full Stack (Docker)

```bash
docker compose up -d
```

This starts:

- **Redpanda** (Kafka-compatible) on port 9092
- **PathwayViz** dashboard on port 3000

## Project Structure

```text
.
├── docker-compose.yml   # Full stack: Redpanda + PathwayViz
├── Dockerfile           # Container for your pipeline
├── pipeline.py          # Your streaming pipeline
└── README.md
```

## Customizing

Edit `pipeline.py` to:

1. **Change Kafka topics** — Update the `topic="events"` parameter
2. **Add widgets** — Use `pv.stat()`, `pv.chart()`, `pv.gauge()`, `pv.table()`
3. **Add aggregations** — Use Pathway's `groupby()`, `reduce()`, `windowby()`

Example with multiple widgets:

```python
import pathway as pw
import pathway_viz as pv

orders = pw.io.kafka.read(...)

# Aggregations
by_region = orders.groupby(pw.this.region).reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

totals = orders.reduce(
    total_revenue=pw.reducers.sum(pw.this.amount),
    order_count=pw.reducers.count(),
)

# Dashboard
pv.title("Order Analytics")
pv.stat(totals, "total_revenue", title="Revenue", unit="$")
pv.stat(totals, "order_count", title="Orders")
pv.table(by_region, title="By Region")
pv.start()
pw.run()
```

## Embedding Widgets

For embedding in other apps:

```python
pv.configure(embed=True)
pv.stat(totals, "revenue", id="revenue-widget")
pv.start()
```

Then embed:

```html
<iframe src="http://localhost:3000/embed/revenue-widget"></iframe>
```

## Production Deployment

See the [Deployment Guide](https://github.com/mvfolino68/pathway-viz/blob/main/docs/deployment.md) for:

- Kubernetes manifests
- Reverse proxy configuration
- TLS setup
- Health checks and monitoring

## Environment Variables

| Variable                  | Default        | Description           |
| ------------------------- | -------------- | --------------------- |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 | Kafka broker address  |
| `PATHWAYVIZ_PORT`         | 3000           | Dashboard port        |
| `PATHWAYVIZ_DATA_DIR`     | /app/data      | Persistence directory |
