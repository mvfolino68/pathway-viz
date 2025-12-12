# Development Guide

This guide covers how to set up, build, test, and release PathwayViz.

## Prerequisites

- **Python 3.11+**
- **Rust** (install via [rustup](https://rustup.rs/))
- **uv** (recommended) or pip
- **Docker** (for demos with Kafka)

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install uv (recommended Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

```bash
# Clone and enter the repo
git clone https://github.com/mvfolino68/pathway-viz.git
cd pathway-viz

# Create virtual environment
uv venv
source .venv/bin/activate  # fish: source .venv/bin/activate.fish

# Build the Rust extension and install in dev mode
uv pip install maturin
maturin develop

# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
```

## Project Structure

```text
pathway-viz/
├── src/                        # Rust code (PyO3 + Axum WebSocket server)
│   ├── lib.rs                  # Python module bindings
│   ├── server.rs               # WebSocket server
│   ├── state.rs                # Ring buffer state management
│   └── generator.rs            # Demo data generator
├── python/pathway_viz/         # Python package
│   ├── __init__.py             # Public API
│   ├── _widgets.py             # Widget implementations
│   ├── _server.py              # Server control
│   ├── _config.py              # Dashboard configuration
│   ├── _state.py               # Global state
│   ├── demos/                  # Built-in demos
│   └── templates/              # Project scaffolding templates
├── frontend/                   # Browser frontend (embedded in Rust binary)
│   ├── index.html              # Main dashboard
│   └── embed.html              # Widget gallery
├── examples/                   # Framework integration examples
├── tests/                      # Python tests
├── docs/                       # Documentation
├── pyproject.toml              # Python package config (VERSION SOURCE OF TRUTH)
├── Cargo.toml                  # Rust crate config
└── Dockerfile                  # Production container
```

## Building

### Development Build (Fast)

```bash
maturin develop
```

This compiles the Rust extension in debug mode and installs it in your virtual environment.

### Release Build (Optimized)

```bash
maturin develop --release
```

Use this for performance testing.

### Build Wheels

```bash
maturin build --release
```

Wheels are output to `target/wheels/`.

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_basic.py::test_version
```

## Code Style

We use [ruff](https://github.com/astral-sh/ruff) for Python linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

For Rust:

```bash
cargo fmt
cargo clippy
```

## Version Management

### Single Source of Truth

The **canonical version** is in `pyproject.toml`:

```toml
[project]
version = "0.1.0"
```

- **Python**: Reads version from package metadata via `importlib.metadata`
- **Rust**: Keep `Cargo.toml` version in sync manually (or use a release script)
- **Git tags**: Must match the version (e.g., `v0.1.0`)

### Updating Version

When releasing a new version:

1. Update `pyproject.toml`:

   ```toml
   version = "0.2.0"
   ```

2. Update `Cargo.toml`:

   ```toml
   version = "0.2.0"
   ```

3. Regenerate lock files:

   ```bash
   uv lock
   cargo check
   ```

4. Commit and tag:
   ```bash
   git add -A
   git commit -m "Release v0.2.0"
   git tag v0.2.0
   git push origin main
   git push origin v0.2.0
   ```

## Releasing to PyPI

### Automated (Recommended)

Push a version tag to trigger the GitHub Actions workflow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `pypi-publish.yml` workflow will:

1. Build wheels for Linux (manylinux), macOS (x86_64 + ARM), and Windows
2. Build source distribution
3. Publish to PyPI using trusted publisher (OIDC)

### Manual (If Needed)

```bash
# Build wheels
maturin build --release

# Upload to PyPI (requires API token)
twine upload target/wheels/*
```

## Docker

### Build Image

```bash
docker build -t pathway-viz .
```

### Run Demo

```bash
docker run -p 3000:3000 pathway-viz python -m pathway_viz --mode simple
```

### Publish to Docker Hub

Push to `main` or create a tag to trigger `.github/workflows/docker-publish.yml`.

## Common Tasks

### Adding a New Widget Type

1. Add widget class in `python/pathway_viz/_widgets.py`
2. Add frontend rendering in `frontend/index.html`
3. Export from `python/pathway_viz/__init__.py`
4. Add tests in `tests/`
5. Document in `docs/widgets.md`

### Modifying the Rust Server

1. Edit files in `src/`
2. Rebuild: `maturin develop`
3. Test your changes

### Updating Frontend

The frontend is embedded in the Rust binary. After editing `frontend/`:

1. The Rust server serves files from disk in dev mode
2. For production, files are embedded at compile time

## Troubleshooting

### "Module not found" after Rust changes

Rebuild the extension:

```bash
maturin develop
```

### Lock file conflicts

Regenerate lock files:

```bash
uv lock
cargo check
```

### Docker build fails

Ensure you have the latest base images:

```bash
docker pull python:3.12-slim
docker pull rust:1.83-slim
```

## CI/CD Workflows

| Workflow             | Trigger                 | Purpose                       |
| -------------------- | ----------------------- | ----------------------------- |
| `pypi-publish.yml`   | `v*` tags               | Build wheels, publish to PyPI |
| `docker-publish.yml` | Push to main, `v*` tags | Build and push Docker image   |

## Resources

- [Maturin Documentation](https://www.maturin.rs/)
- [PyO3 User Guide](https://pyo3.rs/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Trusted Publishers (PyPI)](https://docs.pypi.org/trusted-publishers/)
