# ADR 0002: Release Workflow

## Status

Accepted

## Context

The previous `bump-version.yml` workflow only supported `major`, `minor`, and `patch` bumps, making it impossible to publish pre-release dev versions (`x.y.z.devN`) through the automated CI pipeline. Dev versions are useful for iterating on upcoming releases while allowing early adopters to test changes via PyPI.

`uv version --bump` supports composable bump types: `major`, `minor`, `patch`, `dev`, `stable`, `alpha`, `beta`, `rc`, `post`. Multiple `--bump` flags can be combined (e.g. `--bump minor --bump dev` produces `1.0.0 → 1.1.0.dev0`).

## Decision

### Version bump workflow (`bump-version.yml`)

Extend the workflow with 8 bump types covering the full dev/stable cycle:

| Input | uv command | Example |
|-------|-----------|---------|
| `major` | `uv version --bump major` | `1.0.0 → 2.0.0` |
| `minor` | `uv version --bump minor` | `1.0.0 → 1.1.0` |
| `patch` | `uv version --bump patch` | `1.0.0 → 1.0.1` |
| `major-dev` | `uv version --bump major --bump dev` | `1.0.0 → 2.0.0.dev0` |
| `minor-dev` | `uv version --bump minor --bump dev` | `1.0.0 → 1.1.0.dev0` |
| `patch-dev` | `uv version --bump patch --bump dev` | `1.0.0 → 1.0.1.dev0` |
| `dev` | `uv version --bump dev` | `1.1.0.dev0 → 1.1.0.dev1` |
| `stable` | `uv version --bump stable` | `1.1.0.dev2 → 1.1.0` |

Typical dev cycle:
```
minor-dev  →  1.0.0 → 1.1.0.dev0
dev        →  1.1.0.dev0 → 1.1.0.dev1
dev        →  1.1.0.dev1 → 1.1.0.dev2
stable     →  1.1.0.dev2 → 1.1.0
```

The PR is created by `github-actions[bot]` (using `GITHUB_TOKEN`), which fixes the broken git config.

### Auto-approve and auto-merge

GitHub blocks self-approval: the actor that opens a PR cannot approve it. To enable fully automated merges while respecting branch protection (required approvals), two distinct actors are used:

- `github-actions[bot]` (`GITHUB_TOKEN`) — commits, pushes, and opens the PR
- A GitHub App (secrets `APP_ID` / `PRIVATE_KEY`, via `actions/create-github-app-token`) — approves the PR and enables auto-merge

The app token is used only for the approve + auto-merge step. The merge itself is attributed to the app, which allows `release.yml` to trigger (merges by `GITHUB_TOKEN` do not trigger downstream workflows).

### Release workflow (`release.yml`)

- **Dev versions** (`.devN`): publish to PyPI only. No GitHub Release is created — dev builds are not stable enough to warrant a formal release entry.
- **Stable versions**: publish to PyPI and create a GitHub Release automatically (no draft).

Detection: `uv version --short | grep -q '\.dev'`

## Consequences

- The full dev iteration cycle is automated through CI without local tooling.
- PyPI always reflects the latest published version, including dev builds.
- GitHub Releases remain clean (stable versions only), reducing noise.
- Automated commits use `github-actions[bot]` as the author.
- Branch protection (required approvals) is satisfied without bypassing it — the GitHub App acts as a legitimate reviewer.
- Stable GitHub Releases are published immediately on merge.
