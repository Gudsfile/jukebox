import argparse
import json
import logging
from pprint import pprint

from .dryrun import DryRunPlayer
from .player import Player
from .sonos import SonosPlayer

LOGGER = logging.getLogger("jukebox")


def get_player(player: str) -> Player:
    if player == "dryrun":
        return DryRunPlayer
    elif player == "sonos":
        return SonosPlayer
    raise ValueError(f"The `{player}` player is not yet implemented.")


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--library", default="library.json", help="path to the library JSON file")
    parser.add_argument("player", choices=["dryrun", "sonos"], help="player to use")
    subparsers = parser.add_subparsers(required=True, dest="command", help="subcommands")
    play_parser = subparsers.add_parser("play", help="play specific songs")
    play_parser.add_argument("--artist", required=True, help="specify the artist name to play")
    play_parser.add_argument("--album", required=True, help="specify the album name to play")
    play_parser.add_argument("--shuffle", action="store_true", help="turns on shuffle")
    _ = subparsers.add_parser("list", help="list library contents")
    _ = subparsers.add_parser("stop", help="stop music and clear queue")
    parser.add_argument("--host", default=None, help="specify the host to use for the player")
    return parser.parse_args()


def main():
    args = get_args()
    library = json.load(open(args.library, "r", encoding="utf-8"))["library"]
    if args.command == "list":
        pprint(library)
    elif args.command == "play":
        player_class = get_player(args.player)
        player = player_class(host=args.host)
        uri = library[args.artist][args.album]
        player.play(uri, args.shuffle)
    elif args.command == "stop":
        player_class = get_player(args.player)
        player = player_class(host=args.host)
        player.stop()
    else:
        LOGGER.warning(f"`{args.command}` command not implemented yet")


if __name__ == "__main__":
    main()
