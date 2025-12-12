# E-Commerce Demo (Kafka + Pathway + PathwayViz + DuckDB)

This is the flagship PathwayViz demo. It simulates a production-ish streaming pipeline:

```text
order generator → Kafka/Redpanda → Pathway aggregations → PathwayViz dashboard + embeds
                                    ↘ DuckDB persistence
```

You run it with:

```bash
pathway-viz demo
```

## What You Get

- **A full dashboard** at `http://localhost:3000`
- **A “portal” page** at `http://localhost:3001` that embeds PathwayViz widgets via `<iframe>` (this is meant to resemble embedding into a real app)
- **Optional persistence** via DuckDB (`./data/pathwayviz.duckdb`) so the demo can preload "today so far" metrics on restart

## Prerequisites

- Python 3.11+
- Docker (the demo starts Redpanda via `docker compose`)

Optional but recommended:

- `duckdb` for persistence

## Install

```bash
pip install pathway-viz[demo]
```

This includes everything needed for the demo:

- Pathway for stream processing
- Kafka/Redpanda client
- DuckDB for persistence

If you're running from this repo:

```bash
pip install maturin
maturin develop
pip install .[demo]
```

## Run

```bash
pathway-viz demo
```

The demo will:

- Start `docker compose up -d` (Redpanda)
- Generate random orders into the `orders` Kafka topic
- Run Pathway to compute:
  - totals (revenue, order_count, avg_order)
  - revenue by region
  - revenue by category
- Update PathwayViz widgets in real time

## Widget IDs (useful for embedding)

The demo creates widgets with stable IDs, so they’re easy to embed:

- `revenue`
- `orders`
- `avg_order`
- `revenue_chart`
- `orders_chart`
- `us_east`, `us_west`, `europe`, `asia`
- `electronics`, `apparel`, `books`, `grocery`

Each one is available at:

```text
http://localhost:3000/embed/{widget_id}
```

## Where the Demo Lives

- Demo entrypoint: `python/pathway_viz/demos/pathway.py` (`run_pathway_demo`)
- Portal HTML: `python/pathway_viz/demos/portal.html`
- Kafka infra: `docker-compose.yml`

## Troubleshooting

- If you see “Docker not found”:
  - Install Docker Desktop
- If you see missing dependencies:
  - Install with `pip install pathway-viz[demo]`
- If port 3000 is busy:
  - Run `pathway-viz demo --port 3100` (portal becomes 3101)
