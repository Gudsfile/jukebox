# My jukebox

💿 Play music on speakers using NFC tags.

🚧 At the moment:
- artist, album and URI must be pre-populated in a JSON file (supports playlists via a workaround)
- supports many music providers (Spotify, Apple Music, etc.), just add the URIs to the JSON file
- only works with Sonos speakers (or a "dryrun" player), but code is designed to be modified to add new ones
- **as soon as** the NFC tag is removed, the music pauses, then resumes when the NFC tag is replaced

💡 Inspired by:
- https://github.com/hankhank10/vinylemulator
- https://github.com/zacharycohn/jukebox

📋 Table of contents:
- [Install](#install)
- [Usage](#usage)
- [Avaible players and readers](#avaible-players-and-readers)
  - [Readers](#readers)
  - [Players](#players)
- [The library file](#the-library-file)
- [Developer setup](#developer-setup)

## Notes

The project remains in Python 3.7 to make it easier to use on hardware like Raspberry Pi.

## Install

Install the package from the pre-built available on the [releases page](https://github.com/Gudsfile/jukebox/releases)
```shell
pip3 install https://github.com/Gudsfile/jukebox/releases/latest/download/jukebox-0.1.0.tar.gz
```
The `jukebox-0.1.0.tar.gz` is for now fixed to the version `0.1.0`, don't change it. Use `pip3 install https://github.com/Gudsfile/jukebox/releases/download/vX.Y.Z/jukebox-0.1.0.tar.gz` if you want a precise version.

Create a `library.json` file and complete it with the desired artists and albums.
Complete the `tags` part of the `library.json` file with each tag id and the expected artist and album.
Take a look at `sample_library.json` and the [The library file](#the-library-file) section for more information.

Set the `SONOS_HOST` environment variable with the IP address of your Sonos Zone Player (see [Available players and readers](#available-players-and-readers)).

## Usage

Start the jukebox with the `jukebox` command (show help message with `--help`)
```shell
jukebox PLAYER_TO_USE READER_TO_USE -l YOUR_LIBRARY_FILE
```

🎉 With choosing the `sonos` player and `nfc` reader, by approaching a NFC tag stored in the `library.json` file, you should hear the associated music begins.

## Avaible players and readers

### Readers

**Dry run** (`dryrun`)
Read an input that does nothing.

**NFC** (`nfc`)
Read an NFC tag and get its UID.
This project works with an NFC reader like the **PN532** and NFC tags like the **NTAG2xx**.
It is configured according to the [Waveshare PN532 wiki](https://www.waveshare.com/wiki/PN532_NFC_HAT).

### Players

**Dry run** (`dryrun`)
Play music through a speaker that does nothing.

**Sonos** (`sonos`)
Play music through a Sonos speaker.
`SONOS_HOST` environment variable must be set with the IP address of your Sonos Zone Player.
You could set the environment varible with `export SONOS_HOST=192.168.0.???` to use this speaker through the `jukebox` command.
Or set it in a `.env` file to use the `uv run --env-file .env <command to run>` version.

## The library file

The `library.json` file is a JSON file that contains the artists, albums and tags.
It is used by the `jukebox` command to find the corresponding metadata for each tag.

```json
{
  "library": {
    "artist a": {
        "album 1": "uri",
        "album 2": "uri"
    },
    "artist b": {
        "album 2": "uri"
    }
  },
  "tags": {…}
}
```

The `library` part is a dictionary containing artists as keys.
Each artist is a dictionary containing albums as keys and URIs as values.
URIs are the URIs of the music providers (Spotify, Apple Music, etc.).

The `tags` part is a dictionary that contains the tags UIDs as keys and the corresponding metadata as values.
Metadata contains the artist and album names.

For example, if you have the following `library.json` file:

```json
{
  "library": {
    "artist a": {
        "album 1": "uri",
        "album 2": "uri"
    },
    "artist b": {
        "album 2": "uri"
    }
  },
  "tags": {
    "ta:g1:id": {"artist": "artist a", "album": "album 1"},
    "ta:g2:id": {"artist": "artist a", "album": "album 2", "shuffle": true},
  }
}
```

Then, the jukebox will find the metadata for the tag `ta:g1:id` and play the corresponding album.

It is also possible to use the `shuffle` key to play the album in shuffle mode.

💡 You can add `{"playlists": {"playlist-name": "playlist-uri"}}` to the `library` part and configure a tag with `{"artist": "playlists", "album": "playlist-name"}` to allow playing a playlist with the jukebox.

## Developer setup

### Install

Clone the project.

Installing dependencies with [uv](https://github.com/astral-sh/uv)
```shell
uv sync
```

Set the `SONOS_HOST` environment variable with the IP address of your Sonos Zone Player (see [Available players and readers](#available-players-and-readers)).
To do this you can use a `.env` file and `uv run --env-file .env <command to run>`.

Create a `library.json` file and complete it with the desired artists and albums.
Complete the `tags` part of the `library.json` file with each tag id and the expected artist and album.
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
