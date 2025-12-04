# StreamViz Vision & Architecture

## The Problem We're Solving

**Current reality**: Engineers working with streaming data (Kafka, Redpanda, Flink, Pathway) have limited options:
1. **Grafana/Datadog** - Great, but requires infrastructure, PromQL/InfluxQL, and doesn't integrate with Python code
2. **Streamlit** - Amazing DX, but designed for request-response, not real-time streaming
3. **Custom dashboards** - Every team builds their own, wasting engineering time

**StreamViz goal**: The simplicity of Streamlit, but purpose-built for streaming data. One `pip install`, one Python file, real-time dashboards.

---

## Target Use Cases

### 1. **Development & Debugging** (Primary)
- "I'm building a Kafka consumer and want to see what's happening"
- "I'm testing a Pathway pipeline and need to visualize aggregations"
- "I want to see my ML model's predictions as they stream in"

**Requirements**:
- Zero config startup
- Works with any Python streaming code
- Shows data immediately

### 2. **Team Demos & Presentations**
- "I want to show stakeholders our real-time fraud detection"
- "Demo our streaming ETL pipeline to the team"

**Requirements**:
- Professional-looking dashboards
- Theming/branding options
- Shareable URLs

### 3. **Lightweight Production Monitoring**
- "I need a simple dashboard for our internal streaming service"
- "We don't want to set up Grafana for a small project"

**Requirements**:
- Data persistence (new viewers see history)
- Multiple concurrent viewers
- Basic alerting/thresholds

### 4. **Data Exploration**
- "I want to explore patterns in my streaming data"
- "Let me filter and zoom into specific time ranges"

**Requirements**:
- Interactive charts (zoom, pan, filter)
- Time range selection
- Pause/resume streaming

---

## Core Design Principles

### 1. **Progressive Complexity**
```python
# Level 1: Just works (5 seconds to dashboard)
import stream_viz as sv
sv.metric("cpu").send(75)

# Level 2: Customized (5 minutes to polished dashboard)
sv.title("Production Metrics")
cpu = sv.metric("cpu", title="CPU Usage", unit="%", 
                window="1m", aggregation="avg",
                thresholds={"warning": 70, "critical": 90})

# Level 3: Full control (production-ready)
sv.configure(
    theme="dark",
    persistence="sqlite:///metrics.db",
    retention="7d",
    auth={"type": "basic", "users": ["admin"]},
)
```

### 2. **Streaming-First, Not Adapted**
Unlike Streamlit (which retrofitted `st.write_stream`), we're built for:
- **Continuous data flow** - not request-response
- **Windowed aggregations** - built into the API
- **Backpressure handling** - won't crash on high throughput
- **Time-series native** - every data point has a timestamp

### 3. **Batteries Included, But Swappable**
- Default charting library works great out of box
- But can swap for Apache ECharts, Plotly, etc.
- Default in-memory storage
- But can plug in Redis, SQLite, TimescaleDB

---

## Architecture Decisions

### Frontend: Chart Library Selection

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **uPlot** (current) | Tiny (45kb), fast, good for time-series | Limited chart types, basic interactivity | Good for MVP |
| **Apache ECharts** | Rich features, great interactivity, streaming support | Larger (800kb min) | **Best choice for v1** |
| **Plotly.js** | Beautiful, well-known | Very large (3MB+), not streaming-optimized | Too heavy |
| **Lightweight Charts** | Designed for financial streaming | Limited to candlestick/line | Too specialized |
| **Chart.js** | Popular, decent | Poor streaming performance | Not suitable |

**Decision**: Migrate to **Apache ECharts** because:
- Native streaming/dynamic data support
- Rich interactivity (zoom, pan, brush selection, tooltips)
- Multiple chart types (line, bar, gauge, heatmap, scatter)
- Theming system built-in
- Good performance with large datasets
- 300kb gzipped is acceptable

### Backend: Data Persistence

**Problem**: Currently, when a new user opens the dashboard, they see nothing until new data arrives.

**Solution**: Tiered storage with sensible defaults

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Process                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Ring Buffer (in-memory, last N points per metric)  │   │
│  │  - Always available, zero config                     │   │
│  │  - Lost on restart                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Persistence Layer (optional)                        │   │
│  │  - SQLite (default if enabled)                       │   │
│  │  - Redis (for distributed)                           │   │
│  │  - TimescaleDB (for serious production)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Default behavior**:
- Keep last 1000 points per metric in memory
- New connections receive full buffer immediately
- Optional: `sv.configure(persistence="sqlite:///data.db", retention="24h")`

### Data Flow Architecture

