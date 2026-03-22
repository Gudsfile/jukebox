from jukebox.adapters.inbound.config import parse_config


def main():
    config = parse_config()

    from jukebox.shared.logger import set_logger

    set_logger("jukebox", config.verbose)

    from jukebox.di_container import build_jukebox

    reader, handle_tag_event = build_jukebox(config)

    from jukebox.adapters.inbound.cli_controller import CLIController

    controller = CLIController(reader=reader, handle_tag_event=handle_tag_event)
    controller.run()


if __name__ == "__main__":
    main()
