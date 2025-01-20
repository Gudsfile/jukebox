# My jukebox

💿 Play music on speakers using NFC tags.

🚧 For the moment: 
- artist, album and URI must be pre-populated in a JSON file
- only works with Spotify URIs
- only works with Sonos speakers (or a "dryrun" player), but code is designed to be modified to add new ones
- **as soon as** the NFC tag is removed, the music pauses, then resumes when the NFC tag is replaced

💡 Inspired by:
- https://github.com/hankhank10/vinylemulator
- https://github.com/zacharycohn/jukebox

## Notes

The project remains in Python 3.9 to make it easier to use on hardware like raspberry.

## Install

Installing dependencies with [uv](https://github.com/astral-sh/uv)
```shell
uv sync
```

Add `SONOS_HOST` to env with IP address of your Sonos Zone Player. To do this you can use a `.env` and `uv run --env-file .env <command to run>`.

Create a `library.json` file (`cp sample_library.json library.json`) and complete it with the desired artists and albums.

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


## Usage

### player (`players/utils.py`)

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

### nfcreader (`nfcreader.py`)

This script works with an NFC reader like the **PN532** and NFC tags like the **NTAG2xx**.
It is configured according to the [Waveshare PN532 wiki](https://www.waveshare.com/wiki/PN532_NFC_HAT).

Complete the `tags` part of the `library.json` file with each tag id and the expected artist and album.

```json
{
  "library": {…},
  "tags": {
    "ta:g1:id": {"artist": "artist a", "album": "album 1"},
    "ta:g2:id": {"artist": "artist a", "album": "album 2", "shuffle": true},
  }
}
```

Start the script (show help message with `--help`)
```shell
uv run jukebox
```

🎉 By approaching a NFC tag stored in the `library.json` file, you should hear the associated music begin.