```
                                    ┌──────────────────┐
                                    │   Browser (N)    │
                                    │  ┌────────────┐  │
                                    │  │  ECharts   │  │
                                    │  │  Dashboard │  │
                                    │  └────────────┘  │
                                    └────────┬─────────┘
                                             │ WebSocket
                                             ▼
┌─────────────────┐    send()     ┌──────────────────────┐
│  Python Code    │──────────────▶│   Rust Core          │
│                 │               │  ┌────────────────┐  │
│  metric.send(v) │               │  │ Ring Buffer    │  │
│  table.append() │               │  │ (per widget)   │  │
│  gauge.set()    │               │  └───────┬────────┘  │
└─────────────────┘               │          │           │
                                  │          ▼           │
                                  │  ┌────────────────┐  │
                                  │  │ Broadcast to   │  │
                                  │  │ all WebSockets │  │
                                  │  └────────────────┘  │
                                  │          │           │
                                  │          ▼           │
                                  │  ┌────────────────┐  │
                                  │  │ Persistence    │  │
                                  │  │ (optional)     │  │
                                  │  └────────────────┘  │
                                  └──────────────────────┘
```

---

## API Design (v1.0)

### Widget Types

```python
import stream_viz as sv

# === METRICS (time-series) ===
cpu = sv.metric("cpu", 
    title="CPU Usage",
    unit="%",
    color="#00d4ff",
    window="1m",           # Aggregate over 1 minute windows
    aggregation="avg",     # sum, avg, min, max, count, rate, p50, p95, p99
    max_points=500,        # History length
    thresholds={           # Color zones
        "warning": 70,
        "critical": 90
    }
)
cpu.send(75.5)

# === STATS (big numbers) ===
total = sv.stat("total_orders",
    title="Total Orders",
    format=",.0f",         # Number formatting
    delta=True,            # Show change from last value
    delta_color="auto",    # green for +, red for -
    sparkline=True,        # Mini chart behind the number
)
total.send(15234)

# === GAUGES (bounded values) ===
temp = sv.gauge("temperature",
    title="Server Temp",
    unit="°C",
    min=0,
    max=100,
    thresholds=[(50, "green"), (70, "yellow"), (100, "red")],
)
temp.send(62)

# === MULTI-SERIES CHARTS ===
chart = sv.line_chart("temperatures",
    title="Component Temps",
    y_axis={"label": "°C", "min": 0, "max": 100},
)
chart.add_series("cpu", color="red", label="CPU")
chart.add_series("gpu", color="blue", label="GPU")
chart.send("cpu", 65)
chart.send("gpu", 72)

# === BAR CHARTS ===
regions = sv.bar_chart("traffic",
    title="Traffic by Region",
    categories=["US", "EU", "Asia"],
    stacked=False,
)
regions.send({"US": 1200, "EU": 980, "Asia": 1450})

# === TABLES (streaming) ===
logs = sv.table("events",
    title="Recent Events",
    columns=[
        {"name": "time", "type": "datetime", "width": 100},
        {"name": "level", "type": "badge", "colors": {"ERROR": "red", "WARN": "yellow"}},
        {"name": "message", "type": "text"},
    ],
    max_rows=100,
    sortable=True,
    filterable=True,
)
logs.send({"time": datetime.now(), "level": "ERROR", "message": "Connection failed"})

# === TEXT/MARKDOWN ===
status = sv.text("status", style="caption")
status("Connected to Kafka cluster")

sv.markdown("notes", """
## Pipeline Status
- **Source**: Kafka (3 partitions)
- **Sink**: PostgreSQL
""")

# === HEATMAPS ===
heatmap = sv.heatmap("latency_distribution",
    title="Latency by Hour",
    x_labels=["Mon", "Tue", "Wed", "Thu", "Fri"],
    y_labels=["00:00", "06:00", "12:00", "18:00"],
)
heatmap.send([[10, 20, 30, 40, 50], ...])
```

### Layout System

```python
# Simple: auto-layout (current behavior)
sv.metric("cpu")
sv.metric("memory")
# Renders in 2-column grid

# Explicit columns
with sv.columns(3):
    sv.stat("orders")
    sv.stat("revenue")
    sv.stat("users")

# Rows within columns
with sv.columns(2):
    with sv.column():
        sv.metric("cpu", title="CPU")
        sv.metric("memory", title="Memory")
    with sv.column():
        sv.table("logs")

# Expanders (collapsible sections)
with sv.expander("Advanced Metrics", expanded=False):
    sv.metric("gc_time")
    sv.metric("heap_size")

# Tabs
with sv.tabs(["Overview", "Details", "Logs"]):
    with sv.tab("Overview"):
        sv.stat("total")
    with sv.tab("Details"):
        sv.table("details")
    with sv.tab("Logs"):
        sv.table("logs")

# Sidebar
with sv.sidebar():
    sv.text("Filters")
    # Future: interactive widgets
```

