# Jukebox \[gukebox\]

[![python versions](https://img.shields.io/pypi/pyversions/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![gukebox last version](https://img.shields.io/pypi/v/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![license](https://img.shields.io/pypi/l/gukebox.svg)](https://pypi.python.org/pypi/gukebox)
[![actions status](https://github.com/gudsfile/jukebox/actions/workflows/python.yml/badge.svg)](https://github.com/gudsfile/jukebox/actions)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

💿 Play music on speakers using NFC tags.

🚧 At the moment:

- NFC tags - CDs must be pre-populated in a JSON file (`discstore` included with `jukebox` may be of help to you)
- supports many music providers (Spotify, Apple Music, etc.), just add the URIs to the JSON file
- only works with Sonos speakers (there is a "dryrun" player for development), but code is designed to be modified to add new ones
- **as soon as** the NFC tag is removed, the music pauses, then resumes when the NFC tag is replaced

💡 Inspired by:

- https://github.com/hankhank10/vinylemulator
- https://github.com/zacharycohn/jukebox

📋 Table of contents:

- [Install](#install)
- [Usage](#usage)
- [First steps](#first-steps)
- [Available players and readers](#available-players-and-readers)
  - [Readers](#readers)
  - [Players](#players)
- [The library file](#the-library-file)
- [Developer setup](#developer-setup)

## Notes

The project remains in Python 3.7 to make it easier to use on hardware like Raspberry Pi.
However, it works on Python versions 3.7+.
The `api` and `ui` extras are only available for Python versions 3.8+ and 3.10+.

## Install

### PyPI

Install the package from [PyPI](https://pypi.org/project/gukebox/).

> [!WARNING]
> The package name is `gukebox` with `g` instead of a `j` (due to a name already taken).

To invoke the tool without installing it you could use `uvx`:

```shell
uvx --from gukebox[nfc] jukebox
```

It is recommended to installing `jukebox` into an isolated environment, e.g., with `uv tool install`:

```shell
uv tool install gukebox[nfc]
```

or with `pipx`

```shell
pipx install gukebox[nfc]
```

However you could install it with `pip`:

```shell
pip install gukebox[nfc]
```

> [!NOTE]
> The `nfc` extra is optional but required for installations in isolated environments.
> This extra is used for NFC reading, [check compatibility](#available-players-and-readers)).

### GitHub Releases

All releases can be downloaded from the [GitHub releases page](https://github.com/Gudsfile/jukebox/releases).

## First steps

Set the `SONOS_HOST` environment variable with the IP address of your Sonos Zone Player (see [Available players and readers](#available-players-and-readers)).

Create a `~/.jukebox/library.json` file and complete it with the desired artists and albums.
For this, you can use `discstore` installed with the package or write it manually.

### Using the discstore

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

### Manually

Complete your `~/.jukebox/library.json` file with each tag id and the expected media URI.
Take a look at `sample_library.json` and the [The library file](#the-library-file) section for more information.

## Usage

Start the jukebox with the `jukebox` command (show help message with `--help`)

```shell
jukebox PLAYER_TO_USE READER_TO_USE -l YOUR_LIBRARY_FILE
```

🎉 With choosing the `sonos` player and `nfc` reader, by approaching a NFC tag stored in the `library.json` file, you should hear the associated music begins.

## Available players and readers

### Readers

**Dry run** (`dryrun`)
Read a text entry.

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
`SONOS_HOST` environment variable must be set with the IP address of your Sonos Zone Player.
You could set the environment varible with `export SONOS_HOST=192.168.0.???` to use this speaker through the `jukebox` command.
Or set it in a `.env` file to use the `uv run --env-file .env <command to run>` version.

## The library file

The `library.json` file is a JSON file that contains the artists, albums and tags.
It is used by the `jukebox` command to find the corresponding metadata for each tag.
And the `discsstore` command help you to managed this file with a CLI, an interactive CLI, an API or an UI (see `discstore --help`).

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

Clone the project.

Installing dependencies with [uv](https://github.com/astral-sh/uv):

```shell
uv sync
```

Add `--all-extras` to install dependencies for all extras (`api` and `ui`).

Set the `SONOS_HOST` environment variable with the IP address of your Sonos Zone Player (see [Available players and readers](#available-players-and-readers)).
To do this you can use a `.env` file and `uv run --env-file .env <command to run>`.

Create a `library.json` file and complete it with the desired NFC tags and CDs.
Take a look at `sample_library.json` and the [The library file](#the-library-file) section for more information.

### Usage

Start the jukebox with `uv` and use `--help` to show help message

```shell
uv run jukebox PLAYER_TO_USE READER_TO_USE
```

#### player (`players/utils.py`)

This part allows to play music through a player.
It is used by `app.py` but can be used separately.

Show help message

```shell
uv run player --help
```

Play a specific album

```shell
uv run player sonos play --artist "Your favorite artist" --album "Your favorite album by this artist"
```

Artist and album must be entered in the library's JSON file. This file can be specified with the `--library` parameter.

For the moment, the player can only play music through Sonos speakers.
A "dryrun" player is also available for testing the script without any speakers configured.

#### reader (`readers/utils.py`)

This part allows to read an input like a NFC tag.
It is used by `app.py` but can be used separately, even if it is useless.

Show help message

```shell
uv run reader --help
```

Read an input

```shell
uv run reader nfc
```

For the moment, this part can only works with PN532 NFC reader.
A "dryrun" reader is also available for testing the script without any NFC reader configured.

## Contributing

Contributions are welcome! Feel free to open an issue or a pull request.
