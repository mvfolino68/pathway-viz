# StreamViz Vision

## One-Line Summary

**StreamViz is the visualization layer for Pathway** — making streaming aggregations visible, shareable, and beautiful.

---

## The Problem

Pathway is an incredible stream processing engine. But when you build a pipeline:

```python
stats = orders.groupby(pw.this.region).reduce(
    total=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)
```

**How do you see what's happening?**

Current options:
1. `pw.io.csv.write()` and tail the file → ugly, no visualization
2. Build a custom dashboard → days of work
3. Grafana/Datadog → infrastructure overhead, learning curve
4. Print statements → ephemeral, can't share

**StreamViz answer**: One line of code, instant dashboard.

```python
sv.pathway_table(stats)  # Done.
```

---

## Target Users

### Primary: Pathway Developers

**Persona**: Data engineer building streaming pipelines with Pathway.

**Jobs to be done**:
- "I want to see my Pathway aggregations updating live"
- "I need to demo this pipeline to stakeholders"
- "I'm debugging why my windowed join isn't working"
- "I want a simple dashboard without setting up Grafana"

**Why they'll love StreamViz**:
- Zero learning curve — Pythonic API they already know
- Works with their existing Pathway code
- No infrastructure to set up
- Professional-looking output for demos

### Secondary: Stream Processing Explorers

**Persona**: Developer evaluating Pathway or learning stream processing.

**Jobs to be done**:
- "I want to understand what tumbling windows do"
- "Show me the data flowing through my pipeline"
- "I'm following a tutorial and want to see results"

**Why they'll love StreamViz**:
- Immediate visual feedback while learning
- Makes abstract concepts concrete
- Great for tutorials and documentation

---

## Core Principle: Pathway Does the Hard Work

**We don't compete with Pathway's aggregations. We visualize them.**

| Feature | Pathway | StreamViz |
|---------|---------|-----------|
| Windowed aggregations | ✅ Built-in | ❌ Not needed |
| Joins and transformations | ✅ Full support | ❌ Just visualize output |
| Kafka/Redpanda connectors | ✅ Native | ✅ Via Pathway |
| Real-time updates | ✅ Core feature | ✅ Via WebSocket |
| Dashboard UI | ❌ | ✅ Core feature |
| Interactive charts | ❌ | ✅ Core feature |

StreamViz is the "last mile" — taking Pathway's output and making it visible.

---

## API Design

### The Dream API

```python
import pathway as pw
import stream_viz as sv

# === Pathway Pipeline ===
orders = pw.io.kafka.read(...)
by_region = orders.groupby(pw.this.region).reduce(
    total=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)
totals = orders.reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    orders=pw.reducers.count(),
)

# === StreamViz Dashboard ===
sv.title("E-Commerce Analytics")

# Show the aggregation table
sv.pathway_table(by_region, 
    title="Orders by Region",
    columns=["region", "total", "count"]
)

# Extract single values as stats
sv.pathway_stat(totals, column="revenue", title="Total Revenue", unit="$")
sv.pathway_stat(totals, column="orders", title="Total Orders")

# Time series from windowed aggregations
per_minute = orders.windowby(...).reduce(rps=pw.reducers.count())
sv.pathway_metric(per_minute, 
    time_column="window_end",
    value_column="rps",
    title="Orders/min"
)

sv.start()
pw.run()
```

### How It Works Under the Hood

```
┌──────────────────────────────────────────────────────────────────┐
│  sv.pathway_table(table)                                         │
│                                                                  │
│  1. Creates a Pathway output connector                           │
│  2. On each table update, serializes changed rows                │
│  3. Sends to StreamViz Rust core via channel                     │
│  4. Broadcasts to all WebSocket clients                          │
└──────────────────────────────────────────────────────────────────┘
```

Implementation sketch:

```python
def pathway_table(table: pw.Table, *, title: str = None, columns: list = None):
    """Subscribe to a Pathway table and visualize it."""
    
    widget_id = _register_table_widget(title, columns)
    
    def on_change(key, row, time, is_addition):
        if is_addition:
            _send_data({
                "widget": widget_id,
                "type": "table_upsert",
                "key": key,
                "row": row,
            })
        else:
            _send_data({
                "widget": widget_id,
                "type": "table_delete",
                "key": key,
            })
    
    # Use Pathway's output connector mechanism
    pw.io.subscribe(table, on_change=on_change)
```

---

## Widget Types

### 1. Pathway Table (`sv.pathway_table`)

Shows a Pathway table with live updates. Rows are keyed, so updates replace existing rows.

```python
sv.pathway_table(aggregation_table,
    title="Orders by Region",
    columns=["region", "total", "count"],
    sort_by="total",
    sort_desc=True,
    max_rows=100,
)
```

**Frontend behavior**:
- Shows table with headers
- Updates rows in-place (by key)
- Highlights recently changed rows
- Sortable columns
- Optional: sparklines in numeric columns

### 2. Pathway Stat (`sv.pathway_stat`)

Extracts a single value from a Pathway table (typically a single-row reduction).

```python
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
sv.pathway_stat(totals, column="revenue", title="Revenue", unit="$")
```

**Frontend behavior**:
- Big number display
- Shows delta from previous value
- Optional threshold colors

### 3. Pathway Metric (`sv.pathway_metric`)

Time series from a windowed Pathway aggregation.

```python
per_minute = orders.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=timedelta(minutes=1))
).reduce(count=pw.reducers.count())

sv.pathway_metric(per_minute,
    time_column="window_end",
    value_column="count",
    title="Orders/min"
)
```

**Frontend behavior**:
- Line chart with time on X axis
- Auto-scrolling as new windows arrive
- Zoomable

