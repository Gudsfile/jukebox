import argparse
import json
from time import sleep

from app import create_speaker, get_env, pause, play, resume, stop

DEFAULT_PAUSE_DURATION = 900


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--library", default="library.json", help="path to the library JSON file")
    parser.add_argument(
        "--pause-duration",
        default=DEFAULT_PAUSE_DURATION,
        help="specify the maximum duration of a pause in seconds before resetting the queue",
    )
    return parser.parse_args()


def determine_action(
    current_tag: str | None,
    previous_tag: str | None,
    awaiting_seconds: float,
    max_pause_duration: int,
):
    is_detecting_tag = current_tag is not None
    is_same_tag_has_the_previous = current_tag == previous_tag
    is_paused = awaiting_seconds > 0
    is_acceptable_pause_duration = awaiting_seconds < max_pause_duration

    match is_detecting_tag, is_same_tag_has_the_previous, is_paused, is_acceptable_pause_duration:
        case True, True, False, _:
            return "continue"
        case True, True, True, True:
            return "resume"
        case True, _, _, _:
            return "play"
        case False, False, False, True:
            return "pause"
        case False, False, _, False:
            return "stop"
        case _, _, _, _:
            return "idle"


def main():
    args = get_args()
    library = json.load(open(args.library, "r", encoding="utf-8"))
    sonos = create_speaker(get_env())

    last_rawuid = None
    awaiting_seconds = 0.0
    while True:
        rawuid = input("Enter UID: ")
        rawuid = rawuid.strip() if rawuid else None
        action = determine_action(rawuid, last_rawuid, awaiting_seconds, args.pause_duration)
        match action:
            case "continue":
                print("c", end="")
            case "resume":
                print("r", end="")
                resume(sonos.soco)
            case "play":
                print("P", end="")
                uid = rawuid
                print(f"Found card with UID: {uid}")
                metadata = library["tags"].get(uid)
                if metadata is not None:
                    print(f"Found corresponding metadata: {metadata}")
                    uri = library["library"][metadata["artist"]][metadata["album"]]
                    shuffle = metadata.get("shuffle", False)
                    print(f"Found corresponding URI: {uri}")
                    play(sonos, uri, shuffle)
                else:
                    print(f"Unknown URI found for UID: {uid}")
            case "pause":
                print("p", end="")
                pause(sonos.soco)
                awaiting_seconds = 0
            case "stop":
                print("s")
                stop(sonos.soco)
            case "idle":
                print(".", end="")
                if awaiting_seconds < args.pause_duration:
                    awaiting_seconds += 1
            case _:
                print(f"`{action}` action is not implemented yet")
        sleep(0.5)
        awaiting_seconds += 0.5


if __name__ == "__main__":
    main()
