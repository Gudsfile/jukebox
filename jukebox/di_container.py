from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.adapters.outbound.players.dryrun_player_adapter import DryrunPlayerAdapter
from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.adapters.outbound.readers.dryrun_reader_adapter import DryrunReaderAdapter
from jukebox.adapters.outbound.text_current_tag_adapter import TextCurrentTagAdapter
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.shared.config_utils import get_current_tag_path


def build_jukebox(config: ResolvedJukeboxRuntimeConfig):
    """Build and wire all dependencies for Jukebox."""

    library = JsonLibraryAdapter(config.library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(config.library_path))

    if config.player_type == "sonos":
        player = SonosPlayerAdapter(host=config.sonos_host, name=config.sonos_name, group=config.sonos_group)
    elif config.player_type == "dryrun":
        player = DryrunPlayerAdapter()
    else:
        raise ValueError(f"Unknown player type: {config.player_type}")

    if config.reader_type == "nfc":
        from jukebox.adapters.outbound.readers.nfc_reader_adapter import NfcReaderAdapter

        reader = NfcReaderAdapter(read_timeout_seconds=config.nfc_read_timeout_seconds)
    elif config.reader_type == "dryrun":
        reader = DryrunReaderAdapter()
    else:
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
