import argparse
import json
import logging
import os
from time import sleep
from typing import Union

from .players import Player, get_player
from .readers import Reader, get_reader

DEFAULT_LIBRARY_PATH = os.path.expanduser("~/.jukebox/library.json")
DEFAULT_PAUSE_DURATION = 900

LOGGER = logging.getLogger("jukebox")

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version

try:
    __version__ = version("gukebox")
except PackageNotFoundError:
    __version__ = "unknown"


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-l",
        "--library",
        default=os.environ.get("JUKEBOX_LIBRARY_PATH", DEFAULT_LIBRARY_PATH),
        help="path to the library JSON file",
    )
    parser.add_argument("player", choices=["dryrun", "sonos"], help="player to use")
    parser.add_argument("reader", choices=["dryrun", "nfc"], help="reader to use")
    parser.add_argument(
        "--pause-duration",
        default=DEFAULT_PAUSE_DURATION,
        type=int,
        help="specify the maximum duration of a pause in seconds before resetting the queue",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show more details")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}", help="show current installed version"
    )
    return parser.parse_args()


def set_logger(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("jukebox")
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def load_library(path: str):
    try:
        library = json.load(open(path, "r", encoding="utf-8"))
        return library
    except FileNotFoundError as err:
        LOGGER.error(
            f"Library file not found at `{path}`, place the file at `{DEFAULT_LIBRARY_PATH}` or choose another path with env variable `JUKEBOX_LIBRARY_PATH` or argument `--library`"
        )
        raise err


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
        LOGGER.debug(f"{action} \t\t {uid} | {last_uid} | {awaiting_seconds} | {pause_duration}")
        if action == "continue":
            pass
        elif action == "resume":
            player.resume()
            awaiting_seconds = 0
        elif action == "play":
            last_uid = uid
            LOGGER.info(f"Found card with UID: {uid}")
            disc = library.get(uid)
            if disc is not None:
                LOGGER.info(f"Found corresponding disc: {disc}")
                uri = disc["uri"]
                shuffle = disc.get("option", {"shuffle": False}).get("shuffle", False)
                player.play(uri, shuffle)
                awaiting_seconds = 0
            else:
                LOGGER.warning(f"No disc found for UID: {uid}")
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
            LOGGER.info(f"`{action}` action is not implemented yet")
        sleep(0.5)


def main():
    args = get_args()
    set_logger(args.verbose)
    library = load_library(args.library)["discs"]
    player = get_player(args.player)()
    reader = get_reader(args.reader)()
    actions_loop(reader, player, library, args.pause_duration)


if __name__ == "__main__":
    main()
