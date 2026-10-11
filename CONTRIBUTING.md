# Contributing to Jukebox

Thanks for your interest in Jukebox! Contributions are welcome: bug reports, ideas, documentation, and code.

## Reporting issues and proposing changes

- Search the [existing issues](https://github.com/Gudsfile/jukebox/issues) before opening a new one.
- For a bug, include your Jukebox version (`jukebox --version`), Python version, OS, player and reader, and the steps to reproduce. Logs from `--verbose` help a lot.
- For a larger change (new player, new reader, architecture change), open an issue first to discuss the approach.

## Development setup

Requirements:

- [uv](https://github.com/astral-sh/uv), which installs a compatible Python version
- Node.js 22 and npm, only to work on the admin UI (`admin-ui/`)

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

> [!NOTE]
> You do not need NFC hardware or a Sonos speaker to contribute.
> Use the `dryrun` player and reader: `uv run jukebox --player dryrun --reader dryrun`.

Copy `.env.example` to `.env` if you want to use `uv run --env-file .env <command>`, and `library.example.json` to create a test library.

### Pre-commit hooks

[prek](https://github.com/j178/prek) runs formatting and linting on each commit:

```shell
uv tool install prek
prek install
```

## Project layout

| Path | Content |
| --- | --- |
| `jukebox/` | Main application, following a hexagonal architecture (ports and adapters) |
| `jukebox/domain/` | Entities, ports, repositories and use cases, without external dependencies |
| `jukebox/adapters/` | Inbound (CLI, API, UI) and outbound (players, readers, persistence) adapters |
| `jukebox/di_container.py` | Dependency wiring |
| `admin-ui/` | Svelte + Vite SPA, replacing the FastUI admin UI (see [ADR 0003](docs/adr/0003-ui-framework-migration.md)) |
| `pn532/` | NFC reader library, excluded from linting and type checking |
| `tests/` | Tests, mirroring the source structure |
| `docs/` | User documentation and [architecture decision records](docs/adr/) |

Keep business logic in `jukebox/domain/` and free of external dependencies. New players and readers go in `jukebox/adapters/outbound/`.

## Checks

CI runs these checks on every pull request. Run them locally before pushing.

Python:

```shell
uv run ruff format --check
uv run ruff check
uv run pytest
uv run ty check
```

Use `uv run --extra api --extra ui pytest` to also run the tests that need these extras.

Admin UI (from `admin-ui/`):

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
- Use `pytest` and `pytest-mock`. Mock repositories instead of using the real JSON adapter.

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

Describe the pull request with:

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