### Configuration & Theming

```python
sv.configure(
    # === Appearance ===
    theme="dark",              # "dark", "light", or custom
    title="My Dashboard",
    favicon="/path/to/icon.png",
    logo="/path/to/logo.png",
    
    # === Behavior ===
    auto_refresh=True,         # Auto-scroll charts
    default_time_range="5m",   # Initial view window
    
    # === Persistence ===
    persistence=None,          # None, "memory", "sqlite:///path", "redis://host"
    retention="24h",           # How long to keep data
    buffer_size=1000,          # In-memory ring buffer per metric
    
    # === Server ===
    host="0.0.0.0",
    port=3000,
    cors=True,
    
    # === Auth (future) ===
    auth=None,                 # None, {"type": "basic", "users": {...}}
)

# Custom themes
sv.configure(theme={
    "background": "#1a1a2e",
    "surface": "#16213e",
    "primary": "#00d4ff",
    "secondary": "#7b2cbf",
    "success": "#00ff88",
    "warning": "#ffd93d",
    "error": "#ff6b6b",
    "text": "#e0e0e0",
    "text_muted": "#888888",
    "font_family": "Inter, sans-serif",
})
```

### Interactivity (Frontend Features)

```
┌─────────────────────────────────────────────────────────────────┐
│  My Dashboard                               ● Live  ⏸ Pause    │
├─────────────────────────────────────────────────────────────────┤
│  Time Range: [5m ▼] [15m] [1h] [6h] [24h] [Custom...]          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ CPU Usage      75%  │  │ Memory        62%   │              │
│  │ ████████████░░░░░░  │  │ ██████████░░░░░░░░  │              │
│  │ [Chart with zoom]   │  │ [Chart with zoom]   │              │
│  │                     │  │                     │              │
│  │ 🔍 Click to zoom    │  │ 📊 Export CSV       │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
│  Recent Events                               [Filter: ____]    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Time     │ Level │ Message                              │   │
│  │ 12:34:56 │ ERROR │ Connection timeout                   │   │
│  │ 12:34:52 │ INFO  │ Request processed                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Interactive features**:
- **Pause/Resume**: Stop live updates to analyze data
- **Time range selector**: View last 5m, 15m, 1h, etc.
- **Zoom**: Click-drag to zoom into time range
- **Pan**: Shift+drag to pan through history
- **Tooltips**: Hover for exact values
- **Export**: Download data as CSV/JSON
- **Fullscreen**: Expand individual charts

---

## Windowed Aggregations (Built-in)

One of the key differentiators: **first-class support for stream processing patterns**.

### Tumbling Windows
```python
# Emit sum every minute
orders_per_min = sv.metric("orders", window="1m", aggregation="sum")

for order in kafka_consumer:
    orders_per_min.send(order["amount"])  # Aggregated automatically
```

### Sliding Windows (Future)
```python
# Moving average over last 5 minutes, emitting every 10 seconds
avg_latency = sv.metric("latency", 
    window="5m", 
    slide="10s",
    aggregation="avg"
)
```

### Percentiles
```python
# P95 latency per minute
p95_latency = sv.metric("latency_p95", 
    window="1m", 
    aggregation="p95"
)
```

### Implementation
The aggregation happens **in the Rust core** for performance:

```rust
struct WindowedAggregator {
    window_size: Duration,
    aggregation: AggregationType,
    buffer: VecDeque<(Timestamp, f64)>,
    // Pre-computed stats for O(1) updates
    sum: f64,
    count: u64,
    min: f64,
    max: f64,
    // For percentiles: t-digest or similar
    digest: Option<TDigest>,
}
```

---

## Data Persistence Design

### The Problem
Currently, when you open the dashboard:
1. You see "Waiting for metrics..."
2. Data only appears as new values arrive
3. Refresh the page = lose everything

### The Solution: Ring Buffer + Optional Persistence

**Phase 1: In-Memory Ring Buffer (Default)**
```python
# Automatic - no config needed
# Last 1000 points per metric kept in memory
# New connections receive full buffer
```

**Phase 2: SQLite Persistence (Opt-in)**
```python
sv.configure(
    persistence="sqlite:///metrics.db",
    retention="24h"
)
# Now data survives restarts
# New connections get historical data
```

**Phase 3: Distributed Storage (Future)**
```python
sv.configure(
    persistence="redis://localhost:6379",
    # or
    persistence="timescaledb://user:pass@host/db"
)
```

### Message Protocol Enhancement

Currently we send:
```json
{"type": "data", "metric": "cpu", "timestamp": 1234567890, "value": 75.5}
```

Enhanced for history:
```json
// On new connection, server sends buffer dump
{
    "type": "history",
    "widget": "cpu",
    "data": [
        [1234567800, 72.3],
        [1234567810, 73.1],
        [1234567820, 75.5],
        // ... last N points
    ]
}

