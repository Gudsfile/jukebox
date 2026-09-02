# Todo: UI Migration — FastUI → Svelte SPA

See `tasks/plan.md` for overview and `docs/adr/0003-ui-framework-migration.md` for rationale.

## Phase 0: Foundation

### Task 1: Scaffold Svelte project ✅

**Description:** Create a new `admin-ui/` directory (SvelteKit in static-adapter/SPA mode, or plain Svelte + Vite — pick whichever needs less config for a pure static export) with routing skeleton for the four pages (library, settings, sonos, current-tag banner as a persistent shell element) and a thin API client module wrapping `fetch` against `/api/v1`.

Went with plain Svelte + Vite (not SvelteKit) — pure static export, no adapter config needed.

**Acceptance criteria:**
- [x] `admin-ui/` exists with a working dev server (`npm run dev`)
- [x] `npm run build` emits a static bundle (`admin-ui/dist/` or equivalent) with no server-side runtime required
- [x] Empty placeholder routes/components exist for library, settings, sonos pages

**Verification:**
- [x] `npm run build` succeeds with no errors
- [x] Manual check: dev server loads a blank shell in the browser

**Dependencies:** None

**Files likely touched:**
- `admin-ui/package.json`, `admin-ui/vite.config.*`, `admin-ui/svelte.config.*`
- `admin-ui/src/routes/*` or `admin-ui/src/lib/pages/*`
- `admin-ui/src/lib/api.ts`

**Estimated scope:** Medium: 3-5 files (plus generated scaffold)

---

### Task 2: Static asset serving in FastAPI ✅

**Description:** Mount the built `admin-ui` bundle as static files in the FastAPI app (`jukebox/admin/app.py` or wherever the app is assembled), served alongside `/api/v1`, without removing or touching the existing FastUI routes yet.

Mounted at `/ui` (not `/`) in `APIController.register_routes` (shared base class) — `/` stays reserved for FastUI's catch-all until cutover (Task 9).

**Acceptance criteria:**
- [x] FastAPI serves the Svelte shell at `/` (or an agreed mount point) via `StaticFiles`
- [x] `/api/v1/*` and `/api/ui/*` (FastUI) continue to work unchanged
- [x] `jukebox-admin ui` command still starts the existing FastUI app as-is; new static mount is additive, not a replacement, at this stage

**Verification:**
- [x] `uv run pytest` — no regressions
- [x] Manual check: hit `/` in a browser after a local `npm run build`, see the Svelte placeholder shell

**Dependencies:** Task 1

**Files likely touched:**
- `jukebox/admin/app.py` (or equivalent app assembly point)
- `jukebox/adapters/inbound/admin/` (new static-mount wiring, exact file TBD during implementation)

**Estimated scope:** Small: 1-2 files

---

## Phase 1: API gap closure

### Task 3: Move current-tag SSE endpoint to `/api/v1` ✅

**Description:** Port `/api/ui/current-tag-banner/events` (`ui_controller.py:78`) to a new SSE endpoint under `/api/v1` (e.g. `/api/v1/current-tag/events`), reusing the existing `current_tag_router.py` and the domain logic it already calls. The old FastUI endpoint stays untouched until Task 9.

Emits plain `CurrentTagStatusOutput` JSON (or `null`) instead of FastUI component trees — API stays UI-framework-agnostic, matching the ADR's "single source of truth" rationale.

**Acceptance criteria:**
- [x] New SSE endpoint exists under `/api/v1`, streams the same events as the FastUI one
- [x] Endpoint has test coverage (mirroring existing `current_tag_router.py` test patterns)
- [x] `/api/ui/current-tag-banner/events` still works unchanged (no shared-state regression)

**Verification:**
- [x] `uv run pytest tests/jukebox/adapters/inbound/admin/api/test_current_tag_router.py` passes
- [x] `uv run ruff check` clean
- [x] Manual check: `curl -N http://localhost:PORT/api/v1/current-tag/events` streams events on tag scan

**Dependencies:** None (independent of Phase 0)

**Files likely touched:**
- `jukebox/adapters/inbound/admin/api/current_tag_router.py`
- `tests/adapters/inbound/admin/api/test_current_tag_router.py`

**Estimated scope:** Small: 1-2 files

---

## Phase 2: Feature slices

Each task below starts by diffing the target FastUI page's use-case calls (`ui_pages/*.py`) against the corresponding `/api/v1` router to confirm no other gaps exist beyond what's already known — treat any newly found gap as a blocking sub-task, same shape as Task 3.

**Reprioritized 2026-09-02:** do Task 7 (banner) next, then Task 7b (Library UI parity fixes), then Task 6 (Sonos).

### Task 4: Library/discs page — list, create, edit, delete ✅

**Description:** Build the Svelte page mirroring `ui_pages/library.py`: disc list, create form, edit form, delete confirmation — all calling `/api/v1` disc endpoints (`discs_router.py`).

