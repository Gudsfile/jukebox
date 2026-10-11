# Contributing to Jukebox

Thanks for your interest in Jukebox! Contributions are welcome: bug reports, ideas, documentation, and code.

---

<div align="center">

📋 Table of contents

[Reporting issues and proposing changes](#reporting-issues-and-proposing-changes) • [Development setup](#development-setup) • [Checks](#checks) • [Project layout](#project-layout) • [Architecture Decision Records (ADRs)](#architecture-decision-records-adrs) • [Commits](#commits) • [Pull requests](#pull-requests) • [License](#license)

</div>

---

## Reporting issues and proposing changes

- Search the [existing issues](https://github.com/Gudsfile/jukebox/issues) before opening a new one.
- For a bug, include your Jukebox version (`jukebox --version`), Python version, OS, player and reader, and the steps to reproduce. Logs from `--verbose` help a lot.
- For a larger change (new player, new reader, architecture change), open an issue first to discuss the approach.

## Development setup

The sections below are for code changes. You can skip them for doc fixes and issues.

Requirements:

- [uv](https://github.com/astral-sh/uv), which installs a compatible Python version
- Node.js 22 and npm, to work on the new admin UI (`admin-ui/`) and to run the pre-commit hooks on its files

```shell
git clone https://github.com/Gudsfile/jukebox.git
cd jukebox
uv sync
```

Extras are optional. Install only the ones you need:

```shell
uv sync --extra api            # REST API
uv sync --extra ui             # Web UI (includes api)
uv sync --extra pn532          # NFC reading, requires compatible hardware
```

Copy `.env.example` to `.env` if you want to use `uv run --env-file .env <command>`.

### Running locally

```shell
uv run jukebox --player PLAYER --reader READER
uv run jukebox-admin settings show
uv run --extra api jukebox-admin api   # REST API server
uv run --extra ui jukebox-admin ui     # Web UI
```

> [!NOTE]
> You do not need NFC hardware or a Sonos speaker to contribute. Use the `dryrun` player and reader with the example library:
>
> ```shell
> uv run jukebox --player dryrun --reader dryrun --library library.example.json
> ```
>
> Then type a tag id on stdin to simulate a tag on the reader (see [docs/readers.md](docs/readers.md#dry-run-dryrun)).

### New admin UI

The current admin web UI is built with FastUI, served at `/` by `jukebox-admin ui`.
A new admin UI is a work in progress in `admin-ui/` (Svelte), and will replace FastUI once complete (see [ADR 0003](docs/adr/0003-ui-framework-migration.md)).
Until then, it is served at `/ui` next to FastUI.

The Python app serves the new admin UI from `jukebox/adapters/inbound/admin/static/`, which is not versioned. To see your changes in the app, build the UI and copy it there:

```shell
cd admin-ui
npm install
npm run build
rm -rf ../jukebox/adapters/inbound/admin/static
cp -r dist ../jukebox/adapters/inbound/admin/static
cd ..
uv run --extra ui jukebox-admin ui     # then open /ui
```

`npm run dev` starts a Vite dev server, but it has no proxy to the API: calls to `/api/v1` fail there.

### Pre-commit hooks

[prek](https://github.com/j178/prek) runs formatting and linting on each commit:

```shell
uv tool install prek
prek install
```

The hooks on `admin-ui/` files call npm, so run `npm install` in `admin-ui/` first.

## Checks

CI runs these checks on every pull request. Run them locally before pushing.

Python:

```shell
uv run ruff format --check
uv run ruff check
uv run --extra api --extra ui pytest
uv run --extra api --extra ui ty check
```

New admin UI (from `admin-ui/`):

```shell
npm install
npm run lint
npm run format:check
npm run build
npm test
```

### Tests

- Add or update tests for every behavior change.
- Place tests under `tests/`, mirroring the source path.
- Use `pytest` and `pytest-mock`. To test a library use case, use the in-memory repository in `tests/jukebox/domain/use_cases/library/mock_repo.py` rather than the JSON adapter.

## Project layout

| Path                      | Content                                                                      |
| ------------------------- | ---------------------------------------------------------------------------- |
| `jukebox/`                | Main application, following a hexagonal architecture (ports and adapters)    |
| `jukebox/domain/`         | Entities, ports, repositories and use cases                                  |
| `jukebox/adapters/`       | Inbound (CLI, API, UI) and outbound (players, readers, persistence) adapters |
| `jukebox/di_container.py` | Dependency wiring                                                            |
| `admin-ui/`               | New admin UI (Svelte + Vite), work in progress to replace the FastUI one     |
| `pn532/`                  | NFC reader library, excluded from linting and type checking                  |
| `tests/`                  | Tests, mirroring the source structure                                        |
| `docs/`                   | User documentation and [architecture decision records](docs/adr/)            |

Keep business logic in `jukebox/domain/`. New players and readers go in `jukebox/adapters/outbound/`.

The tests in `tests/jukebox/architecture/` check the import rules, and fail if:

- the domain imports from `jukebox/adapters/`,
- inbound and outbound adapters import from each other,
- a module imports a domain submodule directly instead of its public API (`jukebox.domain.entities`, `jukebox.domain.ports`, etc.).

## Architecture Decision Records (ADRs)

Significant technical decisions are recorded as ADRs in [`docs/adr/`](docs/adr/). They capture the context, the options considered and the rationale, so future contributors understand _why_ the project is built the way it is.

Write an ADR when a change affects the architecture, adds a dependency or a framework, or changes a workflow (CI, release).

To add one, create `docs/adr/NNNN-short-title.md` with the next number. For example, follow the structure of [ADR 0003](docs/adr/0003-ui-framework-migration.md):

```markdown
# ADR NNNN: Title

## Status

Proposed | Accepted | Deprecated | Superseded by ADR XXXX

## Context and Problem Statement

## Considered Options

## Decision Outcome
```

## Commits

Commit messages use [gitmoji](https://gitmoji.dev/) followed by a short imperative sentence, for example:

```text
✨ Add a search bar to the admin UI Settings page
🐛 Align the Settings and Sonos titles with the Library one
♻️ Extract the disc form card into a shared .form-card class
📝 Add a CONTRIBUTING file
```

Prefer small commits that each do one thing.

## Pull requests

1. Fork the repository and create a branch from `main`, named `<type>/<short-description>` (for example `fix/invalid-state`, `docs/add-contributing-file`).
2. Make your changes, with tests and documentation updates when relevant.
3. Run the checks above.
4. Open a pull request against `main`. Link the related issue if any.
5. If `main` moves ahead, rebase your branch onto it rather than merging `main` into it.

Describe the pull request with the following sections, prefilled by the [pull request template](.github/pull_request_template.md):

- **Problem**: the need or intention covered by the pull request
- **Proposal**: the approach in plain language, what changed and why
- **Comments**: additional information, tips or problems encountered
- **Test**: how to reproduce the problem and how you tested the fix

Pull requests are merged with a merge commit, so each commit of the branch stays in the history.

> [!IMPORTANT]
> Releases are automated and handled by the maintainers (see [ADR 0002](docs/adr/0002-release-workflow.md)).
> Do not bump the version in `pyproject.toml`, and do not create commits starting with `🔖 v`: they are reserved for version bumps.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
