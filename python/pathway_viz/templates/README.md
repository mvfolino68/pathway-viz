# My PathwayViz Dashboard

Real-time streaming dashboard powered by [PathwayViz](https://github.com/mvfolino68/pathway-viz).

## Quick Start

```bash
# Simple demo (no Docker)
python pipeline.py --mode simple

# With Kafka (requires Docker)
docker compose up -d
python pipeline.py --mode kafka
```

Open http://localhost:3000 to view your dashboard.

## Files

- `pipeline.py` - Your data pipeline
- `docker-compose.yml` - Kafka/Redpanda for streaming
- `Dockerfile` - For containerizing your app

## Learn More

- [PathwayViz Documentation](https://github.com/mvfolino68/pathway-viz)
- [Pathway Documentation](https://pathway.com/docs)
