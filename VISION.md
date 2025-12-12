# PathwayViz Vision

## Mission

Real-time dashboards for streaming data pipelines. Production-ready visualization that works standalone or with Pathway.

## Core Principles

### 1. Zero Configuration

No JavaScript. No npm. No build step:

```bash
pip install pathway-viz
pathway-viz demo
```

The frontend is embedded in the Rust binary. You write Python, you get a dashboard.

### 2. Production Ready

- **Embeddable** — Drop widgets into existing web apps via iframe
- **Fast** — Rust WebSocket server handles thousands of updates/sec
- **Reliable** — Auto-reconnect, state preserved in ring buffers

### 3. Simple API

Four widget types cover 90% of use cases:

| Widget  | Use           | Example        |
| ------- | ------------- | -------------- |
| `gauge` | Bounded value | CPU %, memory  |
| `stat`  | Single number | Revenue, count |
| `chart` | Time series   | Latency, RPS   |
| `table` | Live rows     | Events, orders |

### 4. Pathway Native

Pass Pathway tables directly — widgets update automatically:

```python
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
sv.stat(totals, "revenue", title="Revenue")
```

## Target Users

### Primary: Python Developers

Anyone who wants real-time dashboards without frontend complexity.

### Secondary: Pathway Users

Developers building streaming pipelines who need production dashboards (not just Jupyter notebooks).

## Differentiation

| Feature     | Pathway + Panel | PathwayViz             |
| ----------- | --------------- | ---------------------- |
| Environment | Jupyter only    | Standalone server      |
| Setup       | Bokeh knowledge | Zero config            |
| Embedding   | Not supported   | iframe-ready           |
| Server      | Python          | Rust (high throughput) |

## Architecture

```text
Python API → Rust WebSocket Server → Browser
                    ↓
            Ring buffers (history)
            Broadcast channels (fan-out)
            Embedded frontend (single binary)
```

**Why Rust?** Tokio async I/O + lock-free broadcast channels avoid Python's GIL for high-throughput WebSocket fan-out.

## Roadmap

### v0.1 (Current)

- [x] Core widgets: gauge, stat, chart, table
- [x] Pathway integration
- [x] Embedded Rust server
- [x] Embed mode for single widgets

### v0.2

- [ ] Theme customization (dark/light)
- [ ] More chart types
- [ ] Prometheus metrics endpoint

### Future

- [ ] Alerts and thresholds
- [ ] Authentication
- [ ] WebGPU rendering for large datasets
