# Widgets Reference

## Which Widget Should I Use?

| I want to show...                           | Use this |
| ------------------------------------------- | -------- |
| A single number (revenue, count, avg)       | `stat`   |
| How something changes over time             | `chart`  |
| A percentage or bounded value (CPU, memory) | `gauge`  |
| A list of items (top customers, events)     | `table`  |

---

## stat

A big number, optionally showing how much it changed.

**When to use:** Totals, counts, averages—any single value you want prominent.

```python
pv.stat(totals, "revenue", title="Revenue", unit="$")
```

| Parameter  | Type  | Default     | Description                              |
| ---------- | ----- | ----------- | ---------------------------------------- |
| `pw_table` | Table | required    | Pathway table to display                 |
| `column`   | str   | None        | Column to display (required for Pathway) |
| `title`    | str   | column name | Display title                            |
| `unit`     | str   | ""          | Unit suffix ($, %, ms)                   |
| `format`   | str   | None        | Python format string (",.2f")            |
| `delta`    | bool  | True        | Show change from previous                |

---

## chart

A line or area chart showing values over time.

**When to use:** Trends, rates, anything where history matters.

```python
pv.chart(orders_per_min, "count", x_column="window_end", title="Orders/min")
```

| Parameter    | Type  | Default     | Description              |
| ------------ | ----- | ----------- | ------------------------ |
| `pw_table`   | Table | required    | Pathway table to display |
| `y_column`   | str   | None        | Value column             |
| `x_column`   | str   | None        | Time column              |
| `title`      | str   | column name | Display title            |
| `unit`       | str   | ""          | Y-axis unit              |
| `chart_type` | str   | "line"      | "line" or "area"         |
| `max_points` | int   | 200         | Max data points to show  |

---

## gauge

A circular gauge for values with a known range.

**When to use:** Percentages, utilization, anything with a min/max.

```python
pv.gauge(system, "cpu", title="CPU", max_val=100, unit="%")

# With color thresholds (green → yellow → red)
pv.gauge(system, "cpu", title="CPU", max_val=100, unit="%",
         thresholds=[(50, "#00ff88"), (80, "#ffd93d"), (100, "#ff6b6b")])
```

| Parameter    | Type  | Default  | Description                        |
| ------------ | ----- | -------- | ---------------------------------- |
| `pw_table`   | Table | required | Pathway table to display           |
| `column`     | str   | None     | Column to display                  |
| `min_val`    | float | 0        | Minimum scale                      |
| `max_val`    | float | 100      | Maximum scale                      |
| `thresholds` | list  | None     | Color zones: [(value, color), ...] |

---

## table

A live table that updates as data changes.

**When to use:** Grouped data, event logs, leaderboards.

```python
pv.table(by_region, columns=["region", "revenue"], sort_by="revenue")
```

| Parameter       | Type  | Default  | Description              |
| --------------- | ----- | -------- | ------------------------ |
| `pw_table`      | Table | required | Pathway table to display |
| `columns`       | list  | all      | Columns to display       |
| `column_labels` | dict  | None     | {"col": "Display Name"}  |
| `column_format` | dict  | None     | {"amount": "$,.2f"}      |
| `max_rows`      | int   | 100      | Maximum rows             |
| `sort_by`       | str   | None     | Sort column              |

Rows update in place based on Pathway's row key.

---

## Common Parameters

All widgets also support:

| Parameter | Type | Default | Description                       |
| --------- | ---- | ------- | --------------------------------- |
| `id`      | str  | auto    | Widget identifier (for embedding) |
| `color`   | str  | auto    | Widget color                      |
| `embed`   | bool | False   | Enable `/embed/{id}` endpoint     |

## Colors

Colors are auto-assigned, or specify your own:

```python
pv.stat(totals, "revenue", color="#00ff88")
```

Default palette: `#00d4ff` `#00ff88` `#ff6b6b` `#ffd93d` `#c44dff` `#ff8c42`
