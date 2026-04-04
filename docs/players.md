# Players

A player is an outbound adapter that receives playback commands from the jukebox (play, pause, resume, stop).
Select a player with `--player`:

```shell
jukebox --player PLAYER --reader READER
```

You can also persist the choice so you don't need to pass it each time:

```shell
jukebox-admin settings set jukebox.player.type PLAYER
```

## Dryrun (`dryrun`)

Logs simulated playback events without sending any audio output. Useful for development and testing.

No configuration required.

## Sonos (`sonos`) [![SoCo](https://img.shields.io/badge/based%20on-SoCo-000)](https://github.com/SoCo/SoCo)

Plays music through a Sonos speaker.

### Ways to set the target

| Layer | How to set | Notes |
| --- | --- | --- |
| CLI | `--sonos-host <ip>` or `--sonos-name <name>` | Overrides everything for the current process |
| Environment | `JUKEBOX_SONOS_HOST` or `JUKEBOX_SONOS_NAME` | Overrides persisted settings for the current process |
| Persisted | `jukebox.player.sonos.selected_group` (written automatically) | Reused across restarts when no CLI/env override is given |

`--sonos-host` and `--sonos-name` (and their env equivalents) are mutually exclusive. CLI enforces this directly; if both appear via env or persisted data, runtime resolution fails.

### Source precedence

When settings are merged, higher layers override lower ones:

```
Defaults < Persisted settings < Environment < CLI
```

So CLI beats environment, and environment beats persisted settings.

> CLI and environment Sonos overrides are process-local: they intentionally clear the persisted `selected_group` for that run. For example, `--sonos-host` ignores any stored group, and `JUKEBOX_SONOS_NAME` replaces a persisted group for the duration of the process.

### Target resolution

Once the merged settings object is built, the Sonos target is resolved in this order:

1. **`manual_host`** — set by `--sonos-host` or `JUKEBOX_SONOS_HOST`
2. **`selected_group` host** — resolved from the persisted group: coordinator's `last_known_host`, then first member with a `last_known_host`; if no host can be resolved from the group, falls through to the next step
3. **`manual_name`** — set by `--sonos-name` or `JUKEBOX_SONOS_NAME`; discovers and filters by name (case-sensitive)
4. **Auto** — discovers and picks the first speaker alphabetically

Short version: `CLI host/name > env host/name > persisted selected_group`, then within the merged result: `manual_host > selected_group host > manual_name > auto`.

### Persistent settings

| Settings path | Description |
| --- | --- |
| `jukebox.player.type` | Persists the player choice across restarts (avoids passing `--player` each time) |
| `jukebox.player.sonos.selected_group` | Persisted Sonos group written automatically at startup — do not edit manually |

> `manual_host` and `manual_name` cannot be set via `jukebox-admin settings set` (they are not in the editable definitions). Use CLI flags or environment variables for process-local host/name overrides.
