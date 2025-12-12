# Core Concepts

Understanding how PathwayViz, Pathway, and windowing work together.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           YOUR PYTHON CODE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐   │
│   │   Pathway    │ ──────▶ │  PathwayViz   │ ──────▶ │    Rust      │   │
│   │   Pipeline   │  pw.io  │   Python     │  JSON   │  WebSocket   │   │
│   │              │ subscribe│   Wrapper    │         │   Server     │   │
│   └──────────────┘         └──────────────┘         └──────────────┘   │
│                                                              │          │
└──────────────────────────────────────────────────────────────┼──────────┘
                                                               │
                                              WebSocket broadcast
                                                               │
                                                               ▼
                                                    ┌──────────────────┐
                                                    │    Browser(s)    │
                                                    │   Dashboard UI   │
                                                    │   uPlot charts   │
                                                    └──────────────────┘
```

## What Each Component Does

### Pathway

Pathway is a **stream processing engine**. It:

- Reads from sources (Kafka, files, databases, APIs)
- Transforms data (filter, map, join)
- Aggregates (sum, count, avg, window)
- Outputs to sinks (databases, APIs, PathwayViz)

Pathway uses **incremental computation**: when new data arrives, it only recomputes what changed, not the entire dataset.

### PathwayViz

PathwayViz is a **visualization sink** for Pathway. It:

- Subscribes to Pathway table changes via `pw.io.subscribe()`
- Converts row updates to JSON messages
- Broadcasts to browsers via WebSocket
- Renders charts/tables/gauges in the browser

**PathwayViz does NOT process data.** It only visualizes what Pathway computes.

### The Rust Server

The WebSocket server is written in Rust for performance:

- Handles high-throughput message fan-out without Python GIL bottleneck
- Maintains ring buffers for recent data (so new clients see history)
- Serves the embedded frontend (no separate static file server needed)

## Two Modes of Operation

### 1. Pathway Mode (Recommended)

Pass Pathway tables directly to widgets. PathwayViz auto-subscribes.

```python
import pathway as pw
import pathway_viz as sv

# Pathway pipeline
orders = pw.io.kafka.read(...)
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

# PathwayViz subscribes automatically
sv.stat(totals, "revenue", title="Revenue")

sv.start()
pw.run()  # Pathway drives everything
```

When Pathway updates `totals`, PathwayViz's subscription callback fires and sends the new value to browsers.

### 2. Manual Mode

Create widgets with string IDs and call `.send()` yourself.

```python
import pathway_viz as sv

revenue = sv.stat("revenue", title="Revenue")
sv.start()

# You control when data is sent
revenue.send(12500)
revenue.send(13200)
```

Use this when:

- You don't use Pathway
- You need custom logic before sending
- You're integrating with other systems

## Understanding Pathway Aggregations

### Global Aggregations (reduce)

`reduce()` produces a **single-row table** that updates in place:

```python
totals = orders.reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)
# Result: Always 1 row, values update as orders arrive
```

Perfect for: `sv.stat()`, `sv.gauge()`

### Grouped Aggregations (groupby + reduce)

`groupby().reduce()` produces **one row per group**:

```python
by_region = orders.groupby(pw.this.region).reduce(
    region=pw.this.region,
    revenue=pw.reducers.sum(pw.this.amount),
)
# Result: One row per unique region, updates as orders arrive
```

Perfect for: `sv.table()`

### The Problem: Unbounded Growth

Without windowing, aggregations grow forever:

```python
# This keeps summing ALL orders since app start
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
```

If you restart the app, `revenue` resets to 0. You lose all history.

---

## Windowing

Windowing groups data into **time buckets** so you can answer questions like:

- "How many orders per minute?"
- "What's the average latency over the last 5 minutes?"
- "What's the revenue for each hour today?"

### Tumbling Windows

Fixed, non-overlapping time buckets:

```
Time:   |-------|-------|-------|-------|
Window:    W1      W2      W3      W4
```

```python
from datetime import timedelta

orders_per_minute = orders.windowby(
    pw.this.event_time,  # Timestamp column in your data
    window=pw.temporal.tumbling(duration=timedelta(minutes=1)),
).reduce(
    window_start=pw.this._pw_window_start,
    window_end=pw.this._pw_window_end,
    count=pw.reducers.count(),
    revenue=pw.reducers.sum(pw.this.amount),
)
```

Output: One row per minute with that minute's totals.

### Sliding Windows

Overlapping windows for smoothed metrics:

```
Time:   |-----------|
            |-----------|
                |-----------|
```

```python
# 5-minute window, updates every 1 minute
orders_5min = orders.windowby(
    pw.this.event_time,
    window=pw.temporal.sliding(
        duration=timedelta(minutes=5),
        hop=timedelta(minutes=1),
    ),
).reduce(
    count=pw.reducers.count(),
)
```

### Session Windows

Group by activity with gaps (great for user sessions):

```python
user_sessions = events.windowby(
    pw.this.timestamp,
    window=pw.temporal.session(max_gap=timedelta(minutes=30)),
).reduce(
    session_start=pw.this._pw_window_start,
    session_end=pw.this._pw_window_end,
    event_count=pw.reducers.count(),
)
```

### Using Windows with PathwayViz

```python
# Time series chart from windowed data
orders_per_minute = orders.windowby(...).reduce(
    window_end=pw.this._pw_window_end,
    count=pw.reducers.count(),
)

sv.chart(
    orders_per_minute,
    "count",
    x_column="window_end",  # Use window end time as X axis
    title="Orders/minute",
)
```

## Event Time vs Processing Time

### Event Time

The timestamp **in your data** (when the event actually happened):

```python
orders.windowby(
    pw.this.event_time,  # Column from your data
    window=pw.temporal.tumbling(duration=timedelta(minutes=1)),
)
```

Use when: Data has meaningful timestamps (orders, logs, sensor readings).

### Processing Time

When Pathway **processes** the data (wall clock time):

```python
orders.windowby(
    pw.this._pw_time,  # Pathway's internal processing time
    window=pw.temporal.tumbling(duration=timedelta(minutes=1)),
)
```

Use when: Data doesn't have timestamps, or you want real-time buckets.

## Data Flow Summary

1. **Source** → Data enters via Kafka, file, API
2. **Transform** → Pathway filters, maps, joins
3. **Aggregate** → `reduce()` or `windowby().reduce()`
4. **Subscribe** → PathwayViz subscribes to table changes
5. **Broadcast** → Rust server sends JSON to browsers
6. **Render** → Browser updates charts/tables

## Next Steps

- [Widgets](./widgets.md) — All widget types and options
- [Persistence](./persistence.md) — Survive restarts with DuckDB
- [E-commerce Example](./examples/ecommerce.md) — Complete production example
