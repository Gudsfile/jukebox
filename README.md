# My jukebox

💿 Play music on speakers using NFC tags.

🚧 For the moment: 
- artist, album and URI must be pre-populated in a JSON file
- only works with Spotify URIs
- as soon as the tag is removed, the music stops and **the position is lost**

💡 Inspired by:
- https://github.com/hankhank10/vinylemulator
- https://github.com/zacharycohn/jukebox

## Install

Installing dependencies with [Poetry](https://python-poetry.org)
```shell
poetry install
```

Add `SONOS_HOST` to env with IP address of your Sonos Zone Player. To do this you can use a `.env` file with [poetry-dotenv-plugin](https://github.com/mpeteuil/poetry-dotenv-plugin)

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

### `app.py`

Show help message
```shell
poetry run python app.py --help
```

Play a specific album
```shell
poetry run python app.py play --artist "Your favorite artist" --album "Your favorite album by this artist"
```
Artist and album must be entered in the library's JSON file. This file can be specified with the `--library` parameter.

### `nfcreader.py`

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
poetry run python nfcreader.py
```

🎉 By approaching a NFC tag stored in the `library.json` file, you should hear the associated music begin.
