#!python
import argparse
import json
import os
from pprint import pprint

from soco import SoCo
from soco.plugins.sharelink import ShareLinkPlugin


def play(sharelink: ShareLinkPlugin, uri: str, shuffle: bool):
    sharelink.soco.clear_queue()
    _ = sharelink.add_share_link_to_queue(uri, position=1)
    if shuffle:
        sharelink.soco.play_mode = "SHUFFLE_NOREPEAT"
    else:
        sharelink.soco.play_mode = "NORMAL"
    sharelink.soco.play_from_queue(index=0, start=True)


def stop(speaker: SoCo):
    speaker.clear_queue()


def create_speaker(host: str):
    sonos = SoCo(host)
    sharelink = ShareLinkPlugin(sonos)
    return sharelink


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--library", default="library.json", help="path to the library JSON file")
    subparsers = parser.add_subparsers(required=True, dest="command", help="subcommands")
    play_parser = subparsers.add_parser("play", help="play specific songs")
    play_parser.add_argument("--artist", required=True, help="specify the artist name to play")
    play_parser.add_argument("--album", required=True, help="specify the album name to play")
    play_parser.add_argument("--shuffle", action="store_true", help="turns on shuffle")
    _ = subparsers.add_parser("list", help="list library contents")
    _ = subparsers.add_parser("stop", help="stop music and clear queue")
    return parser.parse_args()


def get_env():
    sonos_host = os.environ.get("SONOS_HOST")
    if sonos_host is None:
        print("env var `SONOS_HOST` is required")
        exit(1)
    return sonos_host


def main():
    args = get_args()
    library = json.load(open(args.library, "r", encoding="utf-8"))["library"]
    match args.command:
        case "list":
            pprint(library)
        case "play":
            sonos_host = get_env()
            sharelink = create_speaker(sonos_host)
            uri = library[args.artist][args.album]
            play(sharelink, uri, args.shuffle)
        case "stop":
            sonos_host = get_env()
            sharelink = create_speaker(sonos_host)
            stop(sharelink.soco)
        case _:
            print(f"{args.command} command not implemented yet")


if __name__ == "__main__":
    main()
