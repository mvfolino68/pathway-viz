# Widgets Reference

PathwayViz provides four widget types for different visualization needs.

## stat — Big Numbers

Display a single prominent value with optional delta indicator.

```python
# Pathway mode
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))
sv.stat(totals, "revenue", title="Total Revenue", unit="$")

# Manual mode
revenue = sv.stat("revenue", title="Total Revenue", unit="$")
revenue.send(125000)
```

### Parameters

| Parameter | Type         | Default     | Description                              |
| --------- | ------------ | ----------- | ---------------------------------------- |
| `source`  | Table \| str | required    | Pathway table or widget ID               |
| `column`  | str          | None        | Column to display (required for Pathway) |
| `id`      | str          | auto        | Widget identifier                        |
| `title`   | str          | column name | Display title                            |
| `unit`    | str          | ""          | Unit suffix ($, %, ms, etc.)             |
| `color`   | str          | auto        | Text color                               |
| `format`  | str          | None        | Python format string (",.2f")            |
| `delta`   | bool         | True        | Show change from previous value          |
| `embed`   | bool         | False       | Enable /embed/{id} endpoint              |

### Use Cases

- Revenue totals
- Order counts
- Active users
- Error rates

---

## chart — Time Series

Display values over time as line or area chart.

```python
# Pathway mode with windowing
orders_per_min = orders.windowby(
    pw.this.timestamp,
    window=pw.temporal.tumbling(duration=timedelta(minutes=1)),
).reduce(
    window_end=pw.this._pw_window_end,
    count=pw.reducers.count(),
)
sv.chart(orders_per_min, "count", x_column="window_end", title="Orders/min")

# Manual mode
latency = sv.chart("latency", title="Latency", unit="ms")
latency.send(45.2)  # Timestamp auto-generated
latency.send(52.1, timestamp=1702300000)  # Custom timestamp
```

### Parameters

| Parameter    | Type         | Default     | Description                                |
| ------------ | ------------ | ----------- | ------------------------------------------ |
| `source`     | Table \| str | required    | Pathway table or widget ID                 |
| `y_column`   | str          | None        | Value column (required for Pathway)        |
| `x_column`   | str          | None        | Time column (uses Pathway time if not set) |
| `id`         | str          | auto        | Widget identifier                          |
| `title`      | str          | column name | Display title                              |
| `unit`       | str          | ""          | Y-axis unit                                |
| `color`      | str          | auto        | Line/fill color                            |
| `chart_type` | str          | "line"      | "line" or "area"                           |
| `max_points` | int          | 200         | Max data points to display                 |
| `height`     | int          | None        | Chart height in pixels                     |
| `embed`      | bool         | False       | Enable /embed/{id} endpoint                |

### Use Cases

- Requests over time
- Revenue trends
- Latency monitoring
- CPU/memory history

---

## gauge — Bounded Values

Circular gauge for percentage-like bounded values.

```python
# Pathway mode
system = ...reduce(cpu=pw.reducers.avg(pw.this.cpu_pct))
sv.gauge(
    system, "cpu",
    title="CPU",
    max_val=100,
    unit="%",
    thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")],
)

# Manual mode
cpu = sv.gauge("cpu", title="CPU", max_val=100, unit="%")
cpu.send(72)
```

### Parameters

| Parameter    | Type         | Default     | Description                              |
| ------------ | ------------ | ----------- | ---------------------------------------- |
| `source`     | Table \| str | required    | Pathway table or widget ID               |
| `column`     | str          | None        | Column to display (required for Pathway) |
| `id`         | str          | auto        | Widget identifier                        |
| `title`      | str          | column name | Display title                            |
| `unit`       | str          | ""          | Unit suffix                              |
| `min_val`    | float        | 0           | Minimum scale value                      |
| `max_val`    | float        | 100         | Maximum scale value                      |
| `color`      | str          | auto        | Gauge color                              |
| `thresholds` | list         | None        | Color zones: [(value, color), ...]       |
| `embed`      | bool         | False       | Enable /embed/{id} endpoint              |

### Thresholds

Define color zones that change based on value:

```python
thresholds=[
    (50, "#00ff88"),   # Green: 0-50
    (80, "#ffd93d"),   # Yellow: 50-80
    (100, "#ff6b6b"),  # Red: 80-100
]
```

### Use Cases

- CPU utilization
- Memory usage
- Disk space
- SLA compliance percentages

---

