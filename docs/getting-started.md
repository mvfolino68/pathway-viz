# Getting Started

## Install

```bash
pip install pathway-viz
```

## Your First Dashboard

PathwayViz connects directly to [Pathway](https://pathway.com) tables and auto-updates when your streaming data changes.

Create a data file `orders.jsonl`:

```json
{"amount": 99.50, "region": "us-east"}
{"amount": 150.00, "region": "europe"}
{"amount": 75.25, "region": "us-east"}
```

Create `pipeline.py`:

```python
import pathway as pw
import pathwayviz as pv

class OrderSchema(pw.Schema):
    amount: float
    region: str

# Stream from a file (Pathway also supports Kafka, S3, PostgreSQL, etc.)
orders = pw.io.jsonlines.read(
    "./orders.jsonl",
    schema=OrderSchema,
    mode="streaming",
)

# Compute aggregations
totals = orders.reduce(
    revenue=pw.reducers.sum(pw.this.amount),
    count=pw.reducers.count(),
)

by_region = orders.groupby(pw.this.region).reduce(
    region=pw.this.region,
    revenue=pw.reducers.sum(pw.this.amount),
)

# Dashboard updates automatically when Pathway updates
pv.stat(totals, "revenue", title="Revenue", unit="$")
pv.stat(totals, "count", title="Orders")
pv.table(by_region, columns=["region", "revenue"])

pv.start()
pw.run()
```

Run it:

```bash
python pipeline.py
```

The dashboard shows your aggregations. Add more lines to `orders.jsonl` and watch the dashboard update.

To stream from Kafka, S3, or other sources, see [Pathway's connectors](https://pathway.com/developers/user-guide/connect/supported-data-sources/).

## Live Demo

Run the full e-commerce demo (requires Docker):

```bash
pip install pathway-viz[kafka]
pathway-viz demo
```

This starts Kafka, generates sample orders, and shows a real-time analytics dashboard.
