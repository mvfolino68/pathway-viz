# StreamViz Vision

## Mission

**StreamViz is the visualization layer for Pathway.**

Pathway handles the hard parts of streaming data — ingestion, transformations, aggregations, windowing. StreamViz takes Pathway's outputs and makes them visible, in real-time, with zero configuration.

## Core Principles

### 1. Pathway First

The primary API is designed around Pathway tables:

```python
sv.table(pw_table)      # Not sv.table("id")
sv.stat(pw_table, col)  # Not sv.stat("id")
```

Pass a Pathway table, get live updates. That's it.

### 2. Batteries Included

No JavaScript. No npm. No build step. Just:

```bash
pip install stream-viz
```

The frontend is embedded in the Rust binary. The server starts in a thread. You write Python, you get a dashboard.

### 3. Production Ready

StreamViz is built for production observability, not just prototyping:

- **Embeddable** — Drop widgets into existing web apps
- **Fast** — Rust WebSocket server handles thousands of updates/sec
- **Reliable** — Reconnects automatically, preserves state

### 4. Simple API

Four widget types cover 90% of use cases:

| Widget | Use | Pathway Source |
|--------|-----|----------------|
| `table` | Live rows | `groupby().reduce()` |
| `stat` | Single value | `reduce()` |
| `chart` | Time series | `windowby().reduce()` |
| `gauge` | Bounded value | `reduce()` (percentages) |

## Target Users

### Primary: Pathway Users

Developers building streaming pipelines with Pathway who need visibility into their aggregations.

**Their Journey:**

1. Build Pathway pipeline
2. Add `sv.table(my_aggregation)`
3. See it working

### Secondary: Python Developers

Anyone who wants quick real-time dashboards without frontend complexity.

**Their Journey:**

1. `pip install stream-viz`
2. Create widgets, call `.send()`
3. Dashboard running in 5 minutes

## Non-Goals

- **Not a general dashboarding tool** — Use Grafana/Superset for SQL databases
- **Not a Jupyter widget** — Pathway already has Panel integration for notebooks
- **Not a complex layout system** — Keep it simple, embed if you need custom layouts

## Technical Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         User's Python Code                         │
│                                                                     │
│   import pathway as pw                                              │
│   import stream_viz as sv                                           │
│                                                                     │
│   stats = orders.groupby(...).reduce(...)                           │
│   sv.table(stats, title="Orders")  ←── sv.table() calls             │
│   sv.start()                            pw.io.subscribe()           │
│   pw.run()                                                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ JSON messages
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Rust WebSocket Server (axum)                     │
│                                                                     │
│   Routes:                                                           │
│     /          → Full dashboard HTML                                │
│     /embed/:id → Single widget HTML                                 │
│     /ws        → WebSocket for live updates                         │
│                                                                     │
│   State:                                                            │
│     - Widget config cache                                           │
│     - Data point ring buffers (for history on reconnect)            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Browser (embedded HTML/JS)                      │
│                                                                     │
│   - uPlot for charts                                                │
│   - Custom widgets (gauges, tables, stats)                          │
│   - Auto-reconnect                                                  │
│   - Embed mode for single widgets                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Roadmap

### Now (v0.1)

- [x] Core widgets: table, stat, chart, gauge
- [x] Pathway integration via `pw.io.subscribe()`
- [x] Embedded Rust server
- [x] Embed mode for single widgets
- [x] Manual mode for non-Pathway use

### Next (v0.2)

- [ ] Theme customization
- [ ] More chart types (bar, area)
- [ ] Widget sizing hints
- [ ] Export functionality (PNG, data)

### Future

- [ ] Alerts and thresholds
- [ ] Multiple dashboards
- [ ] JavaScript embed library
- [ ] Authentication
