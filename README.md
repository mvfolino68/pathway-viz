# StreamViz

**The visualization layer for [Pathway](https://pathway.com).** Real-time dashboards and embeddable widgets for streaming data pipelines.

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
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

# Visualize it - one line per widget
sv.title("Order Analytics")
sv.table(stats, title="Orders by Region")
sv.start()
pw.run()
```

That's it. Your Pathway aggregations, live in a dashboard.

## Features

- **Pathway-native** — Pass Pathway tables directly to widgets
- **Zero config** — No JavaScript, no build step, just `pip install`
- **Real-time** — Widgets update as data flows through Pathway
- **Fast** — Rust WebSocket server handles high throughput
- **Embeddable** — Embed individual widgets in your own web apps
- **Rich widgets** — Tables, charts, gauges, and stats

## Quick Start

```bash
pip install stream-viz

# Run the interactive demo
python -m stream_viz
```

Open <http://localhost:3000> — live dashboard with demo data.

## Widget Types

### Table — Live Updating Rows

```python
# From Pathway table (auto-updates)
by_region = orders.groupby(pw.this.region).reduce(...)
sv.table(by_region, title="By Region", columns=["region", "revenue", "count"])

# Manual mode (for non-Pathway sources)
events = sv.table("events", title="Events", columns=["time", "level", "msg"])
events.send({"time": "12:00", "level": "INFO", "msg": "Started"})
```

### Stat — Big Numbers

```python
# From Pathway (single-row table)
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
sv.stat(totals, "revenue", title="Total Revenue", unit="$")

# Manual mode
visitors = sv.stat("visitors", title="Active Visitors")
visitors.send(1234)
```

### Chart — Time Series

```python
# From Pathway windowed aggregation
per_minute = orders.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=timedelta(minutes=1))
).reduce(count=pw.reducers.count())

sv.chart(per_minute, "count", x_column="window_end", title="Orders/min")

# Manual mode
cpu = sv.chart("cpu", title="CPU Usage", unit="%")
cpu.send(72.5)
```

### Gauge — Bounded Values

```python
# From Pathway
sv.gauge(system_stats, "cpu", title="CPU", max_val=100, unit="%",
         thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])

# Manual mode
cpu = sv.gauge("cpu", title="CPU", max_val=100, unit="%")
cpu.send(72)
```

## Pathway Integration

StreamViz works seamlessly with Pathway's streaming primitives:

### Reducers → Stats/Gauges

```python
totals = orders.reduce(
    total_orders=pw.reducers.count(),
    total_revenue=pw.reducers.sum(pw.this.amount),
    avg_order=pw.reducers.avg(pw.this.amount),
)

sv.stat(totals, "total_orders", title="Orders")
sv.stat(totals, "total_revenue", title="Revenue", unit="$")
sv.gauge(totals, "avg_order", title="Avg Order", min_val=0, max_val=500)
```

### GroupBy → Tables

```python
by_region = orders.groupby(pw.this.region).reduce(
    region=pw.this.region,
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

sv.table(by_region, title="By Region",
         columns=["region", "revenue", "count"],
         sort_by="revenue")
```

### Windowing → Charts

```python
per_second = orders.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=timedelta(seconds=1))
).reduce(
    window_end=pw.this._pw_window_end,
    rps=pw.reducers.count(),
)

sv.chart(per_second, "rps", x_column="window_end", title="Orders/sec")
```

## Embeddable Widgets

Embed individual widgets in your own web applications:

```python
import stream_viz as sv

# Enable embedding
sv.configure(embed=True)

# Create widgets with IDs
sv.table(by_region, id="regions", embed=True)
sv.stat(totals, "revenue", id="revenue", embed=True)

sv.start(port=3000)
pw.run()
```

Then embed in your HTML:

```html
<!-- Option 1: iframe (simplest) -->
<iframe
    src="http://localhost:3000/embed/regions"
    style="border: none; width: 100%; height: 400px;">
</iframe>

<!-- Option 2: Multiple widgets -->
<iframe src="http://localhost:3000/embed/revenue"></iframe>
<iframe src="http://localhost:3000/embed/regions"></iframe>
```

## API Reference

### Configuration

```python
sv.configure(
    title="My Dashboard",     # Dashboard title
    theme="dark",             # "dark" or "light"
    port=3000,                # Server port
    embed=True,               # Enable embed endpoints
)

sv.title("Dashboard Title")   # Shortcut for title
sv.start(port=3000)           # Start server
```

### Widgets

All widgets accept either a Pathway table or a string ID for manual mode.

```python
# Pathway mode - auto-updates from table changes
sv.table(pw_table, ...)
sv.stat(pw_table, column, ...)
sv.chart(pw_table, y_column, ...)
sv.gauge(pw_table, column, ...)

# Manual mode - returns object with .send() method
widget = sv.table("id", ...)
widget.send(data)
```

### Common Parameters

| Parameter | Description |
|-----------|-------------|
| `id` | Widget identifier (for embedding) |
| `title` | Display title |
| `embed` | Enable embed endpoint for this widget |

## Standalone Mode (No Pathway)

StreamViz works without Pathway for simple dashboards:

```python
import stream_viz as sv
import math

sv.title("System Monitor")

cpu = sv.gauge("cpu", title="CPU", max_val=100, unit="%")
mem = sv.gauge("mem", title="Memory", max_val=100, unit="%")
history = sv.chart("history", title="CPU History", unit="%")

sv.start()

i = 0
while True:
    val = 50 + 30 * math.sin(i * 0.05)
    cpu.send(val)
    history.send(val)
    mem.send(60 + 10 * math.sin(i * 0.02))
    time.sleep(0.1)
    i += 1
```

## Architecture

StreamViz consists of:

1. **Python API** — High-level widget definitions
2. **Rust Server** — WebSocket server for real-time updates (via PyO3)
3. **Frontend** — Embedded HTML/JS dashboard (no build step)

Data flow:

```text
Pathway Table → pw.io.subscribe → Python → Rust WebSocket → Browser
```

## Installation

```bash
# PyPI (when published)
pip install stream-viz

# Development
git clone https://github.com/yourname/stream-viz
cd stream-viz
pip install maturin
maturin develop
```

Requires:

- Python 3.11+
- Rust (for building from source)
- Pathway (optional, for streaming integration)

## License

MIT
