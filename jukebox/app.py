import logging

from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.adapters.inbound.config import JukeboxCliConfig, parse_config
from jukebox.di_container import build_jukebox
from jukebox.settings.errors import SettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService, build_environment_settings_overrides
from jukebox.shared.logger import set_logger

LOGGER = logging.getLogger("jukebox")


def _build_settings_service(config: JukeboxCliConfig) -> SettingsService:
    cli_overrides = {}

    if config.library is not None:
        cli_overrides.setdefault("paths", {})["library_path"] = config.library

    if config.player is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("player", {})["type"] = config.player

    if config.reader is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("reader", {})["type"] = config.reader

    if config.sonos_host is not None:
        sonos_overrides = cli_overrides.setdefault("jukebox", {}).setdefault("player", {}).setdefault("sonos", {})
        sonos_overrides["manual_host"] = config.sonos_host
        sonos_overrides["manual_name"] = None
        sonos_overrides["selected_group"] = None

    if config.sonos_name is not None:
        sonos_overrides = cli_overrides.setdefault("jukebox", {}).setdefault("player", {}).setdefault("sonos", {})
        sonos_overrides["manual_host"] = None
        sonos_overrides["manual_name"] = config.sonos_name
        sonos_overrides["selected_group"] = None

    if config.pause_duration_seconds is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("playback", {})["pause_duration_seconds"] = (
            config.pause_duration_seconds
        )

    if config.pause_delay_seconds is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("playback", {})["pause_delay_seconds"] = (
            config.pause_delay_seconds
        )

    return SettingsService(
        repository=FileSettingsRepository(),
        env_overrides=build_environment_settings_overrides(LOGGER.warning),
        cli_overrides=cli_overrides,
    )


def main():
    config = parse_config()
    set_logger("jukebox", config.verbose)

    try:
        settings_service = _build_settings_service(config)
        runtime_config = settings_service.resolve_jukebox_runtime(verbose=config.verbose)
        reader, handle_tag_event = build_jukebox(runtime_config)
    except SettingsError as err:
        raise SystemExit(str(err)) from err

    controller = CLIController(
        reader=reader,
        handle_tag_event=handle_tag_event,
        loop_interval_seconds=runtime_config.loop_interval_seconds,
    )
    controller.run()


if __name__ == "__main__":
    main()
