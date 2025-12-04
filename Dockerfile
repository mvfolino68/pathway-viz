# StreamViz Docker Image
#
# Build:
#   docker build -t stream-viz .
#
# Run demo:
#   docker run -p 3000:3000 stream-viz
#
# Run with Kafka (use host network to connect to localhost:9092):
#   docker run --network host stream-viz python examples/kafka_demo.py

# Stage 1: Build the Rust extension
FROM rust:1.75-slim as builder

WORKDIR /app

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install maturin
RUN pip3 install maturin --break-system-packages

# Copy source code
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY python ./python
COPY pyproject.toml ./

# Build the wheel
RUN maturin build --release

# Stage 2: Runtime image
FROM python:3.12-slim

WORKDIR /app

# Copy the wheel from builder
COPY --from=builder /app/target/wheels/*.whl ./

# Copy frontend and examples
COPY frontend ./frontend
COPY examples ./examples
COPY demo.py ./

# Install the package with kafka support
RUN pip install --no-cache-dir *.whl kafka-python-ng

# Expose the default port
EXPOSE 3000

# Default: run the demo
CMD ["python", "demo.py"]
