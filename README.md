# Jukebox \[gukebox\]

![rpi](https://img.shields.io/badge/-Zero%202W%20%7C%203%20%7C%205-C51A4A?logo=raspberry-pi&label=RPi&logoColor=C51A4A&labcolor=C51A4A)
[![python versions](https://img.shields.io/pypi/pyversions/gukebox.svg?logo=python)](https://pypi.python.org/pypi/gukebox)
[![gukebox last version](https://img.shields.io/pypi/v/gukebox.svg?logo=pypi)](https://pypi.python.org/pypi/gukebox)
[![license](https://img.shields.io/pypi/l/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![actions status](https://github.com/gudsfile/jukebox/actions/workflows/python.yml/badge.svg)](https://github.com/gudsfile/jukebox/actions)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

💿 Play music on speakers using NFC tags.

🚧 At the moment:

- NFC tags - CDs must be pre-populated in a JSON file (`jukebox-admin` included with `jukebox` may be of help to you)
- supports many music providers (Spotify, Apple Music, etc.), just add the URIs to the JSON file
- only works with Sonos speakers (there is a "dryrun" player for development), but code is designed to **add new ones**
- **as soon as** the NFC tag is removed, the music pauses, then resumes when the NFC tag is replaced

💡 Inspired by:

- https://github.com/hankhank10/vinylemulator
- https://github.com/zacharycohn/jukebox

📋 Table of contents:

- [Install](#install)
- [First steps](#first-steps)
- [Usage](#usage)
- [Readers](#readers)
- [Players](#players)
- [The library file](#the-library-file)
- [Developer setup](#developer-setup)

## Python Compatibility

Jukebox 1.0+ requires Python 3.11 or newer.

| Python version | Compatible Jukebox versions | Notes |
|----------------|-----------------------------|-------|
| 3.7            | 0.4.0 – 0.4.1               | Legacy |
| 3.8            | 0.4.0 – 0.5.4               | Legacy |
| 3.9 – 3.10     | 0.4.0 – 0.9.0 (incl. 1.0.0.dev13) | Legacy |
| 3.11 – 3.12    | 0.4.0 – latest              | Actively supported |
| 3.13           | 0.5.3 – latest              | Actively supported (see installation notes) |

## Install

Install the package from [PyPI](https://pypi.org/project/gukebox/).

> [!WARNING]
> The package name is `gukebox` with `g` instead of a `j` (due to a name already taken).

> [!NOTE]
> The `pn532` extra is optional but required for NFC reading, [check compatibility](#readers).

### Recommended installation

Use `pip` in a virtual environment.

1. If your Python version is **3.13 or newer** and you want NFC support, install the system GPIO binding:
```shell
sudo apt update
sudo apt install python3-lgpio
```

2. Create a virtual environment:
```shell
# Python < 3.13
python3 -m venv jukebox

# Python >= 3.13 for NFC: use the system Python and include system packages
python3 -m venv --system-site-packages jukebox

source jukebox/bin/activate
```

3. Install `gukebox` into the virtual environment:
```shell
pip install "gukebox[pn532]"
```

> [!IMPORTANT]
> For NFC on Python 3.13+, use the **system Python** that comes with your OS.
> A separately installed Python 3.13+ from `uv`, `pyenv`, Homebrew, or similar may not be able
> to import the system `lgpio` package, even when using `--system-site-packages`.
> If you already upgraded to a non-system Python 3.13+, use the system Python instead or use
> Python 3.12 or lower.

### Alternative installations

- `pipx` can be used with `--system-site-packages`.
- `uvx` / `uv tool install` are not recommended for NFC on Python 3.13+ because they may select a non-system interpreter.
- For non-system Python 3.13+, you can still install via pip/uv/poetry/etc. but you must build the `lgpio` package from source and it may require other system packages.
- All releases can be downloaded and installed from the [GitHub releases page](https://github.com/Gudsfile/jukebox/releases).

### Installation for development

For development read the [Developer setup](#developer-setup) section.

tl;dr:
```shell
git clone https://github.com/Gudsfile/jukebox.git
uv sync
```

## First steps

Initialize the library file with `jukebox-admin` or manually create it at `~/.config/jukebox/library.json`.

### Manage the library with the Admin CLI

To associate an URI with an NFC tag:

```shell
jukebox-admin library add tag_id --uri /path/to/media.mp3
```
or to pull the `tag_id` currently on the reader:
```shell
jukebox-admin library add --from-current --uri /path/to/media.mp3
```

Other commands are available, use `--help` to see them.

### Admin CLI

Use `jukebox-admin` for admin workflows such as settings inspection and the
admin API/UI servers.

```shell
jukebox-admin settings show
jukebox-admin settings show --effective
```

To use the `api` and `ui` commands, additional packages are required. You can install the `package[extra]` syntax regardless of the package manager you use, for example:

```shell
uv tool install gukebox[api]

# ui includes the api extra
uv tool install gukebox[ui]
```

When running from this repository with `uv`, include the extra on the command as well:

```shell
uv run --extra api jukebox-admin api
uv run --extra ui jukebox-admin ui
```

### Manage the library manually

Complete your `~/.config/jukebox/library.json` file with each tag id and the expected media URI.
Take a look at `library.example.json` and the [The library file](#the-library-file) section for more information.

## Usage

Start the jukebox with the `jukebox` command (show help message with `--help`)

```shell
jukebox --player PLAYER --reader READER
```

🎉 With choosing the `sonos` player and `pn532` reader, by approaching a NFC tag stored in the `library.json` file, you should hear the associated music begins.

**Optional Parameters**

| Parameter | Description |
| --- | --- |
| `--help` | Show help message. |
| `--player PLAYER` | Player to use (`sonos`, `dryrun`). |
| `--reader READER` | Reader to use (`pn532`, `dryrun`). |
| `--library` | Path to the library file, default: `~/.config/jukebox/library.json`. |
| `--pause-delay SECONDS` | Grace period before pausing when the NFC tag is removed. Fractional values such as `0.5` or `0.2` are supported, with a minimum of `0.2` seconds to avoid pausing on brief missed reads. Default: 0.25 seconds. |
| `--pause-duration SECONDS` | Maximum duration of a pause before resetting the queue. Default: 900 seconds (15 minutes). |
| `--verbose` | Enable verbose logging. |
| `--version` | Show version. |

### Readers

| Name | Description |
| --- | --- |
| Dry Run (`dryrun`) | Simulates NFC tag reading via stdin. Input format: `tag_id` or `tag_id duration_seconds`. |
| Pn532 NFC (`pn532`) | Reads physical NFC tags. Works with a **PN532** reader and **NTAG2xx** tags. Requires the `pn532` extra and SPI enabled on the Raspberry Pi. |

> [!NOTE]
> See [docs/readers.md](docs/readers.md) for full setup, hardware requirements, and settings reference.

### Players

| Name | Description |
| --- | --- |
| Dry Run (`dryrun`) | Displays the events that a real speaker would have performed (`playing …`, `pause`, etc.). |
| Sonos (`sonos`) | [![SoCo](https://img.shields.io/badge/based%20on-SoCo-000)](https://github.com/SoCo/SoCo) Plays music through a Sonos speaker. Select by IP (`--sonos-host`), by name (`--sonos-name`), or let it auto-discover. |

> [!NOTE]
> See [docs/players.md](docs/players.md) for the full configuration reference.

## The library file

The `library.json` file is a JSON file that contains the artists, albums and tags.
It is used by the `jukebox` command to find the corresponding metadata for each tag.
And the `jukebox-admin library` command help you to managed this file with a CLI, an interactive CLI, an API or an UI (see `jukebox-admin --help`).

By default, this file should be placed at `~/.config/jukebox/library.json`. But you can use another path by creating a `JUKEBOX_LIBRARY_PATH` environment variable or with the `--library` argument.

```json
{
  "discs": {
    "a:tag:uid": {
      "uri": "URI of a track, an album or a playlist on many providers",
      "option": { "shuffle": true }
    },
    "another:tag:uid": {
      "uri": "uri"
    },
    …
  }
}
```

The `discs` part is a dictionary containing NFC tag UIDs.
Each UID is associated with an URI.
URIs are the URIs of the music providers (Spotify, Apple Music, etc.) and relate to tracks, albums, playlists, etc.

`metadata` is an optional section where the names of the artist, album, song, or playlist are entered:

```json
    "a:tag:uid": {
      "uri": "uri",
      "metadata": { "artist": "artist" }
    }
```

It is also possible to use the `shuffle` key to play the album in shuffle mode:

```json
    "a:tag:uid": {
      "uri": "uri",
      "option": { "shuffle": true }
    }
```

To summarize, for example, if you have the following `~/.config/jukebox/library.json` file:

```json
{
  "discs": {
    "ta:g1:id": {
      "uri": "uri1",
      "metadata": { "artist": "a", "album": "a" }
    },
    "ta:g2:id": {
      "uri": "uri2",
      "metadata": { "playlist": "b" },
      "option": { "shuffle": true }
    }
  }
}
```

Then, the jukebox will find the metadata for the tag `ta:g2:id` and will send the `uri2` to the speaker so that it plays playlist "b" in random order.

## Developer setup

### Install

Install the project by cloning it and using [uv](https://github.com/astral-sh/uv) to install the dependencies:

```shell
git clone https://github.com/Gudsfile/jukebox.git
uv sync
```

Add `--all-extras` to install dependencies for all extras (`api` and `ui`).

If needed, you can use a `.env` file and `uv run --env-file .env <command to run>`.
A `.env.example` file is available, you can copy it and modify it to use it.

Create a `library.json` file and complete it with the desired NFC tags and CDs.
Take a look at `library.example.json` and the [The library file](#the-library-file) section for more information.

### Usage

Start the jukebox with `uv` and use `--help` to show help message

```shell
uv run jukebox --player PLAYER_TO_USE --reader READER_TO_USE
```

Use `jukebox-admin` for admin commands:

```shell
uv run jukebox-admin settings show
```

For the server-backed admin commands, include the matching extra:

```shell
uv run --extra api jukebox-admin api
uv run --extra ui jukebox-admin ui
```

### Development commands

| Command | Description |
| --- | --- |
| `uv run ruff format` | Format the code. |
| `uv run ruff check` | Check the code. |
| `uv run ruff check --fix` | Fix the code. |
| `uv run pytest` | Run the tests. |

### Pre-commit

[prek](https://github.com/j178/prek) is configured; you can [install it](https://github.com/j178/prek?tab=readme-ov-file#installation) to automatically run validations on each commit.

```shell
uv tool install prek
prek install
```

## Contributing

Contributions are welcome! Feel free to open an issue or a pull request.
