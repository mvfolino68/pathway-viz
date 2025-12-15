# Widgets Reference

## Which Widget Should I Use?

| I want to show...                           | Use this |
| ------------------------------------------- | -------- |
| A single number (revenue, count, avg)       | `Stat`   |
| How something changes over time             | `Chart`  |
| A percentage or bounded value (CPU, memory) | `Gauge`  |
| A list of items (top customers, events)     | `Table`  |

---

## Stat

A big number, optionally showing how much it changed.

**When to use:** Totals, counts, averages—any single value you want prominent.

```python
server.register(pv.Stat(totals, "revenue", id="revenue", title="Revenue", unit="$"))
```

| Parameter  | Type  | Default     | Description                       |
| ---------- | ----- | ----------- | --------------------------------- |
| `pw_table` | Table | required    | Pathway table to display          |
| `column`   | str   | required    | Column to display                 |
| `id`       | str   | auto        | Widget identifier (for embedding) |
| `title`    | str   | column name | Display title                     |
| `unit`     | str   | ""          | Unit suffix ($, %, ms)            |
| `format`   | str   | None        | Python format string (",.2f")     |
| `delta`    | bool  | True        | Show change from previous         |
| `color`    | str   | auto        | Text color                        |

---

## Chart

A line or area chart showing values over time.

**When to use:** Trends, rates, anything where history matters.

```python
server.register(pv.Chart(orders_per_min, "count", id="orders", x_column="window_end", title="Orders/min"))
```

| Parameter     | Type  | Default     | Description                           |
| ------------- | ----- | ----------- | ------------------------------------- |
| `pw_table`    | Table | required    | Pathway table to display              |
| `y_column`    | str   | required    | Value column                          |
| `id`          | str   | auto        | Widget identifier                     |
| `x_column`    | str   | None        | Time column (uses wall-clock if None) |
| `title`       | str   | column name | Display title                         |
| `unit`        | str   | ""          | Y-axis unit                           |
| `chart_type`  | str   | "line"      | "line" or "area"                      |
| `max_points`  | int   | 200         | Max data points to show               |
| `time_window` | int   | 120         | Rolling window in seconds             |
| `color`       | str   | auto        | Line/fill color                       |

---

## Gauge

A circular gauge for values with a known range.

**When to use:** Percentages, utilization, anything with a min/max.

```python
server.register(pv.Gauge(system, "cpu", id="cpu", title="CPU", max_val=100, unit="%"))

# With color thresholds (green → yellow → red)
server.register(pv.Gauge(system, "cpu", id="cpu", title="CPU", max_val=100, unit="%",
                         thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")]))
```

| Parameter    | Type  | Default  | Description                        |
| ------------ | ----- | -------- | ---------------------------------- |
| `pw_table`   | Table | required | Pathway table to display           |
| `column`     | str   | required | Column to display                  |
| `id`         | str   | auto     | Widget identifier                  |
| `min_val`    | float | 0        | Minimum scale                      |
| `max_val`    | float | 100      | Maximum scale                      |
| `thresholds` | list  | None     | Color zones: [(value, color), ...] |
| `color`      | str   | auto     | Gauge color                        |

---

## Table

A live table that updates as data changes.

**When to use:** Grouped data, event logs, leaderboards.

```python
server.register(pv.Table(by_region, id="regions", columns=["region", "revenue"], sort_by="revenue"))
```

| Parameter       | Type  | Default  | Description              |
| --------------- | ----- | -------- | ------------------------ |
| `pw_table`      | Table | required | Pathway table to display |
| `id`            | str   | auto     | Widget identifier        |
| `columns`       | list  | all      | Columns to display       |
| `column_labels` | dict  | None     | {"col": "Display Name"}  |
| `column_format` | dict  | None     | {"amount": "$,.2f"}      |
| `max_rows`      | int   | 100      | Maximum rows             |
| `sort_by`       | str   | None     | Sort column              |

Rows update in place based on Pathway's row key.

---

## WidgetServer

The server that hosts all widgets.

```python
server = pv.WidgetServer(port=3000, title="My Widgets", theme="dark")
server.register(pv.Stat(...))
server.register(pv.Chart(...))
server.start()
```

| Parameter | Type | Default      | Description                     |
| --------- | ---- | ------------ | ------------------------------- |
| `port`    | int  | 3000         | Server port                     |
| `title`   | str  | "PathwayViz" | Browser tab title               |
| `theme`   | str  | "dark"       | Color theme ("dark" or "light") |

## Colors

Colors are auto-assigned, or specify your own:

```python
pv.Stat(totals, "revenue", id="revenue", color="#00ff88")
```

Default palette: `#00d4ff` `#00ff88` `#ff6b6b` `#ffd93d` `#c44dff` `#ff8c42`
