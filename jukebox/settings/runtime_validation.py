from typing import Any


def validate_sonos_group_runtime_consistency(
    player_type: str,
    sonos_host: Any,
    sonos_name: Any,
    sonos_group: Any,
) -> None:
    if player_type != "sonos" or sonos_group is None:
        return

    if sonos_name is not None:
        raise ValueError("sonos_name cannot be set when sonos_group is present")

    if sonos_host != sonos_group.coordinator.host:
        raise ValueError("sonos_host must match the resolved Sonos group coordinator host")


def validate_resolved_jukebox_runtime_rules(runtime_config: Any) -> None:
    validate_sonos_group_runtime_consistency(
        runtime_config.player_type,
        runtime_config.sonos_host,
        runtime_config.sonos_name,
        runtime_config.sonos_group,
    )
