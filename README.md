# My jukebox

CLI to play an album through Sonos speakers.

🎯 The aim is to be able to play music on speakers using NFC tags.

🚧 For the moment: 
- artist, album and URI must be pre-populated in a JSON file
- only works with Spotify URIs

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

## Usage

Show help message
```shell
poetry run python app.py --help
```

Play a specific album
```shell
poetry run python app.py play --artist "Your favorite artist" --album "Your favorite album by this artist"
```
Artist and album must be entered in the library's JSON file. This file can be specified with the `--library` parameter.
