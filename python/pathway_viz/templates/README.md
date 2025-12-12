# My PathwayViz Dashboard

Real-time streaming dashboard powered by [PathwayViz](https://github.com/mvfolino68/pathway-viz).

## Quick Start

```bash
# Simple demo (no Docker required)
python pipeline.py --mode simple

# With Kafka streaming (requires Docker)
docker compose up -d
python pipeline.py --mode kafka
```

Open http://localhost:3000 to view your dashboard.

## Files

- `pipeline.py` - Your data pipeline (customize this!)
- `docker-compose.yml` - Kafka/Redpanda for streaming
- `README.md` - This file

## Containerization

If you want to deploy your pipeline in Docker:

```bash
# Use the official PathwayViz image as a base
docker run -p 3000:3000 mvfolino68/pathway-viz
```

Or create a custom Dockerfile:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pipeline.py .
RUN pip install pathway-viz[demo]
CMD ["python", "pipeline.py"]
```

## Learn More

- [PathwayViz Documentation](https://github.com/mvfolino68/pathway-viz)
- [Pathway Documentation](https://pathway.com/docs)
