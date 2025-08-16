import argparse
import json
import logging
import os
from typing import Type

from .dryrun import DryRunPlayer
from .player import Player
from .sonos import SonosPlayer


def get_player(player: str) -> Type[Player]:
    if player == "dryrun":
        return DryRunPlayer
    elif player == "sonos":
        return SonosPlayer
    raise ValueError(f"The `{player}` player is not yet implemented.")


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-l",
        "--library",
        default=os.environ.get("JUKEBOX_LIBRARY_PATH", os.path.expanduser("~/.jukebox/library.json")),
        help="path to the library JSON file",
    )
    parser.add_argument("player", choices=["dryrun", "sonos"], help="player to use")
    subparsers = parser.add_subparsers(required=True, dest="command", help="subcommands")
    play_parser = subparsers.add_parser("play", help="play specific songs")
    play_parser.add_argument("tag_uid", help="specify the tag_uid of the CD to play")
    _ = subparsers.add_parser("stop", help="stop music and clear queue")
    parser.add_argument("--host", default=None, help="specify the host to use for the player")
    return parser.parse_args()


def main():
    args = get_args()

    level = logging.INFO
    logger = logging.getLogger("jukebox")
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    discs = json.load(open(args.library, "r", encoding="utf-8"))["discs"]
    player_class = get_player(args.player)
    player = player_class(host=args.host)
    if args.command == "play":
        if args.tag_uid in discs:
            disc = discs[args.tag_uid]
            player.play(disc["uri"], disc.get("option", {}).get("shuffle", False))
        else:
            logger.warning(f"Uknown tag_uid: {args.tag_uid}")
    elif args.command == "stop":
        player.stop()
    else:
        logger.warning(f"Comment not implemented yet: `{args.command}`")


if __name__ == "__main__":
    main()
