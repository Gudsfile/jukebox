# ADR 0003: UI Framework Migration (FastUI → Svelte SPA)

## Status

Accepted

## Context and Problem Statement

The admin UI (`jukebox/adapters/inbound/admin/ui_controller.py` and `ui_pages/`) is built on [FastUI](https://github.com/pydantic/fastui). FastUI was archived on 2026-06-07 and had received no updates for 11 months prior. The project has also hit several structural limits of the framework as features were added:

- No native DELETE support in the component/event model — worked around with POST (`ui_controller.py:169`)
- Manual `c.Page.model_rebuild()` required for Pydantic v2 compatibility (`ui_controller.py:362`)
- The UI adapter builds `AnyComponent` trees directly from use cases and does **not** go through the existing REST API (`/api/v1/*`, in `api_controller.py` and `admin/api/*_router.py`), duplicating wiring that already exists and is already tested at the API layer

Total UI adapter surface: ~1,769 LOC across `ui_controller.py` (362), `ui_pages/library.py` (381), `ui_pages/settings.py` (525), `ui_pages/sonos.py` (501).

Constraints:
- Target deployment includes Raspberry Pi / embedded hardware — the UI must not add runtime load (persistent per-client websockets, JS build tooling) on that device.
- `uv sync --extra ui` must remain the entire install step on the Pi — no `node`/`npm` on the device.
- A JS build step in the toolchain (run elsewhere, e.g. CI) is acceptable.

## Considered Options

### Option 1: Stay on FastUI

**Rejected**: archived upstream, no fixes for the DELETE/Pydantic workarounds already hit, and the gap only grows as FastAPI/Pydantic move forward.

### Option 2: HTMX + Jinja2 templates

- Pros: no JS build tooling at all, SSE maps directly to `hx-sse`, smallest conceptual diff from current server-rendered-fragment model.
- Cons: tends to reproduce the current anti-pattern — server-rendered fragments built ad hoc from use cases, bypassing `/api/v1` the same way FastUI does today. Doesn't resolve the API/UI duplication.
- **Rejected**: fixes the framework-risk problem but not the architectural duplication problem.

### Option 3: NiceGUI

- Pros: closest feel to FastUI (server drives a component tree), actively maintained.
- Cons: introduces a new single-vendor Python UI framework dependency — same abandonment-risk class as FastUI. Runs a persistent websocket per client, heavier on Pi than a static-file + REST API split.
- **Rejected**: doesn't reduce framework risk, adds runtime weight on target hardware.

### Option 4: Separate SPA consuming `/api/v1` (React or Svelte)

- Pros: forces `/api/v1` to become the single source of truth for the UI, eliminating the current duplication. Standard REST + standard frontend ecosystem — no proprietary component DSL to be orphaned again. Build step runs in CI, not on the Pi; the Pi only ever serves a static bundle + the existing FastAPI process.
- Cons: most rework — full rewrite of all pages as SPA components, plus one new endpoint to add (SSE tag banner, currently only under `/api/ui`, must move to `/api/v1`).
- **Framework pick — Svelte over React**: smaller compiled bundle (no shipped runtime/virtual DOM), simpler syntax, good fit for a small, solo-maintained admin panel. React's larger ecosystem was weighed but not decisive here — this is not a hiring-at-scale concern.

## Decision Outcome

Adopt **Option 4: a Svelte SPA consuming `/api/v1`**.

- The SPA is built in CI (`npm run build`), and the compiled static bundle is packaged as an asset inside the `gukebox` Python package.
- FastAPI serves the static bundle (via Starlette's `StaticFiles`, already a transitive dependency — no new package needed for this) alongside the existing `/api/v1` routes.
- `uv sync --extra ui` remains the full install step on the Pi; no `node`/`npm` on the device.
- The `ui` extra in `pyproject.toml` drops `fastui` and `python-multipart`; it becomes effectively an alias for `api` (static files need nothing beyond FastAPI/Starlette).
- The SSE endpoint for the live tag banner (`/api/ui/current-tag-banner/events`) moves under `/api/v1` so the SPA can subscribe to it like any other API resource.

## More information

Migration scope, for follow-up planning:
- Add SSE endpoint to `/api/v1` (currently only exists under `/api/ui`, tied to FastUI's `ServerLoad`).
- Confirm `/api/v1` already covers all CRUD/settings/Sonos operations the current `ui_pages/*` implement (initial scan: discs, settings, current-tag, and Sonos routers already exist — SSE is the one known gap).
- Remove `jukebox/adapters/inbound/admin/ui_controller.py` and `ui_pages/` once the SPA replaces them; remove associated tests.
- New Svelte project lives outside the `jukebox` Python package tree (e.g. a top-level `ui/` or `frontend/` directory), with its CI build output copied into the package's static assets at release time.
