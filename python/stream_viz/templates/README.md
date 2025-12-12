# My StreamViz Dashboard

Real-time dashboard powered by [StreamViz](https://github.com/mvfolino68/stream-viz).

## Quick Start

### Option 1: Simple Demo (No Docker)

```bash
pip install stream-viz
python pipeline.py --mode simple
```

Open <http://localhost:3000>

### Option 2: Full Stack (Docker)

```bash
docker compose up -d
```

This starts:

- **Redpanda** (Kafka-compatible) on port 9092
- **StreamViz** dashboard on port 3000

## Project Structure

```text
.
├── docker-compose.yml   # Full stack: Redpanda + StreamViz
├── Dockerfile           # Container for your pipeline
├── pipeline.py          # Your streaming pipeline
└── README.md
```

## Customizing

Edit `pipeline.py` to:

1. **Change Kafka topics** — Update the `topic="events"` parameter
2. **Add widgets** — Use `sv.stat()`, `sv.chart()`, `sv.gauge()`, `sv.table()`
3. **Add aggregations** — Use Pathway's `groupby()`, `reduce()`, `windowby()`

Example with multiple widgets:

```python
import pathway as pw
import stream_viz as sv

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
sv.title("Order Analytics")
sv.stat(totals, "total_revenue", title="Revenue", unit="$")
sv.stat(totals, "order_count", title="Orders")
sv.table(by_region, title="By Region")
sv.start()
pw.run()
```

## Embedding Widgets

For embedding in other apps:

```python
sv.configure(embed=True)
sv.stat(totals, "revenue", id="revenue-widget")
sv.start()
```

Then embed:

```html
<iframe src="http://localhost:3000/embed/revenue-widget"></iframe>
```

## Production Deployment

See the [Deployment Guide](https://github.com/mvfolino68/stream-viz/blob/main/docs/deployment.md) for:

- Kubernetes manifests
- Reverse proxy configuration
- TLS setup
- Health checks and monitoring

## Environment Variables

| Variable                  | Default        | Description           |
| ------------------------- | -------------- | --------------------- |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 | Kafka broker address  |
| `STREAMVIZ_PORT`          | 3000           | Dashboard port        |
| `STREAMVIZ_DATA_DIR`      | /app/data      | Persistence directory |
