# StreamViz

Real-time dashboards for streaming data pipelines. Zero config, embeddable, fast.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## What is StreamViz?

**Pathway** handles streaming aggregations. **StreamViz** makes them visible.

```python
import pathway as pw
import stream_viz as sv

orders = pw.io.kafka.read(...)
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

sv.stat(totals, "revenue", title="Revenue", unit="$")
sv.start()
pw.run()
```

Open `http://localhost:3000` → live dashboard.

## Install

```bash
pip install stream-viz            # Basic
pip install stream-viz[pathway]   # With Pathway
pip install stream-viz[all]       # Everything
```

## Quick Start

```bash
pip install stream-viz

# Run demos
stream-viz demo --mode simple   # No Docker required
stream-viz demo                 # E-commerce demo (requires Docker)

# Scaffold a new project
stream-viz init my-dashboard           # Creates project with Docker files
stream-viz init my-dashboard --k8s     # Include Kubernetes manifests

# View templates
stream-viz templates                   # List all templates
stream-viz show docker-compose         # Print template to stdout
```

## Widgets

| Widget  | Purpose        | Example                                           |
| ------- | -------------- | ------------------------------------------------- |
| `stat`  | Big numbers    | `sv.stat("revenue", title="Revenue", unit="$")`   |
| `chart` | Time series    | `sv.chart("latency", title="Latency", unit="ms")` |
| `gauge` | Bounded values | `sv.gauge("cpu", title="CPU", max_val=100)`       |
| `table` | Live rows      | `sv.table("events", columns=["time", "msg"])`     |

## Embedding

```python
sv.configure(embed=True)
sv.stat("revenue", title="Revenue")
sv.start()
```

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

## Documentation

For comprehensive guides, see the **[docs/](./docs/)** folder:

- **[Concepts](./docs/concepts.md)** — How StreamViz, Pathway, and windowing work
- **[Widgets](./docs/widgets.md)** — All widget types with parameters and examples
- **[Persistence](./docs/persistence.md)** — DuckDB, Pathway checkpointing, surviving restarts
- **[Deployment](./docs/deployment.md)** — Docker, Kubernetes, reverse proxy setup
- **[E-commerce Example](./docs/examples/ecommerce.md)** — Kafka + Pathway demo with embedded widgets and optional DuckDB persistence

## Docker

Pre-built images are available on Docker Hub:

```bash
# Pull the image
docker pull mvfolino68/stream-viz:latest

# Run the simple demo
docker run -p 3000:3000 mvfolino68/stream-viz python -m stream_viz --mode simple

# Or use your own pipeline
docker run -p 3000:3000 -v $(pwd)/my_pipeline.py:/app/pipeline.py \
  mvfolino68/stream-viz python /app/pipeline.py
```

## CLI Reference

```bash
stream-viz demo [--mode simple|pathway] [--port PORT]   # Run demos
stream-viz init DIRECTORY [--k8s] [--force]             # Scaffold project
stream-viz show TEMPLATE                                 # Print template
stream-viz templates                                     # List templates
```

## Architecture

```text
Pathway Pipeline → StreamViz Python → Rust WebSocket Server → Browser
                                              ↓
                                      Ring buffers for history
```

The Rust WebSocket server handles high-throughput broadcast without Python GIL bottlenecks.

## License

MIT
