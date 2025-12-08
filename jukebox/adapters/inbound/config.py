import argparse
import logging
import os
from typing import Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ValidationError

DEFAULT_LIBRARY_PATH = os.path.expanduser("~/.jukebox/library.json")
DEFAULT_PAUSE_DURATION = 900
DEFAULT_PAUSE_DELAY = 1

LOGGER = logging.getLogger("jukebox")

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version

try:
    __version__ = version("gukebox")
except PackageNotFoundError:
    __version__ = "unknown"


class DryrunPlayerConfig(BaseModel):
    type: Literal["dryrun"]


class SonosPlayerConfig(BaseModel):
    type: Literal["sonos"]
    host: str


class DryrunReaderConfig(BaseModel):
    type: Literal["dryrun"]


class NfcReaderConfig(BaseModel):
    type: Literal["nfc"]


class PlaybackConfig(BaseModel):
    pause_duration: int = DEFAULT_PAUSE_DURATION
    pause_delay: int = DEFAULT_PAUSE_DELAY


class JukeboxConfig(BaseModel):
    library: str
    verbose: bool = False
    player: Union[DryrunPlayerConfig, SonosPlayerConfig]
    reader: Union[DryrunReaderConfig, NfcReaderConfig]
    playback: PlaybackConfig


def get_library_path() -> str:
    deprecated_library_path = os.environ.get("LIBRARY_PATH")
    if deprecated_library_path:
        LOGGER.warning("The LIBRARY_PATH environment variable is deprecated, use JUKEBOX_LIBRARY_PATH instead.")
    return os.environ.get("JUKEBOX_LIBRARY_PATH", deprecated_library_path or DEFAULT_LIBRARY_PATH)


def get_sonos_host() -> str:
    deprecated_sonos_host = os.environ.get("SONOS_HOST")
    if deprecated_sonos_host:
        LOGGER.warning("The SONOS_HOST environment variable is deprecated, use JUKEBOX_SONOS_HOST instead.")
    return os.environ.get("JUKEBOX_SONOS_HOST", deprecated_sonos_host)


def parse_config() -> JukeboxConfig:
    parser = argparse.ArgumentParser(
        prog="jukebox",
        description="Play music on speakers using NFC tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Global arguments
    parser.add_argument(
        "-l",
        "--library",
        default=get_library_path(),
        help="path to the library JSON file",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}", help="show current installed version"
    )

    # Player and reader types
    parser.add_argument("player", choices=["dryrun", "sonos"], help="player type to use")
    parser.add_argument("reader", choices=["dryrun", "nfc"], help="reader type to use")

    # Player-specific arguments
    parser.add_argument(
        "--sonos-host",
        default=get_sonos_host(),
        help="IP address or hostname of Sonos speaker (required for sonos player)",
    )

    # Playback arguments
    parser.add_argument(
        "--pause-duration",
        default=DEFAULT_PAUSE_DURATION,
        type=int,
        help="maximum duration of a pause in seconds before resetting the queue",
    )
    parser.add_argument(
        "--pause-delay",
        default=DEFAULT_PAUSE_DELAY,
        type=int,
        help="grace period in seconds before pausing when tag is removed (prevents accidental pauses)",
    )

    args = parser.parse_args()

    # Build player config based on type
    if args.player == "dryrun":
        player_config = DryrunPlayerConfig(type="dryrun")
    elif args.player == "sonos":
        if not args.sonos_host:
            parser.error("Sonos player requires --sonos-host argument or JUKEBOX_SONOS_HOST environment variable")
        player_config = SonosPlayerConfig(type="sonos", host=args.sonos_host)
    else:
        parser.error(f"Unknown player type: {args.player}")

    # Build reader config based on type
    if args.reader == "dryrun":
        reader_config = DryrunReaderConfig(type="dryrun")
    elif args.reader == "nfc":
        reader_config = NfcReaderConfig(type="nfc")
    else:
        parser.error(f"Unknown reader type: {args.reader}")

    # Build playback config
    playback_config = PlaybackConfig(
        pause_duration=args.pause_duration,
        pause_delay=args.pause_delay,
    )

    # Build and validate final config
    try:
        config = JukeboxConfig(
            library=args.library,
            verbose=args.verbose,
            player=player_config,
            reader=reader_config,
            playback=playback_config,
        )
    except ValidationError as err:
        LOGGER.error(f"Configuration validation error: {err}")
        parser.exit(status=1, message=f"Configuration error: {err}\n")

    return config
