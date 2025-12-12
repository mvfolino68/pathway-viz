# Development Guide

## Prerequisites

- **Python 3.11+**
- **Rust** — install via [rustup.rs](https://rustup.rs/)
- **uv** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker** — only needed for Kafka demos

## Setup

```bash
git clone https://github.com/mvfolino68/pathway-viz.git
cd pathway-viz

uv venv && source .venv/bin/activate
uv pip install maturin
maturin develop                # Build Rust extension
uv pip install -e ".[dev]"     # Install dev dependencies
pytest                         # Verify everything works
```

## Project Structure

```text
pathway-viz/
├── src/                        # Rust (PyO3 + Axum WebSocket server)
├── python/pathway_viz/         # Python package
├── frontend/                   # Browser UI (index.html, embed.html)
├── examples/                   # React/Svelte/Next.js integration examples
├── tests/                      # Python tests
├── docs/                       # Documentation
├── pyproject.toml              # Python config — VERSION SOURCE OF TRUTH
├── Cargo.toml                  # Rust config — keep version in sync
└── Dockerfile
```

## Building

```bash
maturin develop              # Fast debug build
maturin develop --release    # Optimized build (for perf testing)
maturin build --release      # Build distributable wheels → target/wheels/
```

After any Rust changes, run `maturin develop` to rebuild.

## Testing & Linting

```bash
pytest                       # Run tests
ruff check . && ruff format . # Lint and format Python
cargo fmt && cargo clippy    # Lint Rust
```

## Releasing a New Version

PathwayViz uses **tag-triggered releases**. Pushing a `v*` tag to GitHub automatically builds and publishes to PyPI.

### Step-by-Step Release

1. **Update version** in both files (keep them in sync):

   - `pyproject.toml`: `version = "X.Y.Z"`
   - `Cargo.toml`: `version = "X.Y.Z"`

2. **Regenerate lock files**:

   ```bash
   uv lock
   cargo check
   ```

3. **Commit, tag, and push**:

   ```bash
   git add -A
   git commit -m "Release vX.Y.Z"
   git tag vX.Y.Z
   git push origin master && git push origin vX.Y.Z
   ```

   The two `git push` commands:

   - `git push origin master` — pushes your commits to the remote branch
   - `git push origin vX.Y.Z` — pushes the tag, which **triggers the PyPI publish workflow**

   Tags and commits are pushed separately because Git doesn't push tags by default.

### What Happens After Tagging

The `pypi-publish.yml` workflow automatically:

1. Builds wheels for Linux, macOS (Intel + ARM), and Windows
2. Publishes to PyPI using trusted publisher (no API token needed)

### Manual Release (if needed)

```bash
maturin build --release
twine upload target/wheels/*  # Requires PyPI API token
```

## Docker

```bash
docker build -t pathway-viz .
docker run -p 3000:3000 pathway-viz pathway-viz demo --mode simple
```

Pushing to `master` or creating a tag triggers `.github/workflows/docker-publish.yml`.

## Common Tasks

| Task                   | Steps                                                          |
| ---------------------- | -------------------------------------------------------------- |
| **Add widget type**    | Edit `_widgets.py` → `index.html` → `__init__.py` → add tests  |
| **Modify Rust server** | Edit `src/` → run `maturin develop`                            |
| **Update frontend**    | Edit `frontend/` → changes apply on browser refresh (dev mode) |

## Troubleshooting

| Problem                             | Solution                                                     |
| ----------------------------------- | ------------------------------------------------------------ |
| Module not found after Rust changes | `maturin develop`                                            |
| Lock file conflicts                 | `uv lock && cargo check`                                     |
| Docker build fails                  | `docker pull python:3.12-slim && docker pull rust:1.83-slim` |

## Resources

- [Maturin](https://www.maturin.rs/) — Build tool for Rust Python extensions
- [PyO3](https://pyo3.rs/) — Rust bindings for Python
- [uv](https://docs.astral.sh/uv/) — Fast Python package manager
- [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) — PyPI OIDC auth
