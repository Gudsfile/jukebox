from jukebox.adapters.inbound.config import (
    DryrunPlayerConfig,
    DryrunReaderConfig,
    JukeboxConfig,
    NfcReaderConfig,
    SonosPlayerConfig,
)
from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.adapters.outbound.players.dryrun_player_adapter import DryrunPlayerAdapter
from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.adapters.outbound.readers.dryrun_reader_adapter import DryrunReaderAdapter
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent


def build_jukebox(config: JukeboxConfig):
    """Build and wire all dependencies for Jukebox.

    Args:
        config: Validated JukeboxConfig instance containing all configuration

    Returns:
        Tuple of (reader, handle_tag_event_use_case)

    Raises:
        ValueError: If config contains unknown player or reader type
    """
    # Outbound adapters
    library = JsonLibraryAdapter(config.library)

    if isinstance(config.player, SonosPlayerConfig):
        player = SonosPlayerAdapter(host=config.player.host)
    elif isinstance(config.player, DryrunPlayerConfig):
        player = DryrunPlayerAdapter()
    else:
        raise ValueError(f"Unknown player type: {config.player.type}")

    if isinstance(config.reader, NfcReaderConfig):
        from jukebox.adapters.outbound.readers.nfc_reader_adapter import NfcReaderAdapter

        reader = NfcReaderAdapter()
    elif isinstance(config.reader, DryrunReaderConfig):
        reader = DryrunReaderAdapter()
    else:
        raise ValueError(f"Unknown reader type: {config.reader.type}")

    # Use cases
    determine_action = DetermineAction(
        pause_delay=config.playback.pause_delay,
        max_pause_duration=config.playback.pause_duration,
    )

    handle_tag_event = HandleTagEvent(
        player=player,
        library=library,
        determine_action=determine_action,
    )

    return reader, handle_tag_event
