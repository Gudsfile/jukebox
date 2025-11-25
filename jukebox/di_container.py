from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.adapters.outbound.players.dryrun_player_adapter import DryrunPlayerAdapter
from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.adapters.outbound.readers.dryrun_reader_adapter import DryrunReaderAdapter
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent


def build_jukebox(
    library_path: str,
    player_type: str,
    reader_type: str,
    pause_duration: int,
    pause_delay: int,
):
    """
    Build and wire all dependencies for Jukebox.

    Args:
        library_path: Path to library JSON file
        player_type: Type of player ("sonos" or "dryrun")
        reader_type: Type of reader ("nfc" or "dryrun")
        pause_duration: Maximum pause duration in seconds
        pause_delay: Grace period before pausing in seconds

    Returns:
        Tuple of (reader, handle_tag_event_use_case)
    """
    # Outbound adapters
    library = JsonLibraryAdapter(library_path)

    if player_type == "sonos":
        player = SonosPlayerAdapter()
    elif player_type == "dryrun":
        player = DryrunPlayerAdapter()
    else:
        raise ValueError(f"Unknown player type: {player_type}")

    if reader_type == "nfc":
        from jukebox.adapters.outbound.readers.nfc_reader_adapter import NfcReaderAdapter

        reader = NfcReaderAdapter()
    elif reader_type == "dryrun":
        reader = DryrunReaderAdapter()
    else:
        raise ValueError(f"Unknown reader type: {reader_type}")

    # Use cases
    determine_action = DetermineAction(
        pause_delay=pause_delay,
        max_pause_duration=pause_duration,
    )

    handle_tag_event = HandleTagEvent(
        player=player,
        library=library,
        determine_action=determine_action,
    )

    return reader, handle_tag_event
