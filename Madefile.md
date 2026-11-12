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
