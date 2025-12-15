# PathwayViz

[![PyPI](https://img.shields.io/pypi/v/pathway-viz)](https://pypi.org/project/pathway-viz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Embeddable real-time widgets for [Pathway](https://pathway.com/) streaming pipelines. Rust WebSocket server with a Python API.

![Demo](assets/demo.gif)

## Overview

PathwayViz makes it easy to embed live-updating data from Kafka streams into any web page. Define widgets in Python, embed them via iframe anywhere.

```python
import pathway as pw
import pathwayviz as pv

orders = pw.io.kafka.read(...)
revenue = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

# Create a widget server
server = pv.WidgetServer(port=3000)
server.register(pv.Stat(revenue, "revenue", id="revenue", title="Revenue", unit="$"))
server.start()
pw.run()
```

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

## Install

```bash
pip install pathway-viz
```

## Architecture

```mermaid
flowchart LR
    subgraph Pathway["Pathway Pipeline"]
        K[Kafka] --> P[Processing]
        P --> T[Tables]
    end

    subgraph PathwayViz
        T -->|subscribe| PY[Python API]
        PY -->|JSON| RS[Rust Server]
        RS --> RB[Ring Buffers]
        RS -->|WebSocket| B[Browser]
    end
```

**Key components:**

- **WidgetServer** - Manages widget registration and serves embeddable endpoints
- **Widget Classes** - `Stat`, `Chart`, `Gauge`, `Table` subscribe to Pathway tables
- **Rust WebSocket Server** - Tokio async runtime handles concurrent connections without GIL contention
- **Ring Buffers** - New clients receive historical data immediately without replaying the stream

## Widgets

```python
server = pv.WidgetServer(port=3000)

# Single value with delta tracking
server.register(pv.Stat(totals, "revenue", id="revenue", title="Revenue", unit="$"))

# Time series chart
server.register(pv.Chart(windowed_data, "count", id="orders_chart", x_column="window_end", title="Orders/sec"))

# Circular gauge
server.register(pv.Gauge(stats, "cpu", id="cpu_gauge", title="CPU", max_val=100, unit="%"))

# Live-updating table
server.register(pv.Table(by_region, id="regions", title="By Region", columns=["region", "revenue"]))

server.start()
```

Each widget is accessible at `/embed/{widget_id}`.

## Demo

Requires Docker (spins up Redpanda for Kafka):

```bash
pip install pathway-viz[kafka]
pathway-viz demo
```

Generates fake e-commerce orders and displays live metrics. Includes a portal page demonstrating embedded widgets in a mock storefront.

## Documentation

- [Getting Started](./docs/getting-started.md)
- [Widgets](./docs/widgets.md)
- [Embedding](./docs/embedding.md)
- [Deployment](./docs/deployment.md)

## Roadmap

- [x] Core widgets (stat, chart, gauge, table)
- [x] Pathway table subscriptions
- [x] Embed mode with per-widget endpoints
- [x] Ring buffer history for late-joining clients
- [ ] Additional chart types
- [ ] Crash recovery

## License

MIT
