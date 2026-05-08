from typing import Literal

from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.adapters.outbound.players.dryrun_player_adapter import DryrunPlayerAdapter
from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.adapters.outbound.readers.dryrun_reader_adapter import DryrunReaderAdapter
from jukebox.adapters.outbound.sonos_discovery_adapter import SoCoSonosDiscoveryAdapter
from jukebox.adapters.outbound.text_current_tag_adapter import TextCurrentTagAdapter
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService as SettingsServiceImpl
from jukebox.settings.resolve import build_environment_settings_overrides
from jukebox.settings.runtime_resolver import JukeboxRuntimeResolver
from jukebox.settings.service_protocols import SettingsService
from jukebox.shared.config_utils import get_current_tag_path
from jukebox.sonos.service import DefaultSonosService


def build_settings_service(
    library: str | None = None,
    player: Literal["dryrun", "sonos"] | None = None,
    reader: Literal["dryrun", "pn532"] | None = None,
    sonos_host: str | None = None,
    sonos_name: str | None = None,
    pause_duration_seconds: int | None = None,
    pause_delay_seconds: float | None = None,
    pn532_spi_reset: int | None = None,
    pn532_spi_cs: int | None = None,
    pn532_spi_irq: int | None = None,
) -> SettingsServiceImpl:
    cli_overrides: dict = {}

    if library is not None:
        cli_overrides.setdefault("paths", {})["library_path"] = library

    if player is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("player", {})["type"] = player

    if reader is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("reader", {})["type"] = reader

    if sonos_host is not None:
        sonos_overrides = cli_overrides.setdefault("jukebox", {}).setdefault("player", {}).setdefault("sonos", {})
        sonos_overrides["manual_host"] = sonos_host
        sonos_overrides["manual_name"] = None
        sonos_overrides["selected_group"] = None

    if sonos_name is not None:
        sonos_overrides = cli_overrides.setdefault("jukebox", {}).setdefault("player", {}).setdefault("sonos", {})
        sonos_overrides["manual_host"] = None
        sonos_overrides["manual_name"] = sonos_name
        sonos_overrides["selected_group"] = None

    if pause_duration_seconds is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("playback", {})["pause_duration_seconds"] = (
            pause_duration_seconds
        )

    if pause_delay_seconds is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("playback", {})["pause_delay_seconds"] = pause_delay_seconds

    if pn532_spi_reset is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("reader", {}).setdefault("pn532", {}).setdefault("spi", {})[
            "reset"
        ] = pn532_spi_reset

    if pn532_spi_cs is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("reader", {}).setdefault("pn532", {}).setdefault("spi", {})[
            "cs"
        ] = pn532_spi_cs

    if pn532_spi_irq is not None:
        cli_overrides.setdefault("jukebox", {}).setdefault("reader", {}).setdefault("pn532", {}).setdefault("spi", {})[
            "irq"
        ] = pn532_spi_irq

    return SettingsServiceImpl(
        repository=FileSettingsRepository(),
        env_overrides=build_environment_settings_overrides(),
        cli_overrides=cli_overrides,
    )


def build_runtime_resolver(settings_service: SettingsService) -> JukeboxRuntimeResolver:
    return JukeboxRuntimeResolver(settings_service, DefaultSonosService(SoCoSonosDiscoveryAdapter()))


def build_jukebox(config: ResolvedJukeboxRuntimeConfig):
    """Build and wire all dependencies for Jukebox."""

    library = JsonLibraryAdapter(config.library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(config.library_path))

    match config.player_type:
        case "sonos":
            player = SonosPlayerAdapter(host=config.sonos_host, name=config.sonos_name, group=config.sonos_group)
        case "dryrun":
            player = DryrunPlayerAdapter()
        case _:
            raise ValueError(f"Unknown player type: {config.player_type}")

    match config.reader_type:
        case "pn532":
            from jukebox.adapters.outbound.readers.pn532_reader_adapter import Pn532ReaderAdapter
            from jukebox.pn532.profiles import SpiConnectionParams

            match config.pn532_protocol, config.pn532_connection:
                case "spi", conn if isinstance(conn, SpiConnectionParams):
                    reader = Pn532ReaderAdapter(
                        read_timeout_seconds=config.pn532_read_timeout_seconds,
                        spi_reset=conn.reset,
                        spi_cs=conn.cs,
                        spi_irq=conn.irq,
                    )
                case "spi", conn:
                    raise ValueError(f"Expected SpiConnectionParams for protocol 'spi', got {type(conn).__name__}")
                case _:
                    raise ValueError(f"Unsupported PN532 protocol: {config.pn532_protocol}")
        case "dryrun":
            reader = DryrunReaderAdapter()
        case _:
            raise ValueError(f"Unknown reader type: {config.reader_type}")

    determine_action = DetermineAction(
        pause_delay=config.pause_delay_seconds,
        max_pause_duration=config.pause_duration_seconds,
    )
    determine_current_tag_action = DetermineCurrentTagAction()

    handle_tag_event = HandleTagEvent(
        player=player,
        library=library,
        current_tag_repository=current_tag_repository,
        determine_action=determine_action,
        determine_current_tag_action=determine_current_tag_action,
    )

    return reader, handle_tag_event
