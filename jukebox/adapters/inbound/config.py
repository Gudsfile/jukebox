import argparse
from typing import Literal

from pydantic import BaseModel

from jukebox.shared.config_utils import add_verbose_arg, add_version_arg


class JukeboxCliConfig(BaseModel):
    library: str | None = None
    verbose: bool = False
    player: Literal["dryrun", "sonos"] | None = None
    reader: Literal["dryrun", "pn532"] | None = None
    sonos_host: str | None = None
    sonos_name: str | None = None
    pause_duration_seconds: int | None = None
    pause_delay_seconds: float | None = None
    pn532_spi_reset: int | None = None
    pn532_spi_cs: int | None = None
    pn532_spi_irq: int | None = None


def parse_config() -> JukeboxCliConfig:
    parser = argparse.ArgumentParser(
        prog="jukebox",
        description="Play music on speakers using NFC tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l",
        "--library",
        default=None,
        help="override the library JSON path for this process",
    )
    add_verbose_arg(parser)
    add_version_arg(parser)

    parser.add_argument(
        "--player",
        choices=["dryrun", "sonos"],
        default=None,
        help="override the player type for this process",
    )
    parser.add_argument(
        "--reader",
        choices=["dryrun", "pn532"],
        default=None,
        help="override the reader type for this process",
    )

    sonos_target_group = parser.add_mutually_exclusive_group()
    sonos_target_group.add_argument(
        "--sonos-host",
        default=None,
        help="override the Sonos host for this process",
    )
    sonos_target_group.add_argument(
        "--sonos-name",
        default=None,
        help="override the Sonos speaker name for this process",
    )

    parser.add_argument(
        "--pause-duration",
        default=None,
        type=int,
        help="override the maximum duration of a pause in seconds before resetting the queue",
    )
    parser.add_argument(
        "--pause-delay",
        default=None,
        type=float,
        help="override the grace period in seconds before pausing when a tag is removed",
    )

    parser.add_argument(
        "--pn532-spi-reset",
        default=None,
        type=int,
        help="override the PN532 SPI reset GPIO pin for this process",
    )
    parser.add_argument(
        "--pn532-spi-cs",
        default=None,
        type=int,
        help="override the PN532 SPI chip select GPIO pin for this process",
    )
    parser.add_argument(
        "--pn532-spi-irq",
        default=None,
        type=int,
        help="override the PN532 SPI IRQ GPIO pin for this process",
    )

    args = parser.parse_args()

    return JukeboxCliConfig(
        library=args.library,
        verbose=args.verbose,
        player=args.player,
        reader=args.reader,
        sonos_host=args.sonos_host,
        sonos_name=args.sonos_name,
        pause_duration_seconds=args.pause_duration,
        pause_delay_seconds=args.pause_delay,
        pn532_spi_reset=args.pn532_spi_reset,
        pn532_spi_cs=args.pn532_spi_cs,
        pn532_spi_irq=args.pn532_spi_irq,
    )
