# ADR 0002: Release Workflow

## Status

Accepted

Superseded by [Decision (v3)](#decision-outcome-v3)

## Context and Problem Statement

The previous `bump-version.yml` workflow only supported `major`, `minor`, and `patch` bumps. This made it impossible to publish pre-release dev versions (`x.y.z.devN`) through the automated CI pipeline. Dev versions are useful for iterating on upcoming releases while allowing early adopters to test changes via PyPI.

`uv version --bump` supports composable bump types: `major`, `minor`, `patch`, `dev`, `stable`, `alpha`, `beta`, `rc`, `post`. Multiple `--bump` flags can be combined (e.g., `--bump minor --bump dev` produces `1.0.0 → 1.1.0.dev0`).

The challenge: automate full dev/stable versioning while ensuring CI runs, branch protection is respected, and releases are safe.

## Considered Options

### Option 1: PR-based version bump (v1)

#### Version bump workflow (`bump-version.yml`)

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

#### Auto-approve and auto-merge

GitHub blocks self-approval: the actor that opens a PR cannot approve it. To enable fully automated merges while respecting branch protection (required approvals), two distinct actors are used:

- `github-actions[bot]` (`GITHUB_TOKEN`) — commits, pushes, and opens the PR
- A GitHub App (secrets `APP_ID` / `PRIVATE_KEY`, via `actions/create-github-app-token`) — approves the PR and enables auto-merge

The app token is used only for the approve + auto-merge step. The merge itself is attributed to the app, which allows `release.yml` to trigger (merges by `GITHUB_TOKEN` do not trigger downstream workflows).

#### Release workflow (`release.yml`)

- **Dev versions** (`.devN`): publish to PyPI only. No GitHub Release is created — dev builds are not stable enough to warrant a formal release entry.
- **Stable versions**: publish to PyPI and create a GitHub Release automatically (no draft).

Detection: `uv version --short | grep -q '\.dev'`

### Option 2: Direct push + tag trigger

`bump-version.yml` pushes the version commit directly to `main` (via App token bypass) and also pushes a tag `v{version}`. `release.yml` is triggered by `push: tags: [v*]` and publishes immediately.

**Rejected**: the publication would happen before CI runs on the bump commit. There is no guarantee that tests pass before the package is published.

### Option 3: Workflow_run with polling

`bump-version.yml` pushes commit and tag. `release.yml` is triggered by `workflow_run` and polls `gh api` to check that a `v*` tag exists on the triggering SHA before publishing.

**Rejected**: unnecessary complexity. Polling an external API adds flakiness and latency with no architectural benefit over creating the tag as an output of the release step.

### Option 4: Direct push with workflow_run (v2)

#### Version bump workflow (`bump-version.yml`)

Same 8 bump types as v1. The difference is the delivery mechanism:

- The GitHub App token is used for **checkout** (not just approval), so the subsequent push bypasses branch protection.
- The version bump commit is pushed **directly to `main`** — no branch, no PR.
- No tag is created here; the tag is an output of the release step (after CI passes).

#### Release workflow (`release.yml`)

Triggered by `workflow_run` on `python.yml` (ci) completing, filtered to the `main` branch:

```yaml
on:
  workflow_run:
    workflows: ["ci"]
    types: [completed]
    branches: [main]
```

The `branches: [main]` filter is evaluated against the branch the triggering workflow ran on. Since `python.yml` also runs on pull requests (which run on PR head branches, never `main`), this filter prevents PR-triggered CI from firing the release workflow at the event level.

Job condition:

```yaml
if: |
  github.event_name == 'workflow_dispatch'
  || (
    github.event_name == 'workflow_run'
    && github.event.workflow_run.conclusion == 'success'
    && startsWith(github.event.workflow_run.head_commit.message, '🔖 v')
  )
```

The commit message check (`🔖 v`) distinguishes version bump commits from regular pushes to `main`.

On successful publish, `release.yml` creates and pushes the git tag. The tag is an output of the release, not its trigger.

`workflow_dispatch` retains its dry-run input for testing the workflow manually. It does not publish for real.

#### Security properties of `workflow_run`

`workflow_run` always executes the workflow file from the **default branch** (`main`), never from a PR branch. A PR that modifies `release.yml` to remove the guards has no effect until it is merged. This is the key property that makes `workflow_run` safe for privileged operations, unlike `pull_request_target`.

- **Dev versions** (`.devN`): publish to PyPI only.
- **Stable versions**: publish to PyPI, create git tag, create GitHub Release.

#### Guard workflow (`protect-version-bump.yml`)

Since version bump commits are pushed directly to `main`, a dedicated workflow blocks any PR that contains a commit starting with `🔖 v`, preventing accidental inclusion of bump commits in regular PRs.

### Option 5: Single dispatched release workflow (v3)

#### Release workflow (`release.yml`)

`bump-version.yml` and `release.yml` are merged into a single workflow, triggered manually only:

```yaml
on:
  workflow_dispatch:
    inputs:
      bump:
        type: choice
        options: [major, minor, patch, major-dev, minor-dev, patch-dev, dev, stable]
```

It runs two jobs:

1. `test`: format, lint, tests and type check on the commit to release.
2. `publish` (`needs: test`, `prod` environment): fails unless dispatched from `main`, bumps the version with the same 8 bump types as v1, commits `🔖 v{version}` and tags `v{version}` with the GitHub App token, pushes the commit and the tag together, builds the admin UI bundle and the package, and publishes to PyPI.

- **Dev versions** (`.devN`): publish to PyPI only.
- **Stable versions**: publish to PyPI and create a GitHub Release.

The version is bumped, tagged and published only when the tests pass, without `workflow_run`, polling or a separate guard workflow.

#### CI on pull requests (`ci.yml`)

Since the release workflow runs its own tests, CI runs on pull requests only, not on pushes to `main`.

`ci.yml` runs on every pull request, without `paths`:

- `changes` lists the files of the pull request and decides which parts to check (Python, admin UI; a change under `.github/workflows/` checks both).
- `python` and `admin-ui` call the reusable workflows `python.yml` and `admin-ui.yml` (`workflow_call`), only when their part changed. Both keep `workflow_dispatch` to run them by hand.
- `ci-result` needs all of them and runs `if: always()`: it passes when every job succeeded or was skipped, and fails otherwise.

`ci-result` is the required status check of the `main` ruleset. As it runs on every pull request, the check never stays pending, and a failing job blocks the merge.

## Decision Outcome (v1)

We adopted solution 1 (PR-based version bump).

## Decision Outcome (v2)

We adopted solution 4 (Direct push + workflow_run) because it:
- Ensures CI is executed before publishing.
- Provides linear, verifiable git history.
- Keeps dev/stable release automation fully automated.
- Preserves security and branch protection.

## Decision Outcome (v3)

We adopted solution 5 (Single dispatched release workflow) because it:
- Runs the tests before the version is bumped, tagged and published.
- Keeps the whole release in one workflow, with no `workflow_run` trigger or guard workflow.
- Keeps dev/stable release automation fully automated.

## More information

Why decision v1 was superseded?

v1's PR-based approach has a fundamental flaw: **CI does not run on auto-created PRs**. GitHub deliberately prevents `pull_request` workflow triggers from firing when the PR is opened by `GITHUB_TOKEN` (anti-loop protection). The GitHub App workaround allowed merging but did not fix the missing CI runs — the version bump was never tested before publication.

Why decision v2 was superseded?

v2 split the release across three workflows (`bump-version.yml`, `release.yml`, `protect-version-bump.yml`) and relied on CI running on pushes to `main`. A single workflow that tests, then bumps, tags and publishes gives the same guarantee with fewer moving parts.
