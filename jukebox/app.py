from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.adapters.inbound.config import parse_config
from jukebox.di_container import build_jukebox
from jukebox.shared.logger import set_logger


def main():
    config = parse_config()
    set_logger("jukebox", config.verbose)

    reader, handle_tag_event = build_jukebox(config)

    controller = CLIController(reader=reader, handle_tag_event=handle_tag_event)
    controller.run()


if __name__ == "__main__":
    main()
