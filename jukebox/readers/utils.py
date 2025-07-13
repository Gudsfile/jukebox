import argparse
import logging
from time import sleep

from .dryrun import DryRunReader
from .reader import Reader

LOGGER = logging.getLogger("jukebox")


def get_reader(reader: str) -> Reader:
    if reader == "dryrun":
        return DryRunReader
    if reader == "nfc":
        try:
            from .nfc import NFCReader

            return NFCReader
        except ModuleNotFoundError as err:
            LOGGER.warning(f"NFC reader not available: {err}")
        except ImportError as err:
            LOGGER.warning(f"NFC reader not available: {err}")
    raise ValueError(f"The `{reader}` reader is not yet implemented.")


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("reader", choices=["dryrun", "nfc"], help="reader to use")
    return parser.parse_args()


def main():
    args = get_args()
    reader = get_reader(args.reader)()
    for i in range(60):
        msg = reader.read()
        if not msg:
            LOGGER.info()
        LOGGER.info(f"Read `{msg}`")
        sleep(0.5)


if __name__ == "__main__":
    main()
