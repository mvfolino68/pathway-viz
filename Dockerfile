# PathwayViz Production Docker Image
#
# Installs pathway-viz from PyPI (no build required).
#
# ==============================================================================
# RUN - DEMO MODE
# ==============================================================================
#
#   docker run -p 3000:3000 -p 3001:3001 --network host pathway-viz pathway-viz demo
#
# ==============================================================================
# RUN - PRODUCTION (Your own pipeline)
# ==============================================================================
#
#   docker run -p 3000:3000 \
#     -v $(pwd)/my_pipeline.py:/app/my_pipeline.py \
#     pathway-viz python my_pipeline.py
#
# ==============================================================================

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install pathway-viz from PyPI with all optional dependencies
RUN pip install --no-cache-dir 'pathway-viz[all]'

# Environment variables
ENV PATHWAYVIZ_PORT=3000

# Expose the default port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PATHWAYVIZ_PORT}/')" || exit 1

# Default: print usage
CMD ["python", "-c", "print('PathwayViz container ready.\\n\\nUsage:\\n  Mount your pipeline: -v ./my_pipeline.py:/app/my_pipeline.py\\n  Run it: python my_pipeline.py\\n\\nOr run the demo with --network host')"]