No API gaps found — `discs_router.py` already covered full CRUD. Added `apiPatch` to `api.js` (discs use PATCH, not PUT).

**Acceptance criteria:**
- [x] List, create, edit, delete all work end-to-end against a running backend
- [x] Delete uses a real HTTP DELETE (fixing the FastUI POST-only workaround at `ui_controller.py:169`)
- [x] Form validation errors from the API surface in the UI (`error = err.body?.detail ?? err.message` in `DiscForm.svelte`)

**Verification:**
- [x] Manual check: full CRUD cycle on a disc via `/api/v1` (create → patch → delete), verified against the real `library.json`, no residue left
- [x] `npm run build` still succeeds

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `admin-ui/src/lib/pages/Library.svelte` (+ subcomponents for form/list)
- `admin-ui/src/lib/api.ts` (disc client methods)

**Estimated scope:** Medium: 3-5 files

---

### Task 5: Settings page — list, edit, reset ✅

**Description:** Build the Svelte page mirroring `ui_pages/settings.py`: settings list, edit form (input/select/textarea field types), reset action — calling `/api/v1` settings endpoints (`settings_router.py`).

**Gap found and closed:** `EditableSettingDisplay` (labels, sections, choices, provenance, badges) was pure Python domain logic in `jukebox/settings/definitions.py`, never exposed via `/api/v1` — only raw JSON trees were. Added `GET /api/v1/settings/displays` wrapping `build_editable_setting_displays()`, with the same graceful-degradation-on-`SettingsError` behavior as the FastUI page.

**Acceptance criteria:**
- [x] List, edit, reset all work end-to-end against a running backend
- [x] Field types (text/select/textarea) render correctly per setting type

**Verification:**
- [x] Manual check: edit and reset a setting via a scratch library file — `admin.api.port` 8000 → patch 9999 (persisted) → reset → back to 8000 (default), confirmed via `/api/v1/settings/displays`
- [x] `npm run build` still succeeds

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `admin-ui/src/lib/pages/Settings.svelte` (+ subcomponents)
- `admin-ui/src/lib/api.ts` (settings client methods)

**Estimated scope:** Medium: 3-5 files

---

### Task 6: Sonos page — group selection, discovery, reset ✅

**Description:** Build the Svelte page mirroring `ui_pages/sonos.py`: speaker/group selection, discovery trigger, reset — calling `/api/v1/sonos/*`.

No new API gaps — `GET /sonos/speakers`, `GET /sonos/selection`, `PUT /sonos/selection` already covered discovery/status/save. Reset reuses Task 5's generic `POST /settings/reset {path: "jukebox.player.sonos.selected_group"}` — no dedicated Sonos reset endpoint needed.

**Known limitation (not fixed, flagging per no-silent-caps):** `GET /api/v1/sonos/selection` is all-or-nothing — on total discovery failure it 502s with no data at all, whereas FastUI's page builder read the persisted `selected_group` directly (no discovery needed) and showed it raw even when discovery failed. Fixing this would mean changing `GetSonosSelectionStatus`'s error handling, which is broader than a simple missing-endpoint gap — left as-is for this migration.

**Acceptance criteria:**
- [x] Discovery, selection, and reset all work end-to-end against a running backend (or dryrun player)
- [x] Error states (e.g. discovery failure) surface in the UI

**Verification:**
- [x] Manual check: `GET /api/v1/sonos/selection` and `/sonos/speakers` against real Sonos hardware on the network — correct partial-availability status, coordinator/member labels resolved
- [x] `npm run build` still succeeds
- [x] `uv run pytest` — no backend changes needed, 763 passed unaffected

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `admin-ui/src/lib/pages/Sonos.svelte` (+ subcomponents)
- `admin-ui/src/lib/api.ts` (sonos client methods)

**Estimated scope:** Medium: 3-5 files

---

### Task 7: Current-tag banner — SSE-driven live indicator ✅

**Description:** Build a persistent shell component subscribing to the `/api/v1` SSE endpoint from Task 3, showing the live "current tag" banner across all pages (mirroring the FastUI `ServerLoad` banner in `ui_controller.py`).

Used the browser's native `EventSource` — it reconnects automatically on connection drop, no custom retry logic needed (FastUI's version had to poll manually since it wasn't using real SSE client API). Also wired "Edit this disc" / "Add this disc" banner buttons to jump to the Library page with the tag pre-filled (`libraryIntent` state lifted to `App.svelte`), matching FastUI parity.

**Acceptance criteria:**
- [x] Banner updates live on tag scan/removal without a page reload
- [x] Reconnects gracefully if the SSE connection drops (native `EventSource` behavior)

**Verification:**
- [x] Manual check: wrote directly to the current-tag sidecar file while an SSE connection was open — stream emitted `null` then the new tag payload live
- [x] `npm run build` still succeeds

**Dependencies:** Task 1, Task 2, Task 3

