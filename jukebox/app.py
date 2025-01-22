import argparse
import json
from time import sleep
from typing import Union

from dotenv import load_dotenv

from .players import Player, get_player
from .readers import Reader, get_reader

DEFAULT_PAUSE_DURATION = 900


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--library", default="library.json", help="path to the library JSON file")
    parser.add_argument("player", choices=["dryrun", "sonos"], help="player to use")
    parser.add_argument("reader", choices=["dryrun", "nfc"], help="reader to use")
    parser.add_argument(
        "--pause-duration",
        default=DEFAULT_PAUSE_DURATION,
        help="specify the maximum duration of a pause in seconds before resetting the queue",
    )
    return parser.parse_args()


def load_library(path: str):
    return json.load(open(path, "r", encoding="utf-8"))


def determine_action(
    current_tag: Union[str, None],
    previous_tag: Union[str, None],
    awaiting_seconds: float,
    max_pause_duration: int,
):
    is_detecting_tag = current_tag is not None
    is_same_tag_has_the_previous = current_tag == previous_tag
    is_paused = awaiting_seconds > 0
    is_acceptable_pause_duration = awaiting_seconds < max_pause_duration

    if is_detecting_tag and is_same_tag_has_the_previous and not is_paused:
        return "continue"
    elif is_detecting_tag and is_same_tag_has_the_previous and is_paused and is_acceptable_pause_duration:
        return "resume"
    elif is_detecting_tag:
        return "play"
    elif not is_detecting_tag and not is_same_tag_has_the_previous and not is_paused and is_acceptable_pause_duration:
        return "pause"
    elif not is_detecting_tag and not is_same_tag_has_the_previous and not is_acceptable_pause_duration:
        return "stop"
    else:
        return "idle"


def actions_loop(reader: Reader, player: Player, library: dict, pause_duration: int):
    last_uid = None
    awaiting_seconds = 0.0
    while True:
        uid = reader.read()
        action = determine_action(uid, last_uid, awaiting_seconds, pause_duration)
        print(f"{action} \t\t {uid} | {last_uid} | {awaiting_seconds} | {pause_duration}")
        if action == "continue":
            pass
        elif action == "resume":
            player.resume()
            awaiting_seconds = 0
        elif action == "play":
            last_uid = uid
            print(f"Found card with UID: {uid}")
            metadata = library["tags"].get(uid)
            if metadata is not None:
                print(f"Found corresponding metadata: {metadata}")
                uri = library["library"][metadata["artist"]][metadata["album"]]
                shuffle = metadata.get("shuffle", False)
                print(f"Found corresponding URI: {uri}")
                player.play(uri, shuffle)
                awaiting_seconds = 0
            else:
                print(f"No URI found for UID: {uid}")
        elif action == "pause":
            player.pause()
            awaiting_seconds += 1
        elif action == "stop":
            player.stop()
            last_uid = None
        elif action == "idle":
            if awaiting_seconds < pause_duration:
                awaiting_seconds += 1
        else:
            print(f"`{action}` action is not implemented yet")
        sleep(0.5)


def main():
    load_dotenv()
    args = get_args()
    library = load_library(args.library)
    player = get_player(args.player)()
    reader = get_reader(args.reader)()
    actions_loop(reader, player, library, args.pause_duration)


if __name__ == "__main__":
    main()