## table — Live Data Tables

Display grouped data or event streams as a table.

```python
# Pathway mode (auto-updates)
by_region = orders.groupby(pw.this.region).reduce(
    region=pw.this.region,
    revenue=pw.reducers.sum(pw.this.amount),
    orders=pw.reducers.count(),
)
sv.table(
    by_region,
    title="Revenue by Region",
    columns=["region", "revenue", "orders"],
    column_labels={"revenue": "Revenue ($)", "orders": "Order Count"},
    sort_by="revenue",
    sort_desc=True,
)

# Manual mode (append rows)
events = sv.table("events", title="Events", columns=["time", "level", "msg"])
events.send({"time": "12:00:01", "level": "INFO", "msg": "Started"})
events.send({"time": "12:00:02", "level": "ERROR", "msg": "Failed"})
```

### Parameters

| Parameter       | Type         | Default  | Description                         |
| --------------- | ------------ | -------- | ----------------------------------- |
| `source`        | Table \| str | required | Pathway table or widget ID          |
| `id`            | str          | auto     | Widget identifier                   |
| `title`         | str          | "Table"  | Display title                       |
| `columns`       | list         | all      | Which columns to display            |
| `column_labels` | dict         | None     | Display names: {"col": "Label"}     |
| `column_format` | dict         | None     | Format strings: {"amount": "$,.2f"} |
| `max_rows`      | int          | 100      | Maximum rows to show                |
| `sort_by`       | str          | None     | Column to sort by                   |
| `sort_desc`     | bool         | True     | Sort descending                     |
| `embed`         | bool         | False    | Enable /embed/{id} endpoint         |

### Pathway vs Manual Mode

**Pathway mode:** Table reflects the current state of the Pathway table. Rows are upserted/deleted based on primary key.

**Manual mode:** Rows are appended. Old rows scroll off when `max_rows` is reached.

### Use Cases

- Grouped aggregations (by region, category, etc.)
- Recent events/logs
- Top N items
- Leaderboards

---

## Embedding

Enable embedding to use widgets in external pages:

```python
sv.configure(embed=True)
sv.stat("revenue", title="Revenue", embed=True)
sv.chart("latency", title="Latency", embed=True)
sv.start()
```

Access individual widgets at:

- `http://localhost:3000/embed/revenue`
- `http://localhost:3000/embed/latency`

### HTML Embed

```html
<iframe
  src="http://localhost:3000/embed/revenue"
  style="border: none; width: 250px; height: 150px;"
></iframe>
```

### React Component

```tsx
// components/PathwayVizWidget.tsx
"use client";
import { useEffect, useRef } from "react";

interface Props {
  widgetId: string;
  serverUrl?: string;
  className?: string;
}

export function PathwayVizWidget({
  widgetId,
  serverUrl = "http://localhost:3000",
  className = "",
}: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  return (
    <iframe
      ref={iframeRef}
      src={`${serverUrl}/embed/${widgetId}`}
      className={className}
      style={{ border: "none", width: "100%", height: "100%" }}
    />
  );
}

// Usage
<PathwayVizWidget widgetId="revenue" className="h-32" />;
```

### Svelte Component

```svelte
<!-- PathwayVizWidget.svelte -->
<script lang="ts">
  interface Props {
    widgetId: string;
    serverUrl?: string;
    class?: string;
  }

  let {
    widgetId,
    serverUrl = "http://localhost:3000",
    class: className = ""
  }: Props = $props();
</script>

<iframe
  src="{serverUrl}/embed/{widgetId}"
  class={className}
  style="border: none; width: 100%; height: 100%;"
  title={widgetId}
></iframe>
```

---

## Layout Control

Widgets appear in the order you create them. Currently, PathwayViz uses a responsive grid layout automatically.

```python
# These appear in order: left to right, top to bottom
sv.stat("revenue", title="Revenue")
sv.stat("orders", title="Orders")
sv.stat("avg", title="Average")
sv.chart("trend", title="Trend")
sv.table("breakdown", title="Breakdown")
```

## Colors

PathwayViz auto-assigns colors from a palette, or specify your own:

```python
sv.stat("revenue", color="#00ff88")
sv.chart("errors", color="#ff6b6b")
```

Default palette:

- `#00d4ff` (cyan)
- `#00ff88` (green)
- `#ff6b6b` (red)
- `#ffd93d` (yellow)
- `#c44dff` (purple)
- `#ff8c42` (orange)
