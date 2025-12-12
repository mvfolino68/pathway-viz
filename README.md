# PathwayViz

Real-time dashboards for streaming data pipelines. Zero config, embeddable, fast.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## What is PathwayViz?

**Pathway** handles streaming aggregations. **PathwayViz** makes them visible.

```python
import pathway as pw
import pathway_viz as pv

orders = pw.io.kafka.read(...)
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

pv.stat(totals, "revenue", title="Revenue", unit="$")
pv.start()
pw.run()
```

Open `http://localhost:3000` → live dashboard.

Note: the Python module name is `pathway_viz` (e.g. `import pathway_viz as pv`).

## Install

```bash
pip install pathway-viz            # Basic
pip install pathway-viz[pathway]   # With Pathway
pip install pathway-viz[all]       # Everything
```

## Quick Start

```bash
pip install pathway-viz

# Run demos
pathway-viz demo --mode simple   # No Docker required
pathway-viz demo                 # E-commerce demo (requires Docker)

# Scaffold a new project
pathway-viz init my-dashboard           # Creates project with Docker files
pathway-viz init my-dashboard --k8s     # Include Kubernetes manifests

# View templates
pathway-viz templates                   # List all templates
pathway-viz show docker-compose         # Print template to stdout
```

## Widgets

| Widget  | Purpose        | Example                                           |
| ------- | -------------- | ------------------------------------------------- |
| `stat`  | Big numbers    | `pv.stat("revenue", title="Revenue", unit="$")`   |
| `chart` | Time series    | `pv.chart("latency", title="Latency", unit="ms")` |
| `gauge` | Bounded values | `pv.gauge("cpu", title="CPU", max_val=100)`       |
| `table` | Live rows      | `pv.table("events", columns=["time", "msg"])`     |

## Embedding

```python
pv.configure(embed=True)
pv.stat("revenue", title="Revenue")
pv.start()
```

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

## Documentation

For comprehensive guides, see the **[docs/](./docs/)** folder:

- **[Concepts](./docs/concepts.md)** — How PathwayViz, Pathway, and windowing work
- **[Widgets](./docs/widgets.md)** — All widget types with parameters and examples
- **[Persistence](./docs/persistence.md)** — DuckDB, Pathway checkpointing, surviving restarts
- **[Deployment](./docs/deployment.md)** — Docker, Kubernetes, reverse proxy setup
- **[E-commerce Example](./docs/examples/ecommerce.md)** — Kafka + Pathway demo with embedded widgets and optional DuckDB persistence

## Docker

Pre-built images are available on Docker Hub:

```bash
# Pull the image
docker pull mvfolino68/pathway-viz:latest

# Run the simple demo
docker run -p 3000:3000 mvfolino68/pathway-viz python -m pathway_viz --mode simple

# Or use your own pipeline
docker run -p 3000:3000 -v $(pwd)/my_pipeline.py:/app/pipeline.py \
  mvfolino68/pathway-viz python /app/pipeline.py
```

## CLI Reference

```bash
pathway-viz demo [--mode simple|pathway] [--port PORT]   # Run demos
pathway-viz init DIRECTORY [--k8s] [--force]             # Scaffold project
pathway-viz show TEMPLATE                                 # Print template
pathway-viz templates                                     # List templates
```

## Architecture

```text
Pathway Pipeline → PathwayViz Python (`pathway_viz`) → Rust WebSocket Server → Browser
                                              ↓
                                      Ring buffers for history
```

The Rust WebSocket server handles high-throughput broadcast without Python GIL bottlenecks.

## License

MIT
