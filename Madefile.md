# Madefile

Development tasks for [made](https://github.com/Tarektouati/made). made reads `README.md` by default, so pass this file with `-f`:

```text
made -f Madefile.md            # list tasks
made -f Madefile.md run-ui     # run a task
```

made does not stop a task on the first error and runs it from the current directory: each task sets `-e` and moves to the repository root.

### run-ui
Build the admin UI into the Python app and serve it with jukebox-admin ui.
```shell
set -e
cd "$(git rev-parse --show-toplevel)"
npm --prefix admin-ui install
npm --prefix admin-ui run build -- --outDir ../jukebox/adapters/inbound/admin/static --emptyOutDir
# --emptyOutDir also removes the versioned .gitkeep that keeps the directory in git
touch jukebox/adapters/inbound/admin/static/.gitkeep
uv run --extra ui jukebox-admin ui
```

### check
Run the Python checks run by CI.
```shell
set -e
trap 'status=$?; [ $status -eq 0 ] && echo "✅ Python checks passed" || echo "❌ Python checks failed (exit $status)"' EXIT
cd "$(git rev-parse --show-toplevel)"
uv run ruff check
uv run ruff format --check
uv run --extra api --extra ui ty check
uv run --extra api --extra ui pytest
```

### check-ui
Run the admin UI checks run by CI.
```shell
set -e
trap 'status=$?; [ $status -eq 0 ] && echo "✅ Admin UI checks passed" || echo "❌ Admin UI checks failed (exit $status)"' EXIT
cd "$(git rev-parse --show-toplevel)/admin-ui"
npm install
npm run lint
npm run format:check
npm run build
npm test
```
