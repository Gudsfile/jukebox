#!python
import argparse
import json
import os
from pprint import pprint

from soco import SoCo
from soco.plugins.sharelink import ShareLinkPlugin


def play(sharelink, uri):
    sharelink.soco.clear_queue()
    _ = sharelink.add_share_link_to_queue(uri, position=1, as_next=True)
    sharelink.soco.play_from_queue(index=0, start=True)


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--library", default="library.json", help="path to the library JSON file")
    subparsers = parser.add_subparsers(required=True, dest="command", help="subcommands")
    play_parser = subparsers.add_parser("play", help="play specific songs")
    play_parser.add_argument("--artist", required=True, help="specify the artist name to play")
    play_parser.add_argument("--album", required=True, help="specify the album name to play")
    _ = subparsers.add_parser("list", help="list library contents")
    return parser.parse_args()


def get_env():
    sonos_host = os.environ.get("SONOS_HOST")
    if sonos_host is None:
        print("env var `SONOS_HOST` is required")
        exit(1)
    return sonos_host


def main():
    args = get_args()
    library = json.load(open(args.library, "r", encoding="utf-8"))
    match args.command:
        case "list":
            pprint(library)
        case "play":
            sonos_host = get_env()
            uri = library[args.artist][args.album]
            sonos = SoCo(sonos_host)
            sharelink = ShareLinkPlugin(sonos)
            play(sharelink, uri)


if __name__ == "__main__":
    main()
