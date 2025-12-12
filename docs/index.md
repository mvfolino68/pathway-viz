# PathwayViz Documentation

Real-time dashboards for Kafka/Redpanda streaming pipelines.

## Quick Start

```bash
pip install pathway-viz

# No-Docker demo
pathway-viz demo --mode simple

# Kafka + Pathway demo (requires Docker)
pathway-viz demo
```

Opens:

- **Dashboard**: <http://localhost:3000>
- **Portal**: <http://localhost:3001> (embedded widgets demo)

The demo auto-starts Kafka (Redpanda) via Docker.

## What is PathwayViz?

PathwayViz is a **visualization layer** for [Pathway](https://pathway.com/) streaming pipelines:

- **Kafka/Redpanda** → ingests data
- **Pathway** → processes streams (aggregations, windows)
- **PathwayViz** → displays real-time dashboards
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
- **[Concepts](./concepts.md)** — How Pathway, windowing, and PathwayViz work
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
