import logging

from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.adapters.inbound.config import parse_config
from jukebox.di_container import build_jukebox

LOGGER = logging.getLogger("jukebox")


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
    config = parse_config()
    set_logger(config.verbose)

    reader, handle_tag_event = build_jukebox(config)

    controller = CLIController(reader=reader, handle_tag_event=handle_tag_event)
    controller.run()


if __name__ == "__main__":
    main()
