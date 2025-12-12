# Deployment Guide

How to deploy PathwayViz in production environments.

## Overview

PathwayViz runs as a single Python process that:

1. Runs your Pathway pipeline
2. Serves the dashboard UI
3. Broadcasts data via WebSocket

For production, you typically:

1. Build a Docker image with your pipeline
2. Deploy to your container platform
3. Connect to your Kafka/data sources
4. Put behind a reverse proxy for TLS

---

## Docker

### Build the Image

```bash
# From the pathway-viz repo
docker build -t pathway-viz .

# Or with specific Python version
docker build --build-arg PYTHON_VERSION=3.11 -t pathway-viz .
```

### Run Your Pipeline

```bash
# Mount your pipeline script
docker run -p 3000:3000 \
  -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
  pathway-viz python my_pipeline.py

# With Kafka on the same Docker network
docker run -p 3000:3000 \
  --network my-network \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
  pathway-viz python my_pipeline.py

# With persistence volume
docker run -p 3000:3000 \
  -v streamviz-data:/app/data \
  -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
  pathway-viz python my_pipeline.py
```

### Custom Dockerfile

For production, create your own Dockerfile:

```dockerfile
FROM pathway-viz:latest

# Copy your pipeline
COPY my_pipeline.py /app/
COPY requirements.txt /app/

# Install additional dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV STREAMVIZ_PORT=3000

CMD ["python", "my_pipeline.py"]
```

---

## Docker Compose

### Development Setup

```yaml
version: "3.8"

services:
  redpanda:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 512M
      - --overprovisioned
      - --kafka-addr PLAINTEXT://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://redpanda:9092
    ports:
      - "9092:9092"
      - "8081:8081" # Schema registry
      - "9644:9644" # Admin API

  streamviz:
    build: .
    ports:
      - "3000:3000"
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
    volumes:
      - ./my_pipeline.py:/app/my_pipeline.py
      - streamviz-data:/app/data
    command: python my_pipeline.py
    depends_on:
      - redpanda
    restart: unless-stopped

volumes:
  streamviz-data:
```

### Production Setup

```yaml
version: "3.8"

services:
  streamviz:
    image: your-registry/streamviz:v1.0.0
    ports:
      - "3000:3000"
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}
      - STREAMVIZ_PORT=3000
    volumes:
      - streamviz-data:/app/data
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:3000/')",
        ]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    restart: always
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  streamviz-data:
```

---

## Kubernetes

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: streamviz
  labels:
    app: streamviz
spec:
  replicas: 1 # StreamViz is stateful, single replica recommended
  selector:
    matchLabels:
      app: streamviz
  template:
    metadata:
      labels:
        app: streamviz
    spec:
      containers:
        - name: streamviz
          image: your-registry/streamviz:v1.0.0
          ports:
            - containerPort: 3000
              name: http
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              valueFrom:
                configMapKeyRef:
                  name: streamviz-config
                  key: kafka_servers
            - name: STREAMVIZ_PORT
              value: "3000"
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 10
          volumeMounts:
            - name: data
              mountPath: /app/data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: streamviz-pvc
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: streamviz
spec:
  selector:
    app: streamviz
  ports:
    - port: 80
      targetPort: 3000
      name: http
  type: ClusterIP
```

### Ingress (with TLS)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: streamviz
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/websocket-services: streamviz
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - dashboard.example.com
      secretName: streamviz-tls
  rules:
    - host: dashboard.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: streamviz
                port:
                  number: 80
```

### PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: streamviz-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: streamviz-config
data:
  kafka_servers: "kafka-0.kafka:9092,kafka-1.kafka:9092"
```

---

## Reverse Proxy

### Nginx

WebSocket support requires specific configuration:

```nginx
upstream streamviz {
    server localhost:3000;
}

server {
    listen 443 ssl http2;
    server_name dashboard.example.com;

    ssl_certificate /etc/letsencrypt/live/dashboard.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.example.com/privkey.pem;

    location / {
        proxy_pass http://streamviz;
        proxy_http_version 1.1;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-lived WebSocket connections
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

### Traefik

```yaml
# docker-compose.yml with Traefik
services:
  traefik:
    image: traefik:v2.10
    command:
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --providers.docker
      - --certificatesresolvers.le.acme.email=admin@example.com
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - letsencrypt:/letsencrypt

  streamviz:
    image: pathway-viz
    labels:
      - traefik.enable=true
      - traefik.http.routers.streamviz.rule=Host(`dashboard.example.com`)
      - traefik.http.routers.streamviz.entrypoints=websecure
      - traefik.http.routers.streamviz.tls.certresolver=le
      - traefik.http.services.streamviz.loadbalancer.server.port=3000
```

---

## Environment Variables

| Variable                  | Default        | Description                             |
| ------------------------- | -------------- | --------------------------------------- |
| `STREAMVIZ_PORT`          | 3000           | Server port                             |
| `STREAMVIZ_DATA_DIR`      | /app/data      | Data directory for persistence          |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 | Kafka connection (use in your pipeline) |

---

## Production Checklist

### Security

- [ ] TLS termination at reverse proxy
- [ ] Network policies restricting access
- [ ] No sensitive data in widget titles/labels
- [ ] Authentication if needed (reverse proxy level)

### Reliability

- [ ] Health checks configured
- [ ] Restart policy set
- [ ] Resource limits defined
- [ ] Persistent volume for state

### Monitoring

- [ ] Container logs collected
- [ ] Health endpoint monitored
- [ ] Alerts for container restarts

### Performance

- [ ] Adequate CPU/memory limits
- [ ] SSD storage for DuckDB
- [ ] Network latency to Kafka minimized

### Backup

- [ ] Persistent volume backed up
- [ ] DuckDB database included in backups
- [ ] Pathway state directory included

---

## Scaling Considerations

StreamViz is designed as a **single-instance** application:

- Pathway runs one pipeline per process
- WebSocket server broadcasts to all connected clients
- State is local (DuckDB, ring buffers)

For high availability:

1. Run in active-passive with shared storage
2. Use Kubernetes PVC with ReadWriteOnce
3. Container orchestrator handles failover

For high throughput:

1. Scale Kafka partitions
2. Increase Pathway worker threads
3. Add CPU/memory to StreamViz container
