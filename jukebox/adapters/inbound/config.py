import argparse
from typing import Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel

from jukebox.shared.config_utils import add_verbose_arg, add_version_arg


class JukeboxCliConfig(BaseModel):
    library: Optional[str] = None
    verbose: bool = False
    player: Optional[Literal["dryrun", "sonos"]] = None
    reader: Optional[Literal["dryrun", "nfc"]] = None
    sonos_host: Optional[str] = None
    sonos_name: Optional[str] = None
    pause_duration_seconds: Optional[int] = None
    pause_delay_seconds: Optional[float] = None


def parse_config() -> JukeboxCliConfig:
    parser = argparse.ArgumentParser(
        prog="jukebox",
        description="Play music on speakers using NFC tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l",
        "--library",
        default=None,
        help="override the library JSON path for this process",
    )
    add_verbose_arg(parser)
    add_version_arg(parser)

    parser.add_argument("positional_player", nargs="?", choices=["dryrun", "sonos"], help="override the player type")
    parser.add_argument("positional_reader", nargs="?", choices=["dryrun", "nfc"], help="override the reader type")

    parser.add_argument(
        "--player",
        choices=["dryrun", "sonos"],
        default=None,
        help="override the player type without providing both positional type arguments",
    )
    parser.add_argument(
        "--reader",
        choices=["dryrun", "nfc"],
        default=None,
        help="override the reader type without providing both positional type arguments",
    )

    sonos_target_group = parser.add_mutually_exclusive_group()
    sonos_target_group.add_argument(
        "--sonos-host",
        default=None,
        help="override the Sonos host for this process",
    )
    sonos_target_group.add_argument(
        "--sonos-name",
        default=None,
        help="override the Sonos speaker name for this process",
    )

    parser.add_argument(
        "--pause-duration",
        default=None,
        type=int,
        help="override the maximum duration of a pause in seconds before resetting the queue",
    )
    parser.add_argument(
        "--pause-delay",
        default=None,
        type=float,
        help="override the grace period in seconds before pausing when a tag is removed",
    )

    args = parser.parse_args()

    return JukeboxCliConfig(
        library=args.library,
        verbose=args.verbose,
        player=args.player or args.positional_player,
        reader=args.reader or args.positional_reader,
        sonos_host=args.sonos_host,
        sonos_name=args.sonos_name,
        pause_duration_seconds=args.pause_duration,
        pause_delay_seconds=args.pause_delay,
    )
