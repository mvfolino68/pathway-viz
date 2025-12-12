# StreamViz Documentation

Real-time dashboards for Kafka/Redpanda streaming pipelines.

## Quick Start

```bash
# Install (from source for now)
git clone https://github.com/yourusername/stream-viz.git
cd stream-viz
pip install maturin
maturin develop
pip install pathway kafka-python-ng duckdb

# Run the demo
python -m stream_viz
```

Opens:

- **Dashboard**: http://localhost:3000
- **Portal**: http://localhost:3001 (embedded widgets demo)

The demo auto-starts Kafka (Redpanda) via Docker.

## What is StreamViz?

StreamViz is a **visualization layer** for [Pathway](https://pathway.com/) streaming pipelines:

- **Kafka/Redpanda** → ingests data
- **Pathway** → processes streams (aggregations, windows)
- **StreamViz** → displays real-time dashboards
- **DuckDB** → persists data (survives restarts)

```python
import pathway as pw
import stream_viz as sv

orders = pw.io.kafka.read(...)
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

sv.stat(totals, "revenue", title="Today's Revenue", unit="$")
sv.start()
pw.run()
```

## Documentation

- **[Getting Started](./getting-started.md)** — Installation and first dashboard
- **[Concepts](./concepts.md)** — How Pathway, windowing, and StreamViz work
- **[Widgets](./widgets.md)** — stat, chart, gauge, table reference
- **[Persistence](./persistence.md)** — DuckDB for surviving restarts
- **[Deployment](./deployment.md)** — Docker, Kubernetes

## Embedding

```python
sv.configure(embed=True)
sv.stat("revenue", title="Revenue")
sv.start()
```

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

See [examples/](../examples/) for React, Svelte, and Next.js components.
