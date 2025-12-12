# Contributing to PathwayViz

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Rust (install via [rustup](https://rustup.rs/))
- Docker (for Kafka/Redpanda demos)

### Setup

```bash
# Clone the repo
git clone https://github.com/mvfolino68/pathway-viz.git
cd pathway-viz

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # fish: source .venv/bin/activate.fish

# Install Rust if needed
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build the Rust extension
pip install maturin
maturin develop

# Install dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-format
ruff format .
```

## Project Structure

```text
stream_viz/
├── src/                    # Rust code (PyO3 + Axum)
│   ├── lib.rs             # Python module bindings
│   ├── server.rs          # WebSocket server
│   ├── state.rs           # Global state management
│   └── generator.rs       # Demo data generator
├── python/stream_viz/     # Python code (module name stays stream_viz)
│   └── __init__.py        # High-level API
├── frontend/              # Browser frontend
│   └── index.html         # Dashboard UI
└── examples/              # Demo scripts
```

## Making Changes

### Rust Changes

After modifying Rust code, rebuild with:

```bash
maturin develop
```

For faster iteration during development:

```bash
maturin develop --release  # Optimized build
```

### Python Changes

Python changes take effect immediately (no rebuild needed).

### Frontend Changes

The frontend is served from `frontend/index.html`. Changes take effect on browser refresh.

## Pull Request Guidelines

1. **Fork & Branch**: Create a feature branch from `main`
2. **Test**: Ensure all tests pass
3. **Lint**: Run `ruff check .` and fix any issues
4. **Commit**: Write clear commit messages
5. **PR**: Open a pull request with a description of changes

## Reporting Issues

When reporting issues, please include:

- Python version (`python --version`)
- Rust version (`rustc --version`)
- OS and version
- Steps to reproduce
- Expected vs actual behavior

## Questions?

Feel free to open an issue for discussion!
