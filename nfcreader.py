import argparse
import json
from time import sleep

from app import create_speaker, get_env, pause, play, resume, stop
from pn532 import PN532_SPI

DEFAULT_PAUSE_DURATION = 900


def create_reader():
    pn532 = PN532_SPI(debug=False, reset=20, cs=4)
    ic, ver, rev, support = pn532.get_firmware_version()
    print(f"Found PN532 with firmware version: {ver}.{rev}")
    pn532.SAM_configuration()
    return pn532


def parse_raw_uid(raw: bytearray):
    return ":".join([hex(i)[2:].lower().rjust(2, "0") for i in raw])


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
    pn532 = create_reader()

    last_rawuid = None
    awaiting_seconds = 0.0
    while True:
        rawuid = pn532.read_passive_target(timeout=0.5)
        action = determine_action(rawuid, last_rawuid, awaiting_seconds, args.pause_duration)
        print(f"{action} \t\t {rawuid} | {last_rawuid} | {awaiting_seconds} | {args.pause_duration}")
        match action:
            case "continue":
                pass
            case "resume":
                resume(sonos.soco)
                awaiting_seconds = 0
            case "play":
                uid = parse_raw_uid(rawuid)
                last_rawuid = rawuid
                print(f"Found card with UID: {uid}")
                metadata = library["tags"].get(uid)
                if metadata is not None:
                    print(f"Found corresponding metadata: {metadata}")
                    uri = library["library"][metadata["artist"]][metadata["album"]]
                    shuffle = metadata.get("shuffle", False)
                    print(f"Found corresponding URI: {uri}")
                    play(sonos, uri, shuffle)
                    awaiting_seconds = 0
                else:
                    print(f"No URI found for UID: {uid}")
            case "pause":
                pause(sonos.soco)
                awaiting_seconds += 1
            case "stop":
                stop(sonos.soco)
                last_rawuid = None
            case "idle":
                if awaiting_seconds < args.pause_duration:
                    awaiting_seconds += 1
            case _:
                print(f"`{action}` action is not implemented yet")
        sleep(0.5)


if __name__ == "__main__":
    main()