### 4. Standalone Widgets

For non-Pathway use cases (or mixed dashboards):

```python
# Manual data sending
cpu = sv.gauge("cpu", title="CPU", max_val=100)
cpu.send(75.5)

events = sv.table("events", columns=["time", "level", "msg"])
events.send({"time": "12:34", "level": "ERROR", "msg": "Failed"})

latency = sv.metric("latency", title="Latency", unit="ms")
latency.send(42.5)
```

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Python Process                              │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │  Pathway Engine │    │  StreamViz API  │    │  Rust Core     │  │
│  │                 │    │                 │    │  (PyO3)        │  │
│  │  table.reduce() │───▶│ pathway_table() │───▶│                │  │
│  │  windowby()     │    │ pathway_stat()  │    │  Ring Buffer   │  │
│  │  groupby()      │    │ pathway_metric()│    │  (per widget)  │  │
│  │                 │    │                 │    │                │  │
│  └─────────────────┘    └─────────────────┘    └───────┬────────┘  │
│                                                        │           │
└────────────────────────────────────────────────────────┼───────────┘
                                                         │
                                            WebSocket    │
                                            Broadcast    │
                                                         ▼
                              ┌───────────────────────────────────────┐
                              │            Browser (N)                │
                              │                                       │
                              │   ┌─────────┐ ┌─────────┐ ┌───────┐  │
                              │   │  Table  │ │  Chart  │ │ Gauge │  │
                              │   │         │ │         │ │       │  │
                              │   └─────────┘ └─────────┘ └───────┘  │
                              │                                       │
                              └───────────────────────────────────────┘
```

### Data Flow for Pathway Tables

1. **Pathway produces updates** via `pw.io.subscribe()`
2. **StreamViz receives** `(key, row, time, is_addition)`
3. **Rust core** stores in widget-specific buffer
4. **WebSocket broadcasts** to all connected browsers
5. **Frontend** updates table in-place using key

### Message Protocol

```json
// Config (on connect)
{
    "type": "config",
    "title": "E-Commerce Analytics",
    "widgets": {
        "orders_by_region": {
            "widget_type": "pathway_table",
            "title": "Orders by Region",
            "columns": [
                {"name": "region", "type": "string"},
                {"name": "total", "type": "number", "format": "$,.2f"},
                {"name": "count", "type": "number"}
            ]
        }
    }
}

// Table upsert
{
    "type": "data",
    "widget": "orders_by_region",
    "op": "upsert",
    "key": "us-east",
    "row": {"region": "us-east", "total": 15234.50, "count": 42}
}

// Table delete
{
    "type": "data",
    "widget": "orders_by_region", 
    "op": "delete",
    "key": "us-east"
}

// Stat update
{
    "type": "data",
    "widget": "total_revenue",
    "value": 152345.67,
    "delta": 1234.50
}

// Metric point
{
    "type": "data",
    "widget": "orders_per_min",
    "timestamp": 1701705600000,
    "value": 156
}
```

---

## Implementation Roadmap

### Phase 1: Pathway Integration (Next)

**Goal**: `sv.pathway_table()` works end-to-end.

Tasks:
- [ ] Implement `sv.pathway_table()` using `pw.io.subscribe()`
- [ ] Handle upserts and deletes in frontend table
- [ ] Highlight recently changed rows
- [ ] Test with real Kafka + Pathway pipeline

### Phase 2: Pathway Stats & Metrics

**Goal**: Full Pathway widget suite.

Tasks:
- [ ] `sv.pathway_stat()` — single value from table
- [ ] `sv.pathway_metric()` — time series from windowed aggregation
- [ ] Delta tracking for stats
- [ ] Proper time axis for metrics

### Phase 3: Polish

**Goal**: Production-ready for demos.

Tasks:
- [ ] Fix layout issues (table stretching charts)
- [ ] Add widget descriptions/subtitles
- [ ] Theming (dark/light)
- [ ] Pause/resume live updates
- [ ] Time range selector

### Phase 4: Advanced

**Goal**: Feature parity with simple dashboards.

Tasks:
- [ ] Layout system (`sv.columns()`, `sv.row()`)
- [ ] Export data (CSV/JSON)
- [ ] Snapshot dashboard as image
- [ ] Basic authentication

---

## Success Metrics

1. **Pathway adoption**: StreamViz mentioned in Pathway tutorials/docs
2. **Time to dashboard**: < 60 seconds from Pathway pipeline to visualization
3. **Demo quality**: Stakeholders impressed by dashboard appearance
4. **Performance**: Handle Pathway pipelines producing 10k updates/sec

---

## Open Questions

1. **Should we bundle with Pathway?** (As `pw.viz.table()` instead of separate package)
2. **How do we handle high-cardinality tables?** (100k rows in groupby)
3. **Do we need server-side pagination?**
4. **Should Pathway team be involved in design?**

---

## Competitive Positioning

### vs Grafana
- ❌ Grafana: Requires infrastructure, PromQL learning curve
- ✅ StreamViz: One `pip install`, Python-native

### vs Streamlit
- ❌ Streamlit: Request-response, awkward for streaming
- ✅ StreamViz: Streaming-first, Pathway-native

### vs Custom Dashboard
- ❌ Custom: Days/weeks of development
- ✅ StreamViz: Minutes to dashboard

### vs Print Statements
- ❌ Print: Ephemeral, no visualization, can't share
- ✅ StreamViz: Persistent, visual, shareable URL

---

## The Pitch

> "Pathway gives you world-class stream processing.
> StreamViz gives you world-class stream visualization.
> Together: the complete streaming data platform for Python."
