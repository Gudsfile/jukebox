# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

**Jukebox** is an NFC-based music player system. It uses NFC tags to trigger playback on speakers. The repo contains three modules:

- **jukebox** — Main music player app (reads NFC tags, controls playback)
- **discstore** — Library management tool (manages the tag → music URI mapping)
- **pn532** — NFC reader library (excluded from linting/type-checking)

## Commands

```bash
# Install dependencies
uv sync                   # base installation (always safe)

# Install optional extras (EXPLICIT ONLY — do not guess)
uv sync --extra nfc       # enable NFC tag reading in jukebox (requires compatible hardware)
uv sync --extra api       # enable REST API for discstore
uv sync --extra ui        # enable Web UI for discstore

# NEVER use:
# uv sync --all-extras
# Reason: extras are environment-dependent (Python version, OS, hardware like NFC reader).
# Installing all extras may fail or introduce unnecessary dependencies.

# Rule for agents:
# - Only install extras if explicitly required by the task.
# - Do not assume availability of NFC hardware.
# - Prefer minimal installation.

# Run
uv run jukebox PLAYER READER
uv run discstore --help
uv run --extra api discstore api     # REST API server
uv run --extra ui discstore ui       # Web UI

# Format, lint, test, typecheck
uv run ruff format          # auto-format code
uv run ruff format --check  # check formatting
uv run ruff check           # lint code
uv run ruff check --fix     # auto-fix lint issues
uv run pytest               # run all tests
uv run ty check             # run type checker

# Run a single test
uv run pytest tests/path/to/test_file.py::test_function_name
uv run pytest -k "test_pattern"

# Run tests including those needing specific extra
uv run --extra ui pytest
```

## Architecture

Both `jukebox` and `discstore` follow **Hexagonal Architecture** (Ports & Adapters):

```
<module>/
├── domain/
│   ├── entities/        # Pydantic value objects
│   ├── repositories/    # Abstract port interfaces
│   └── use_cases/       # Business logic (no external deps)
├── adapters/
│   ├── inbound/         # CLI, API, UI controllers
│   └── outbound/        # Players, readers, JSON persistence
└── di_container.py      # Wires all dependencies
```

### Key Domain Concepts

**Jukebox:**
See `jukebox/domain/entities/` for data models and `jukebox/domain/use_cases/` for business logic.
The state machine lives in `DetermineAction` and `HandleTagEvent`.

- `Disc` — music item with URI, metadata (artist, album, etc.), and playback options (shuffle, is_test)
- `Library` — collection of `Disc` associated with a `tag_id`

**Discstore:**
See `discstore/domain/entities/` for data models and `discstore/domain/use_cases/` for business logic.

### Dependency Injection

All components are wired in `di_container.py`. There is no global state — dependencies flow through constructors. Entry points call `build_*()` functions that instantiate the full object graph.

### Configuration

Pydantic-based config with union types + discriminators for plugin-style player/reader selection. Config can come from CLI args or environment variables. See `adapters/inbound/config.py`.

### Persistence

The library is stored as `library.json` via `json_library_adapter.py`. No database.

## Code Style Guidelines

### Type Annotations

- Use type hints for function parameters and return types
- Use `Optional[X]` over `X | None` for Python 3.9 compatibility

## Testing Patterns

- Tests mirror source structure under `tests/`
- Use `pytest` and `pytest-mock`; mock repositories via `MockRepo` (not the real JSON adapter)
- Conditional skip for Python version requirements (UI tests require 3.10+)
