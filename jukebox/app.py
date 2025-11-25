import argparse
import logging
import os

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
    parser.add_argument(
        "--pause-delay",
        default=1,
        type=int,
        help="grace period in seconds before pausing when tag is removed (prevents accidental pauses)",
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


def main():
    args = get_args()
    set_logger(args.verbose)

    from .adapters.inbound.cli_controller import CLIController
    from .di_container import build_jukebox

    reader, handle_tag_event = build_jukebox(
        library_path=args.library,
        player_type=args.player,
        reader_type=args.reader,
        pause_duration=args.pause_duration,
        pause_delay=args.pause_delay,
    )

    controller = CLIController(reader=reader, handle_tag_event=handle_tag_event)
    controller.run()


if __name__ == "__main__":
    main()
