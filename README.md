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
The `ui` extension is only available for Python versions 3.10 and above.

Raspberry Pi 5 on Python >= 3.13 is currently not supported (https://github.com/Gudsfile/jukebox/pull/86).

## Install

### PyPI

Install the package from [PyPI](https://pypi.org/project/gukebox/).

> [!WARNING]
> The package name is `gukebox` with `g` instead of a `j` (due to a name already taken).

To invoke the tool without installing it you could use `uvx`:

```shell
uvx --from gukebox[nfc] jukebox
```

Or install it into an isolated environment with `uv tool install` or `pipx`.

> [!NOTE]
> The `nfc` extra is optional but required for NFC reading, [check compatibility](#available-players-and-readers).

### GitHub Releases

All releases can be downloaded and installed from the [GitHub releases page](https://github.com/Gudsfile/jukebox/releases).

### Developer setup

For development read the [Developer setup](##developer-setup) section.

tl;dr:
```shell
git clone https://github.com/Gudsfile/jukebox.git
uv sync
```

## First steps

Set the `JUKEBOX_SONOS_HOST` environment variable with the IP address of your Sonos Zone Player (see [Available players and readers](#available-players-and-readers)).

Initialize the library file with `discstore` or manually create it at `~/.jukebox/library.json`.

### Manage the library with the discstore

To associate an URI with an NFC tag:

```shell
discstore add tag_id uri
```

Other commands are available, use `--help` to see them.

To use the `api` and `ui` commands, additional packages are required. You can install the `package[extra]` syntax regardless of the package manager you use, for example:

```shell
# Python 3.8+ required
uv tool install gukebox[api]

# Python 3.10+ required, ui includes the api extra
uv tool install gukebox[ui]
```

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
| `--pause-delay SECONDS` | Grace period (in seconds) before pausing when the NFC tag is removed. This prevents accidental pauses if the tag briefly loses contact. Default: 1 second. |
| `--pause-duration SECONDS` | Maximum duration of a pause before resetting the queue. Default: 900 seconds (15 minutes). |
| `--verbose` | Enable verbose logging. |
| `--version` | Show version. |

### Readers

**Dry run** (`dryrun`)
Read a text entry.
Allows you to simulate reading an NFC tag by writting the tag id in the console.
Expected syntax: `tag_id` or `tag_id counter`.
- tag_id: the full identifier of the tag, in the format required by the system
- counter: an integer used to simulate the internal counter of the tag. Increasing the counter simulates the tag remaining in place and being read repeatedly by the system.
Complete example: `your:tag:uid 10`

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
`JUKEBOX_SONOS_HOST` environment variable must be set with the IP address of your Sonos Zone Player.
You could set the environment varible with `export JUKEBOX_SONOS_HOST=192.168.0.???` to use this speaker through the `jukebox` command.
Or set it in a `.env` file to use the `uv run --env-file .env <command to run>` version.

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

Set the `JUKEBOX_SONOS_HOST` environment variable with the IP address of your Sonos Zone Player (see [Available players and readers](#available-players-and-readers)).
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

Other commands are available:

| Command | Description |
| --- | --- |
| `uv run ruff format` | Format the code. |
| `uv run ruff check` | Check the code. |
| `uv run ruff check --fix` | Fix the code. |
| `uv run pytest` | Run the tests. |

## Contributing

Contributions are welcome! Feel free to open an issue or a pull request.
