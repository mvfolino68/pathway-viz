# StreamViz

Real-time streaming data visualization for Python. Build dashboards in seconds with a Streamlit-like API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Simple** — Streamlit-like API: just `sv.metric()` and `.send()`
- **Fast** — Rust-powered WebSocket server handles thousands of messages/sec
- **Zero config** — No JavaScript, no build step, just `pip install` and go
- **Multi-chart** — Each metric gets its own auto-scaling chart
- **Batteries included** — Works with Kafka, Redpanda, Pathway, or plain Python

## Quick Start

```bash
# Install
pip install stream-viz

# Run the demo
python -m stream_viz
```

Open <http://localhost:3000> — that's it! 🎉

## Usage

```python
import stream_viz as sv
import math
import time

# Define your dashboard
sv.title("My Dashboard")
cpu = sv.metric("cpu", title="CPU Usage", unit="%")
memory = sv.metric("memory", title="Memory", unit="%")

# Start the server
sv.start(port=3000)

# Stream data
i = 0
while True:
    cpu.send(50 + 30 * math.sin(i * 0.1))
    memory.send(60 + 10 * math.cos(i * 0.05))
    time.sleep(0.05)
    i += 1
```

## Demos

```bash
python -m stream_viz              # Built-in demo
python -m stream_viz simple       # Simple waves demo
python -m stream_viz kafka        # Kafka demo (needs Docker)
python -m stream_viz ecommerce    # Pathway aggregations
```

## With Kafka/Redpanda

```bash
# Start Redpanda
docker compose up -d

# Terminal 1: Producer
python examples/producer.py

# Terminal 2: Dashboard
python examples/kafka_demo.py
```

```python
import json
from kafka import KafkaConsumer
import stream_viz as sv

sv.title("Kafka Metrics")
cpu = sv.metric("cpu", title="CPU", unit="%")

sv.start(port=3000)

consumer = KafkaConsumer(
    "metrics",
    bootstrap_servers=["localhost:9092"],
    value_deserializer=lambda m: json.loads(m.decode()),
)

for msg in consumer:
    cpu.send(msg.value["cpu"])
```

## Installation from Source

```bash
# Install Rust (if needed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Clone and install
git clone https://github.com/yourusername/stream-viz.git
cd stream-viz

# Setup with uv (recommended)
uv venv --python 3.12 .venv
source .venv/bin/activate.fish  # or: source .venv/bin/activate
uv pip install maturin && maturin develop
uv pip install -e ".[all]"
```

## Optional Dependencies

| Extra | Description | Install |
|-------|-------------|---------|
| `kafka` | Kafka/Redpanda | `pip install stream-viz[kafka]` |
| `pathway` | Stream processing | `pip install stream-viz[pathway]` |
| `all` | Everything | `pip install stream-viz[all]` |

Note: Pathway requires Python 3.11-3.13.

## API Reference

### `sv.title(text)`

Set the dashboard title.

### `sv.metric(id, *, title=None, unit="", color=None, max_points=200)`

Create a metric. Returns a `Metric` object.

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | str | Unique identifier |
| `title` | str | Display title (defaults to id) |
| `unit` | str | Unit label (e.g., "%", "ms") |
| `color` | str | Hex color (auto-assigned if None) |
| `max_points` | int | Max points before scrolling |

### `metric.send(value, timestamp=None)`

Send a data point. Timestamp is milliseconds (defaults to now).

### `sv.start(port=3000)`

Start the server. Non-blocking.

### `sv.run_demo(port=3000)`

Run the built-in demo. Blocks forever.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  Python                                                         │
│                                                                 │
│  sv.metric("cpu")  ──────────────┐                             │
│  cpu.send(75.5)  ────────────────┼──▶  WebSocket broadcast     │
│                                  │                              │
└──────────────────────────────────┼──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Rust (Axum + Tokio)                                            │
│  • WebSocket server on background thread                        │
│  • Embedded frontend (no external files!)                       │
└──────────────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
│  • Creates charts dynamically from config                       │
│  • Auto-reconnects on disconnect                                │
└─────────────────────────────────────────────────────────────────┘
```

## Development

```bash
git clone https://github.com/yourusername/stream-viz.git
cd stream-viz
uv venv --python 3.12 .venv && source .venv/bin/activate.fish
uv pip install maturin && maturin develop
uv pip install -e ".[dev]"
pytest
```

## License

MIT
