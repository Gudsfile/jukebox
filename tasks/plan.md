# Implementation Plan: UI Migration — FastUI → Svelte SPA

## Overview

Replace the FastUI-based admin UI (`jukebox/adapters/inbound/admin/ui_controller.py`, `ui_pages/`) with a Svelte single-page app that consumes the existing `/api/v1` REST API. Rationale and options considered: `docs/adr/0003-ui-framework-migration.md`.

## Architecture Decisions

- New Svelte project lives in a new top-level `admin-ui/` directory, outside the `jukebox` Python package.
- CI builds `admin-ui/` and copies the compiled bundle into `jukebox/adapters/inbound/admin/static/` before packaging — the Python package ships pre-built assets, never source JS.
- FastAPI serves that static directory via Starlette's `StaticFiles` (no new dependency).
- `ui` extra in `pyproject.toml` drops `fastui` and `python-multipart`.
- Old and new UI coexist until every page has a Svelte equivalent at parity (per-slice cutover, not a big-bang switch), then the FastUI code is deleted in one final task.

## Task List

### Phase 0: Foundation

- [x] Task 1: Scaffold Svelte project
- [x] Task 2: Static asset serving in FastAPI

### Checkpoint: Foundation
- [x] `admin-ui/` builds (`npm run build`) and produces a `dist/` bundle
- [x] `uv run --extra ui jukebox-admin ui` serves the built Svelte shell at `/ui/` without touching FastUI routes (mounted at `/ui`, not `/` — `/` stays reserved for FastUI's catch-all until Task 9)
- [x] Review with human before proceeding — confirmed working manually

### Phase 1: API gap closure

- [x] Task 3: Move current-tag SSE endpoint to `/api/v1`

### Checkpoint: API gap closure
- [x] All four resources (discs, settings, sonos, current-tag incl. SSE) are reachable under `/api/v1` with test coverage
- [x] Existing FastUI pages still work unchanged (no regression)

### Phase 2: Feature slices (Svelte pages, one per existing FastUI page)

Reprioritized 2026-09-02 per user request: finish the Library workstream (banner, then UI parity gaps vs. FastUI — e.g. missing "type"/"title" columns, details pending) before moving on to Sonos.

- [x] Task 4: Library/discs page — list, create, edit, delete
- [x] Task 5: Settings page — list, edit, reset
- [x] Task 7: Current-tag banner — SSE-driven live indicator (moved up, do before Task 6)
- [x] Task 7b: Library UI parity fixes — Type/Title columns, shuffle ✓/×, button styling
- [x] Task 6: Sonos page — group selection, discovery, reset

### Checkpoint: Feature parity
- [x] Every FastUI page has a working Svelte equivalent, manually verified against a running backend
- [x] No functionality regression vs. the FastUI version (side-by-side check) — one known limitation flagged (Sonos discovery-failure fallback, see Task 6 notes in `tasks/todo.md`)

### Phase 3: Cutover

- [x] Task 8: Wire CI to build and package the Svelte bundle
- [ ] Task 9: Remove FastUI — delete `ui_controller.py`, `ui_pages/`, associated tests, `fastui`/`python-multipart` from `pyproject.toml`

### Checkpoint: Complete
- [ ] `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`, `uv run ty check` all pass
- [ ] `uv sync --extra ui` installs cleanly with no `fastui` in the resolved set
- [ ] Manual smoke test of every page against a real (or dryrun) player/reader
- [ ] `docs/adr/0003-ui-framework-migration.md` status still accurate; update if reality diverged during implementation

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `/api/v1` has gaps beyond the known SSE one, discovered mid-slice | Medium | Each Phase 2 task starts by diffing the target FastUI page's calls against `/api/v1` before writing Svelte code (see task descriptions) |
| CI packaging step (copying `admin-ui/dist` into the Python package) breaks the `uv_build` module layout | Medium | Task 8 is isolated and verified with a real `uv build` + `uv sync --extra ui` before Task 9 deletes the fallback (FastUI) |
| Scope creep: redesigning pages instead of porting them | Low | Phase 2 tasks are explicitly "port to parity", not redesign — visual/UX changes are a separate follow-up, not part of this migration |

## Open Questions

- Auth/access control for the admin UI: out of scope for this migration (assumed unchanged — whatever the current setup is, carried over as-is). Flag if this assumption is wrong.
- Exact static directory path and StaticFiles mount point (`/`, `/admin`, etc.) — proposed in Task 2, confirm during implementation.
