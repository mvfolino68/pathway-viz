# StreamViz Examples

This folder contains example scripts demonstrating different StreamViz use cases.

## Quick Start

### No Dependencies

```bash
python examples/simple_demo.py
```

Open <http://localhost:3000> to see four animated wave charts.

### With Kafka/Redpanda

```bash
# Install Kafka dependencies
pip install stream-viz[kafka]

# Start Redpanda
docker compose up -d

# Terminal 1: Start the producer
python examples/producer.py

# Terminal 2: Start the dashboard
python examples/kafka_demo.py
```

### With Pathway (Stream Processing)

> ⚠️ Requires Python 3.11-3.13 (Pathway depends on pyarrow which doesn't support 3.14 yet)

```bash
# Install Pathway dependencies
pip install stream-viz[pathway]

# Start Redpanda
docker compose up -d

# Terminal 1: Generate fake orders
python examples/ecommerce_producer.py

# Terminal 2: Run Pathway aggregations
python examples/pathway_demo.py
```

## Examples Overview

| File | Description | Requirements |
|------|-------------|--------------|
| `simple_demo.py` | Four animated sine/cosine waves | None |
| `kafka_demo.py` | Consume and visualize Kafka metrics | Docker, `[kafka]` |
| `producer.py` | Generate fake system metrics | Docker, `[kafka]` |
| `pathway_demo.py` | Real-time revenue aggregations | Docker, `[pathway]`, Python <3.14 |
| `ecommerce_producer.py` | Generate fake e-commerce orders | Docker, `[kafka]` |
