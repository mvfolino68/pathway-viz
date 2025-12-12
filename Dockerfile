# PathwayViz Production Docker Image
#
# ==============================================================================
# BUILD
# ==============================================================================
#
#   # Build the image
#   docker build -t pathway-viz .
#
#   # Build with specific Python version
#   docker build --build-arg PYTHON_VERSION=3.11 -t pathway-viz .
#
# ==============================================================================
# RUN - DEMO MODE
# ==============================================================================
#
#   # Run the demo (requires Kafka on host or docker network)
#   docker run -p 3000:3000 -p 3001:3001 --network host pathway-viz
#
# ==============================================================================
# RUN - PRODUCTION (Your own pipeline)
# ==============================================================================
#
#   # Mount your pipeline script
#   docker run -p 3000:3000 \
#     -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
#     pathway-viz python my_pipeline.py
#
#   # With environment variables for Kafka
#   docker run -p 3000:3000 \
#     -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
#     -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
#     pathway-viz python my_pipeline.py
#
#   # With DuckDB persistence (mount a volume)
#   docker run -p 3000:3000 \
#     -v pathwayviz-data:/app/data \
#     -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
#     pathway-viz python my_pipeline.py
#
# ==============================================================================

ARG PYTHON_VERSION=3.12

# Stage 1: Build the Rust extension
FROM rust:1.83-slim AS builder

WORKDIR /app

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install maturin
RUN pip3 install maturin --break-system-packages

# Copy source code
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY python ./python
COPY frontend ./frontend
COPY pyproject.toml README.md ./

# Build the wheel
RUN maturin build --release

# Stage 2: Runtime image
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy the wheel from builder
COPY --from=builder /app/target/wheels/*.whl ./

# Install the package with all optional dependencies
RUN pip install --no-cache-dir *.whl && rm -f *.whl

# Copy examples for reference
COPY examples ./examples

# Create data directory for persistence
RUN mkdir -p /app/data

# Environment variables
ENV PATHWAYVIZ_PORT=3000
ENV PATHWAYVIZ_DATA_DIR=/app/data

# Expose the default port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PATHWAYVIZ_PORT}/')" || exit 1

# Default: print usage
CMD ["python", "-c", "print('PathwayViz container ready.\\n\\nUsage:\\n  Mount your pipeline: -v ./my_pipeline.py:/app/my_pipeline.py\\n  Run it: python my_pipeline.py\\n\\nOr run the demo with --network host')"]