// Then continues with live updates
{"type": "data", "widget": "cpu", "timestamp": 1234567890, "value": 76.2}
```

---

## Implementation Roadmap

### Phase 1: Core Improvements (This Sprint)
- [ ] **Ring buffer in Rust** - Keep last N points per widget
- [ ] **History on connect** - Send buffer to new WebSocket connections
- [ ] **Windowed aggregations** - Tumbling windows in Rust
- [ ] **New widget types** - stat, gauge (Python API)
- [ ] **Frontend: ECharts migration** - Replace uPlot

### Phase 2: Interactivity (Next Sprint)
- [ ] **Time range selector** - UI to change visible window
- [ ] **Pause/Resume** - Stop live updates
- [ ] **Zoom/Pan** - Chart interactions
- [ ] **Theming** - Dark/light + custom themes
- [ ] **Layout system** - columns(), row(), expander()

### Phase 3: Production Features
- [ ] **SQLite persistence** - Survive restarts
- [ ] **Multiple pages** - sv.page("metrics"), sv.page("logs")
- [ ] **Export** - CSV/JSON download
- [ ] **Alerts** - Threshold notifications (console, webhook)

### Phase 4: Advanced
- [ ] **Authentication** - Basic auth, API keys
- [ ] **Redis persistence** - Distributed deployments
- [ ] **Embedded mode** - Use in Jupyter notebooks
- [ ] **Sliding windows** - More aggregation options
- [ ] **Percentile aggregations** - p50, p95, p99

---

## File Structure (After Refactor)

```
stream_viz/
├── python/
│   └── stream_viz/
│       ├── __init__.py          # Public API (sv.metric, sv.start, etc.)
│       ├── __main__.py          # CLI (python -m stream_viz)
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── metric.py        # Time-series metric
│       │   ├── stat.py          # Big number display
│       │   ├── gauge.py         # Circular gauge
│       │   ├── chart.py         # Multi-series charts
│       │   ├── table.py         # Streaming table
│       │   └── text.py          # Text/markdown
│       ├── aggregations/
│       │   ├── __init__.py
│       │   └── windows.py       # Tumbling/sliding window logic
│       ├── layout/
│       │   ├── __init__.py
│       │   └── containers.py    # columns, row, expander, tabs
│       ├── config.py            # sv.configure() implementation
│       └── themes.py            # Theme definitions
├── src/                         # Rust core
│   ├── lib.rs
│   ├── server.rs                # Axum WebSocket server
│   ├── state.rs                 # Shared state, ring buffers
│   ├── aggregator.rs            # Windowed aggregation (NEW)
│   └── persistence.rs           # Storage backends (NEW)
├── frontend/
│   ├── index.html               # Main dashboard (embedded in binary)
│   ├── js/
│   │   ├── app.js               # Main application logic
│   │   ├── widgets/             # Widget renderers
│   │   └── themes/              # Theme CSS
│   └── css/
│       └── styles.css
└── examples/
    ├── simple_demo.py
    ├── kafka_demo.py
    ├── pathway_demo.py
    └── full_dashboard.py        # Showcases all features
```

---

## Success Metrics

1. **Time to first dashboard**: < 30 seconds from `pip install` to seeing data
2. **Performance**: Handle 10,000 data points/second without lag
3. **Memory efficiency**: < 100MB for typical dashboard with 1M points history
4. **Adoption**: Developers choose StreamViz over custom solutions

---

## Open Questions

1. **Should we support bi-directional communication?** (Frontend → Python for filters/controls)
2. **How do we handle very high throughput?** (Downsample before sending to browser?)
3. **Should persistence be in Rust or Python?** (Rust for performance, Python for flexibility)
4. **Do we need a separate "viewer" mode?** (Read-only dashboard without running Python)

---

## Next Steps

1. ✅ Create this vision document
2. 🔄 Implement ring buffer in Rust (send history on connect)
3. 🔄 Add windowed aggregations to Python API
4. 🔄 Migrate frontend to ECharts
5. 🔄 Add stat and gauge widgets
6. 🔄 Implement theming system
7. 🔄 Add time range selector to UI

Let's build the streaming dashboard that developers actually want to use.
