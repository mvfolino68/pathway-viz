# PathwayViz Architecture: Embeddable Pathway Visualization

## Key Insight

Pathway already has `table.plot()` and `table.show()` for **Jupyter notebooks**.
PathwayViz should focus on **production dashboards** and **embeddable widgets**.

## Two Modes

### 1. Standalone Dashboard Mode

```python
import pathway_viz as sv

sv.title("Analytics")
sv.table(my_table)
sv.start()
pw.run()
```

Opens full dashboard at localhost:3000

### 2. Embed Mode (iframes)

```python
import pathway_viz as sv

sv.configure(embed=True)
sv.stat("revenue", title="Revenue")
sv.start()
```

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

## Embed Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│  Your Web App (React, Vue, plain HTML)                              │
│                                                                     │
│  <iframe src="http://localhost:3000/embed/orders?height=400" />     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ WebSocket
┌─────────────────────────────────────────────────────────────────────┐
│  PathwayViz Server (Rust)                                            │
│                                                                     │
│  Routes:                                                            │
│    /                     → Full dashboard                           │
│    /embed/:widget_id     → Single widget (embeddable)               │
│    /ws                   → WebSocket for full dashboard             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ pw.io.subscribe
┌─────────────────────────────────────────────────────────────────────┐
│  Pathway Pipeline                                                   │
│                                                                     │
│  sv.table(orders_table, id="orders")                                │
│  sv.stat(totals, "revenue", id="revenue")                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Embed Integrations

For framework examples (React / Next.js / Svelte), see `examples/`.

## Pathway-Native API Design

```python
import pathway as pw
import pathway_viz as sv

# Read from Kafka
orders = pw.io.kafka.read(...)

# Pathway aggregations
by_region = orders.groupby(pw.this.region).reduce(
    region=pw.this.region,
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
    avg_order=pw.reducers.avg(pw.this.amount),
)

totals = orders.reduce(
    total_revenue=pw.reducers.sum(pw.this.amount),
    total_orders=pw.reducers.count(),
)

# Windowed aggregations
per_minute = orders.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=timedelta(minutes=1)),
).reduce(
    window_start=pw.this._pw_window_start,
    window_end=pw.this._pw_window_end,
    count=pw.reducers.count(),
    revenue=pw.reducers.sum(pw.this.amount),
)

# === PathwayViz subscribes to table changes
sv.configure(
    title="E-Commerce Analytics",
    theme="dark",
    embed=True,  # Enable embed endpoints
)

# Tables - keyed by Pathway pointer, updates in place
sv.table(by_region,
    id="by_region",
    title="Revenue by Region",
    columns=["region", "revenue", "count", "avg_order"],
    sort_by="revenue",
    sort_desc=True,
)

# Stats - single values with delta
sv.stat(totals, "total_revenue",
    id="revenue",
    title="Total Revenue",
    unit="$",
    format=",.2f",
)

sv.stat(totals, "total_orders",
    id="orders",
    title="Total Orders",
)

# Time series from windowed aggregations
sv.chart(per_minute,
    id="rps",
    title="Orders/min",
    x="window_end",
    y="count",
    chart_type="line",
)

sv.chart(per_minute,
    id="revenue_chart",
    title="Revenue/min",
    x="window_end",
    y="revenue",
    chart_type="area",
)

# Gauges for bounded metrics
sv.gauge(some_table, "cpu_usage",
    id="cpu",
    title="CPU",
    min=0, max=100,
    thresholds=[(50, "green"), (80, "yellow"), (100, "red")],
)

# Start server
sv.start(port=3000)

# Run Pathway
pw.run()

## Supported Pathway Features

### Reducers → Widget Mapping

| Reducer | Best Widget |
|---------|-------------|
| `count()` | stat, chart |
| `sum()` | stat, chart |
| `avg()` | stat, gauge, chart |
| `min()` | stat |
| `max()` | stat |
| `count_distinct()` | stat |
| `earliest()` | stat (timestamp) |
| `latest()` | stat (timestamp) |

### Windowing → Chart Types

| Window Type | Best Visualization |
|-------------|-------------------|
| Tumbling | Line/bar chart |
| Sliding | Line chart (smoothed) |
| Session | Event timeline |

### Table Operations

| Operation | Support |
|-----------|---------|
| `groupby().reduce()` | ✅ Table with keyed rows |
| `reduce()` | ✅ Single-row → stat/gauge |
| `windowby()` | ✅ Time series chart |
| `filter()` | ✅ Works transparently |
| `select()` | ✅ Choose columns |
| `join()` | ✅ Works transparently |
```