**Files likely touched:**
- `admin-ui/src/lib/components/CurrentTagBanner.svelte`
- `admin-ui/src/lib/api.ts` (SSE client helper)

**Estimated scope:** Small: 1-2 files

---

### Task 7b: Library UI parity fixes ✅

**Description:** Close visual/data gaps between the Svelte Library page and the old FastUI one: missing "Type"/"Title" columns (replacing separate Artist/Album/Track/Playlist columns), plain "yes"/"no" shuffle text, unstyled buttons.

**Gap found and closed:** `DiscMetadata.display_type`/`display_title` (`jukebox/domain/entities/disc.py`) are pure domain `@property`s — Pydantic doesn't serialize plain properties, so they never reached `/api/v1`. Added `@computed_field` versions on `DiscOutput` (`api/models.py`) delegating to the domain properties — no duplicated logic, matches ADR's single-source-of-truth rationale (same pattern as Task 5's settings-displays gap).

**Acceptance criteria:**
- [x] Library table shows "Type" (🎵/💿/🎧/🎤 + label) and "Title" columns instead of Artist/Album/Track/Playlist
- [x] Shuffle column shows ✓/× instead of yes/no
- [x] Edit/Delete buttons restyled (solid buttons, Delete in red, horizontal layout)

**Verification:**
- [x] `uv run pytest` — 763 passed (3 pre-existing tests updated for the new computed fields, 2 new tests added for `DiscOutput` serialization)
- [x] Manual check: `GET /api/v1/discs` against real `library.json` confirms `display_type`/`display_title` match FastUI's output exactly (e.g. "💿 Album" / "Veridis Project — Voir le soleil")
- [x] `npm run build` still succeeds

**Dependencies:** Task 4, Task 7

---

## Phase 3: Cutover

### Task 8: Wire CI to build and package the Svelte bundle ✅

**Description:** Add a build step to `.github/workflows/python.yml` (or a new workflow) that runs `npm run build` in `admin-ui/` and copies the output into the location the `uv_build` module layout expects (see `pyproject.toml`'s `[tool.uv.build-backend]`), so `uv build`/`uv sync --extra ui` ship the compiled bundle without requiring `node` at install time.

Confirmed `uv_build` already packages non-`.py` files under a module directory by default — no `[tool.uv.build-backend]` config change needed, just get the built bundle into `jukebox/adapters/inbound/admin/static/` before `uv build` runs. Added the same Node setup → `npm ci` → `npm run build` → copy steps to **both** `python.yml`'s `build` job (PR/push builds) **and** `release.yml`'s `publish` job (the actual PyPI release path calls `uv build` independently — would have shipped without the bundle otherwise).

**Acceptance criteria:**
- [x] CI builds `admin-ui/` on every push/PR (at least a build check, even before full cutover)
- [x] A local `uv build` produces a wheel containing the compiled static assets
- [x] `uv sync --extra ui` on a clean machine with no `node`/`npm` installed still works

**Verification:**
- [x] Local simulation of the CI steps: `npm run build` → copy → `uv build` → inspected the wheel zip, confirmed `jukebox/adapters/inbound/admin/static/{index.html,favicon.svg,assets/*}` present
- [x] Installed the built wheel into a clean venv (Python 3.13, `[api]` extra only, no `node`/`npm`, no access to `admin-ui/` source) — `jukebox-admin api` served the Svelte bundle at `/ui/` correctly
- [x] Workflow YAML validated with `yaml.safe_load`

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `.github/workflows/python.yml`
- `pyproject.toml` (`[tool.uv.build-backend]` / MANIFEST-equivalent config)

**Estimated scope:** Small: 1-2 files

---

### Task 9: Remove FastUI

**Description:** Once Phase 2's checkpoint confirms full parity, delete the FastUI adapter and its dependency.

**Acceptance criteria:**
- [ ] `jukebox/adapters/inbound/admin/ui_controller.py` and `jukebox/adapters/inbound/admin/ui_pages/` deleted
- [ ] Associated tests deleted
- [ ] `fastui` and `python-multipart` removed from `pyproject.toml`'s `ui` extra
- [ ] `/api/ui/*` routes no longer exist; only `/api/v1/*` + static Svelte shell remain

**Verification:**
- [ ] `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`, `uv run ty check` all pass
- [ ] `uv sync --extra ui` resolves with no `fastui` in the lockfile
- [ ] Manual full smoke test of the Svelte UI end-to-end (all four pages)

**Dependencies:** Task 4, Task 5, Task 6, Task 7, Task 8

**Files likely touched:**
- `jukebox/adapters/inbound/admin/ui_controller.py` (deleted)
- `jukebox/adapters/inbound/admin/ui_pages/` (deleted)
- `tests/adapters/inbound/admin/ui_controller_test.py` and `ui_pages/*` tests (deleted)
- `pyproject.toml`

**Estimated scope:** Medium: 3-5 files (deletions)
