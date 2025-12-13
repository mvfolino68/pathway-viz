# Deployment

PathwayViz runs as a single Python process—pipeline, dashboard, and WebSocket server together.

## Docker

Create your pipeline (`pipeline.py`). This file is your application code; the container image provides the PathwayViz server and UI.

Then run:

```bash
docker run -p 3000:3000 \
  -v $(pwd)/pipeline.py:/app/pipeline.py \
  -v dashboard-data:/app/data \
  mvfolino68/pathway-viz python pipeline.py
```

`dashboard-data` is a named Docker volume mounted at `/app/data`.

## Docker Compose

For Kafka streaming:

```yaml
services:
  kafka:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 512M
      - --kafka-addr PLAINTEXT://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://kafka:9092
    ports:
      - "9092:9092"

  dashboard:
    image: mvfolino68/pathway-viz:latest
    ports:
      - "3000:3000"
    volumes:
      - ./pipeline.py:/app/pipeline.py
      - dashboard-data:/app/data
    command: python pipeline.py
    depends_on:
      - kafka

volumes:
  dashboard-data:
```

```bash
docker compose up
```

## Production Image

Bake your pipeline into the image:

```dockerfile
FROM mvfolino68/pathway-viz:latest
COPY pipeline.py /app/
CMD ["python", "pipeline.py"]
```

## Reverse Proxy (WebSocket)

PathwayViz uses WebSockets. Your proxy needs to support connection upgrades.

**Nginx:**

```nginx
location / {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
```

## Environment Variables

| Variable          | Default | Description |
| ----------------- | ------- | ----------- |
| `PATHWAYVIZ_PORT` | 3000    | Server port |
