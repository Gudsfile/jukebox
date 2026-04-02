# Jukebox \[gukebox\]

[![python versions](https://img.shields.io/pypi/pyversions/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![gukebox last version](https://img.shields.io/pypi/v/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![license](https://img.shields.io/pypi/l/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![actions status](https://github.com/gudsfile/jukebox/actions/workflows/python.yml/badge.svg)](https://github.com/gudsfile/jukebox/actions)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

💿 Play music on speakers using NFC tags.

🚧 At the moment:

- NFC tags - CDs must be pre-populated in a JSON file (`discstore` included with `jukebox` may be of help to you)
- supports many music providers (Spotify, Apple Music, etc.), just add the URIs to the JSON file
- only works with Sonos speakers (there is a "dryrun" player for development), but code is designed to **add new ones**
- **as soon as** the NFC tag is removed, the music pauses, then resumes when the NFC tag is replaced

💡 Inspired by:

- https://github.com/hankhank10/vinylemulator
- https://github.com/zacharycohn/jukebox

📋 Table of contents:

- [Install](#install)
- [First steps](#first-steps)
  - [Discstore](#manage-the-library-with-the-discstore)
- [Usage](#usage)
  - [Readers](#readers)
  - [Players](#players)
- [The library file](#the-library-file)
- [Developer setup](#developer-setup)

## Notes

Python 3.7 is supported by Jukebox up to version 0.4.1.

Python 3.8 is supported by Jukebox up to version 0.5.4.

The `ui` extension is only available for Python versions 3.10 and above.

## Install

Install the package from [PyPI](https://pypi.org/project/gukebox/).

> [!WARNING]
> The package name is `gukebox` with `g` instead of a `j` (due to a name already taken).

> [!NOTE]
> The `nfc` extra is optional but required for NFC reading, [check compatibility](#readers).

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
pip install "gukebox[nfc]"
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

Initialize the library file with `discstore` or manually create it at `~/.jukebox/library.json`.

### Manage the library with the discstore

To associate an URI with an NFC tag:

```shell
discstore add tag_id --uri /path/to/media.mp3
```
or to pull the `tag_id` currently on the reader:
```shell
discstore add --from-current --uri /path/to/media.mp3
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
# Python 3.9+ required
uv tool install gukebox[api]

# Python 3.10+ required, ui includes the api extra
uv tool install gukebox[ui]
```

When running from this repository with `uv`, include the extra on the command as well:

```shell
uv run --extra api jukebox-admin api
uv run --extra ui jukebox-admin ui
```

`discstore settings ...`, `discstore api`, and `discstore ui` remain available as compatibility commands, but `jukebox-admin` is the preferred CLI for admin flows.

### Manage the library manually

Complete your `~/.jukebox/library.json` file with each tag id and the expected media URI.
Take a look at `library.example.json` and the [The library file](#the-library-file) section for more information.

## Usage

Start the jukebox with the `jukebox` command (show help message with `--help`)

```shell
jukebox PLAYER_TO_USE READER_TO_USE
```

🎉 With choosing the `sonos` player and `nfc` reader, by approaching a NFC tag stored in the `library.json` file, you should hear the associated music begins.

Optional Parameters

| Parameter | Description |
| --- | --- |
| `--help` | Show help message. |
| `--library` | Path to the library file, default: `~/.jukebox/library.json`. |
| `--pause-delay SECONDS` | Grace period before pausing when the NFC tag is removed. Fractional values such as `0.5` or `0.2` are supported, with a minimum of `0.2` seconds to avoid pausing on brief missed reads. Default: 0.25 seconds. |
| `--pause-duration SECONDS` | Maximum duration of a pause before resetting the queue. Default: 900 seconds (15 minutes). |
| `--verbose` | Enable verbose logging. |
| `--version` | Show version. |

### Readers

**Dry run** (`dryrun`)
Read a text entry.
Allows you to simulate reading an NFC tag by writting the tag id in the console.
Expected syntax: `tag_id` or `tag_id duration_seconds`.
- tag_id: the full identifier of the tag, in the format required by the system
- duration_seconds: a non-negative number of seconds used to simulate how long the tag remains in place. Fractional values are allowed.
Complete example: `your:tag:uid 2.5`

**NFC** (`nfc`)
Read an NFC tag and get its UID.
This project works with an NFC reader like the **PN532** and NFC tags like the **NTAG2xx**.
It is configured according to the [Waveshare PN532 wiki](https://www.waveshare.com/wiki/PN532_NFC_HAT).
Don't forget to enable the SPI interface using the command `sudo raspi-config`, then go to: `Interface Options > SPI > Enable > Yes`.

### Players

**Dry run** (`dryrun`)
Displays the events that a real speaker would have performed (`playing …`, `pause`, etc.).

**Sonos** (`sonos`) [![SoCo](https://img.shields.io/badge/based%20on-SoCo-000)](https://github.com/SoCo/SoCo)
Play music through a Sonos speaker.
Three ways to select the speaker (mutually exclusive):

| Option | CLI flag | Environment variable | Behaviour |
| --- | --- | --- | --- |
| By IP | `--sonos-host 192.168.0.x` | `JUKEBOX_SONOS_HOST` | Connect directly, no discovery |
| By name | `--sonos-name "Living Room"` | `JUKEBOX_SONOS_NAME` | Discover, then filter by name (case-sensitive) |
| Auto | *(omit both)* | *(omit both)* | Discover, pick the first speaker alphabetically |

## The library file

The `library.json` file is a JSON file that contains the artists, albums and tags.
It is used by the `jukebox` command to find the corresponding metadata for each tag.
And the `discstore` command help you to managed this file with a CLI, an interactive CLI, an API or an UI (see `discstore --help`).

By default, this file should be placed at `~/.jukebox/library.json`. But you can use another path by creating a `JUKEBOX_LIBRARY_PATH` environment variable or with the `--library` argument.

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

To summarize, for example, if you have the following `~/.jukebox/library.json` file:

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

If needed, set `JUKEBOX_SONOS_HOST` (IP) or `JUKEBOX_SONOS_NAME` (speaker name) to select your Sonos speaker (see [Players](#players)).
If neither is set, the jukebox will auto-discover a speaker on the network.
To do this you can use a `.env` file and `uv run --env-file .env <command to run>`.
A `.env.example` file is available, you can copy it and modify it to use it.

Create a `library.json` file and complete it with the desired NFC tags and CDs.
Take a look at `library.example.json` and the [The library file](#the-library-file) section for more information.

### Usage

Start the jukebox with `uv` and use `--help` to show help message

```shell
uv run jukebox PLAYER_TO_USE READER_TO_USE
```

Start the discstore `uv` and use `--help` to show help message
```shell
uv run discstore --help
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

Legacy compatibility commands remain available during the transition:

```shell
uv run discstore settings show
uv run --extra api discstore api
uv run --extra ui discstore ui
```

Other commands are available:

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
