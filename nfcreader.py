import argparse
import json
from time import sleep

import RPi.GPIO as GPIO

from app import create_speaker, get_env, play, stop
from pn532 import PN532_SPI


def create_reader():
    pn532 = PN532_SPI(debug=False, reset=20, cs=4)
    ic, ver, rev, support = pn532.get_firmware_version()
    print(f"Found PN532 with firmware version: {ver}.{rev}")
    pn532.SAM_configuration()
    return pn532


def parse_rawuid(rawuid):
    uid = ""
    for i in rawuid:
        bit = str(hex(i)).lower()[2:]
        if len(bit) == 1:
            bit = "0" + bit
        uid += bit + ":"
    return uid[:-1]


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--library", default="library.json", help="path to the library JSON file")
    return parser.parse_args()


def main():
    args = get_args()
    library = json.load(open(args.library, "r", encoding="utf-8"))
    sonos = create_speaker(get_env())
    pn532 = create_reader()

    last_rawuid = None
    while True:
        rawuid = pn532.read_passive_target(timeout=0.5)
        if rawuid is None and last_rawuid is not None:
            print("s")
            last_rawuid = None
            stop(sonos.soco)
        elif rawuid is None:
            # print(".", end="")
            sleep(0.2)
        elif rawuid is not None and rawuid == last_rawuid:
            print("p", end="")
        elif rawuid is not None and rawuid != last_rawuid:
            last_rawuid = rawuid
            uid = parse_rawuid(rawuid)
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


if __name__ == "__main__":
    main()
