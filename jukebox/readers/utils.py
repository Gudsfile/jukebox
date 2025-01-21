import argparse
from time import sleep

from jukebox.readers.dryrun import DryRunReader
from jukebox.readers.reader import Reader


def get_reader(reader: str) -> Reader:
    if reader == "dryrun":
        return DryRunReader
    if reader == "nfc":
        try:
            from jukebox.readers.nfc import NFCReader

            return NFCReader
        except ImportError as err:
            print(f"nfc reader not available: {err}")
            exit(1)
        except ModuleNotFoundError as err:
            print(f"nfc reader not available: {err}")
    raise ValueError(f"Unknown reader: {reader}")


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
            print()
        print(f"read `{msg}`")
        sleep(0.5)


if __name__ == "__main__":
    main()
