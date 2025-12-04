# StreamViz

**The visualization layer for [Pathway](https://pathway.com).** Real-time dashboards for streaming data pipelines.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Why StreamViz?

Pathway gives you powerful streaming aggregations. StreamViz makes them visible.

```python
import pathway as pw
import stream_viz as sv

# Your Pathway pipeline
orders = pw.io.kafka.read(...)
stats = orders.groupby(pw.this.region).reduce(
    total=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

# Visualize it
sv.title("Order Analytics")
sv.pathway_table(stats, 
    columns=["region", "total", "count"],
    title="Orders by Region"
)
sv.start()
pw.run()
```

That's it. Your Pathway aggregations, live in a dashboard.

## Features

- **Pathway-native** — Direct integration with `pw.Table` outputs
- **Zero config** — No JavaScript, no build step, just `pip install`
- **Real-time** — See aggregations update as data flows
- **Fast** — Rust WebSocket server handles high throughput
- **Rich widgets** — Tables, gauges, stats, time series charts

## Quick Start

```bash
pip install stream-viz pathway

# Run the e-commerce demo
python -m stream_viz ecommerce
```

Open <http://localhost:3000> — live dashboard showing Pathway aggregations.

## Pathway Integration

### Visualize a Pathway Table

```python
import pathway as pw
import stream_viz as sv

# Read from Kafka
events = pw.io.kafka.read(
    rdkafka_settings={"bootstrap.servers": "localhost:9092"},
    topic="events",
    format="json",
    schema=EventSchema,
)

# Pathway aggregations
hourly_stats = events.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=datetime.timedelta(hours=1)),
).reduce(
    count=pw.reducers.count(),
    total=pw.reducers.sum(pw.this.amount),
    avg=pw.reducers.avg(pw.this.amount),
)

# Send to StreamViz
sv.title("Hourly Analytics")
sv.pathway_table(hourly_stats, columns=["window_start", "count", "total", "avg"])
sv.start()

pw.run()
```

### Track a Single Metric

```python
# Pathway pipeline that outputs a single row with current totals
totals = orders.reduce(
    total_orders=pw.reducers.count(),
    total_revenue=pw.reducers.sum(pw.this.amount),
)

# Visualize as gauges/stats
sv.pathway_stat(totals, column="total_orders", title="Total Orders")
sv.pathway_stat(totals, column="total_revenue", title="Revenue", unit="$")
```

### Time Series from Pathway

```python
# Windowed aggregation
per_second = events.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=datetime.timedelta(seconds=1)),
).reduce(
    rps=pw.reducers.count(),
)

# Visualize as chart
sv.pathway_metric(per_second, 
    time_column="window_start",
    value_column="rps", 
    title="Requests/sec"
)
```

## Standalone Mode (No Pathway)

StreamViz also works without Pathway for quick visualizations:

```python
import stream_viz as sv
import random

sv.title("System Metrics")

# Widgets
cpu = sv.gauge("cpu", title="CPU", unit="%", max_val=100,
    thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])
    
rps = sv.metric("rps", title="Requests/sec")
events = sv.table("events", title="Events", 
    columns=["time", "level", "message"], max_rows=20)

sv.start()

while True:
    cpu.send(random.uniform(30, 90))
    rps.send(random.randint(100, 500))
    # ... your data source
```

## Widget Types

| Widget | Use Case | Example |
|--------|----------|---------|
| `sv.pathway_table()` | Show Pathway table output | Aggregation results, latest state |
| `sv.pathway_stat()` | Big number from Pathway | Total count, sum, current value |
| `sv.pathway_metric()` | Time series from Pathway | Windowed aggregations over time |
| `sv.gauge()` | Bounded value | CPU %, memory, progress |
| `sv.stat()` | Big number | Totals, counts |
| `sv.metric()` | Time series | Any numeric over time |
| `sv.table()` | Streaming rows | Logs, events, records |

## Demos

```bash
python -m stream_viz              # Built-in demo (no Pathway needed)
python -m stream_viz ecommerce    # E-commerce with Pathway + Kafka
python -m stream_viz kafka        # Kafka consumer
```

## Installation

```bash
# With Pathway (recommended)
pip install stream-viz[pathway]

# Just StreamViz
pip install stream-viz

# Everything (Pathway + Kafka)
pip install stream-viz[all]
```

### From Source

```bash
# Requires Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

git clone https://github.com/yourusername/stream-viz.git
cd stream-viz
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install maturin && maturin develop
uv pip install -e ".[all]"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Pathway Pipeline                                               │
│                                                                 │
│  events.groupby().reduce()  ─────▶  sv.pathway_table(stats)    │
│                                            │                    │
└────────────────────────────────────────────┼────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  StreamViz (Rust)                                               │
│  • WebSocket server with history buffer                         │
│  • Embedded dashboard (no external files)                       │
│  • Handles 10k+ messages/sec                                    │
└────────────────────────────────────────────┬────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Browser Dashboard                                              │
│  • Live-updating tables, charts, gauges                         │
│  • Auto-reconnect on disconnect                                 │
│  • New connections see existing data                            │
└─────────────────────────────────────────────────────────────────┘
```

## Why Not Just Use...?

| Alternative | Limitation |
|-------------|------------|
| **Grafana** | Requires infrastructure, PromQL, not Python-native |
| **Streamlit** | Request-response model, not designed for streaming |
| **Jupyter** | Great for exploration, not for live dashboards |
| **Print statements** | No visualization, hard to share |

StreamViz is purpose-built for streaming Python pipelines, especially Pathway.

## Roadmap

- [x] Core widget types (gauge, stat, metric, table)
- [x] Rust WebSocket server with history buffer
- [ ] `sv.pathway_table()` — direct Pathway integration
- [ ] `sv.pathway_output()` — subscribe to Pathway table changes
- [ ] Interactive features (pause, time range, zoom)
- [ ] Theming and layout customization
- [ ] Export/snapshot dashboards

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

## License

MIT
