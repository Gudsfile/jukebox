import argparse
import logging
import os
from typing import Optional, Union

try:
    from typing import Annotated, Literal
except ImportError:
    from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from jukebox.shared.config_utils import (
    add_library_arg,
    add_verbose_arg,
    add_version_arg,
)
from jukebox.shared.timing import MIN_PAUSE_DELAY_SECONDS

DEFAULT_PAUSE_DURATION = 900
DEFAULT_PAUSE_DELAY = 0.25

LOGGER = logging.getLogger("jukebox")


class DryrunPlayerConfig(BaseModel):
    type: Literal["dryrun"]


class SonosPlayerConfig(BaseModel):
    type: Literal["sonos"]
    host: Optional[str] = None
    name: Optional[str] = None

    @model_validator(mode="after")
    def host_and_name_are_mutually_exclusive(self) -> "SonosPlayerConfig":
        if self.host and self.name:
            raise ValueError("host and name are mutually exclusive")
        return self


class DryrunReaderConfig(BaseModel):
    type: Literal["dryrun"]


class NfcReaderConfig(BaseModel):
    type: Literal["nfc"]


class PlaybackConfig(BaseModel):
    pause_duration: int = DEFAULT_PAUSE_DURATION
    pause_delay: float = Field(default=DEFAULT_PAUSE_DELAY, ge=MIN_PAUSE_DELAY_SECONDS)


class JukeboxConfig(BaseModel):
    library: str
    verbose: bool = False
    player: Annotated[
        Union[DryrunPlayerConfig, SonosPlayerConfig],
        Field(discriminator="type"),
    ]
    reader: Union[DryrunReaderConfig, NfcReaderConfig]
    playback: PlaybackConfig


def parse_config() -> JukeboxConfig:
    parser = argparse.ArgumentParser(
        prog="jukebox",
        description="Play music on speakers using NFC tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Global arguments
    add_library_arg(parser)
    add_verbose_arg(parser)
    add_version_arg(parser)

    # Player and reader types
    parser.add_argument("player", choices=["dryrun", "sonos"], help="player type to use")
    parser.add_argument("reader", choices=["dryrun", "nfc"], help="reader type to use")

    # Player-specific arguments
    parser.add_argument(
        "--sonos-host",
        default=None,
        help="IP address or hostname of Sonos speaker (env: JUKEBOX_SONOS_HOST, if omitted, auto-discovery is used)",
    )
    parser.add_argument(
        "--sonos-name",
        default=None,
        help="name of the Sonos speaker to use, case-sensitive (env: JUKEBOX_SONOS_NAME, mutually exclusive with --sonos-host)",
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
        type=float,
        help=(
            "grace period in seconds before pausing when tag is removed "
            f"(minimum: {MIN_PAUSE_DELAY_SECONDS:g}s to avoid pausing on brief missed reads)"
        ),
    )

    args = parser.parse_args()

    # Resolve Sonos speaker selection: CLI flags take precedence over env vars.
    env_host = os.environ.get("JUKEBOX_SONOS_HOST") or os.environ.get("SONOS_HOST")
    if os.environ.get("SONOS_HOST") and not os.environ.get("JUKEBOX_SONOS_HOST"):
        LOGGER.warning("The SONOS_HOST environment variable is deprecated, use JUKEBOX_SONOS_HOST instead.")
    env_name = os.environ.get("JUKEBOX_SONOS_NAME")

    sonos_host = args.sonos_host or (env_host if not args.sonos_name else None)
    sonos_name = args.sonos_name or (env_name if not args.sonos_host else None)

    # Build and validate final config
    try:
        if args.player == "dryrun":
            player_config = DryrunPlayerConfig(type="dryrun")
        elif args.player == "sonos":
            player_config = SonosPlayerConfig(type="sonos", host=sonos_host, name=sonos_name)
        else:
            parser.error(f"Unknown player type: {args.player}")

        if args.reader == "dryrun":
            reader_config = DryrunReaderConfig(type="dryrun")
        elif args.reader == "nfc":
            reader_config = NfcReaderConfig(type="nfc")
        else:
            parser.error(f"Unknown reader type: {args.reader}")

        config = JukeboxConfig(
            library=args.library,
            verbose=args.verbose,
            player=player_config,
            reader=reader_config,
            playback=PlaybackConfig(
                pause_duration=args.pause_duration,
                pause_delay=args.pause_delay,
            ),
        )
    except ValidationError as err:
        LOGGER.error(f"Configuration validation error: {err}")
        parser.exit(status=1, message=f"Configuration error: {err}\n")

    return config
