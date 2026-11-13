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

### run-soco
Open an interactive Python shell with SoCo objects ready to use.
```shell
set -e
cd "$(git rev-parse --show-toplevel)"
uv run python -i -c "
from soco.plugins.sharelink import ShareLinkPlugin
from rich.console import Console
from rich.table import Table

from jukebox.di_container import build_sonos_playback_target_resolver
from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter

player = SonosPlayerAdapter(
    sonos_playback_target_resolver=build_sonos_playback_target_resolver()
)
speaker = player.speaker
sharelink = ShareLinkPlugin(speaker)
uri = 'spotify:album:3IvUwbVgAZSqNh06PVxwG7'

table = Table(title='Dev Shell', show_header=True, header_style='bold cyan')
table.add_column('Variable', style='bold green')
table.add_column('Type', style='cyan')
table.add_column('Description')

table.add_row('player', type(player).__name__, 'SonosPlayerAdapter')
table.add_row('speaker', type(speaker).__name__, f'Sonos: {speaker.player_name}')
table.add_row('sharelink', type(sharelink).__name__, 'ShareLinkPlugin')
table.add_row('uri', type(uri).__name__, 'Spotify album URI')

Console().print(table)
print()
"
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
