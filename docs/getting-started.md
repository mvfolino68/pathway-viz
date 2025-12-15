# Getting Started

## Install

```bash
pip install pathway-viz
```

## Your First Widget Server

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

# Create widget server and register widgets
server = pv.WidgetServer(port=3000)
server.register(pv.Stat(totals, "revenue", id="revenue", title="Revenue", unit="$"))
server.register(pv.Stat(totals, "count", id="orders", title="Orders"))
server.register(pv.Table(by_region, id="regions", columns=["region", "revenue"]))

server.start()
pw.run()
```

Run it:

```bash
python pipeline.py
```

Open `http://localhost:3000` to see all widgets. Embed individual widgets via:

```html
<iframe src="http://localhost:3000/embed/revenue"></iframe>
```

Add more lines to `orders.jsonl` and watch the widgets update in real-time.

To stream from Kafka, S3, or other sources, see [Pathway's connectors](https://pathway.com/developers/user-guide/connect/supported-data-sources/).

## Live Demo

Run the full e-commerce demo (requires Docker):

```bash
pip install pathway-viz[kafka]
pathway-viz demo
```

This starts Kafka, generates sample orders, and shows real-time widgets.
