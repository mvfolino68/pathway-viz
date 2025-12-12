# PathwayViz Pipeline
#
# Build:  docker build -t my-pathway-viz .
# Run:    docker run -p 3000:3000 my-pathway-viz
#
# Or use the pre-built image:
#   docker pull mvfolino68/pathway-viz:latest

FROM python:3.12-slim

WORKDIR /app

# Install pathway-viz with all optional dependencies
RUN pip install --no-cache-dir "pathway-viz[all]"

# Copy your pipeline
COPY pipeline.py .

# Create data directory for persistence
RUN mkdir -p /app/data

ENV PATHWAYVIZ_PORT=3000
ENV PATHWAYVIZ_DATA_DIR=/app/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/')" || exit 1

CMD ["python", "pipeline.py"]
