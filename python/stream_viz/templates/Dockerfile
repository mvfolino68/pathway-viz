# StreamViz Pipeline
#
# Build:  docker build -t my-streamviz .
# Run:    docker run -p 3000:3000 my-streamviz
#
# Or use the pre-built image:
#   docker pull mvfolino68/stream-viz:latest

FROM python:3.12-slim

WORKDIR /app

# Install stream-viz with all optional dependencies
RUN pip install --no-cache-dir "stream-viz[all]"

# Copy your pipeline
COPY pipeline.py .

# Create data directory for persistence
RUN mkdir -p /app/data

ENV STREAMVIZ_PORT=3000
ENV STREAMVIZ_DATA_DIR=/app/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/')" || exit 1

CMD ["python", "pipeline.py"]
