from importlib import import_module
from typing import Callable, Optional, Protocol

from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.shared.dependency_messages import optional_extra_dependency_message
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import GetSonosSelectionStatus, SaveSonosSelection
from jukebox.sonos.service import SonosService

from .cli_presentation import (
    build_discstore_settings_deprecation_warning,
    render_settings_output,
    render_sonos_selection_saved_output,
    render_sonos_selection_status_output,
    render_sonos_speakers_output,
)
from .commands import (
    ApiCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
    SonosListCommand,
    SonosSelectCommand,
    SonosShowCommand,
    UiCommand,
)
from .services import AdminServices
from .sonos_households import GroupedSonosHousehold, group_sonos_speakers_by_household


class AppController(Protocol):
    app: object


def _raise_optional_extra_error(command_name: str, extra_name: str, source_command: str, err: ModuleNotFoundError):
    raise SystemExit(
        optional_extra_dependency_message(
            subject=f"`{source_command} {command_name}`",
            extra_name=extra_name,
            source_command=f"{source_command} {command_name}",
        )
    ) from err


def _load_uvicorn(command_name: str, extra_name: str, source_command: str):
    try:
        return import_module("uvicorn")
    except ModuleNotFoundError as err:
        if err.name not in (None, "uvicorn"):
            raise
        _raise_optional_extra_error(command_name, extra_name, source_command, err)


def _build_server_app(
    build_app: Callable[[str, AdminServices], AppController],
    library_path: str,
    services: AdminServices,
    command_name: str,
    extra_name: str,
    source_command: str,
):
    try:
        return build_app(library_path, services)
    except ModuleNotFoundError as err:
        if err.name in {"fastapi", "fastui"} or "requires the optional" in str(err):
            _raise_optional_extra_error(command_name, extra_name, source_command, err)
        raise


def execute_settings_command(
    command: object,
    settings_service: SettingsService,
    stdout_fn: Callable[[str], None] = print,
) -> None:
    if isinstance(command, SettingsShowCommand):
        payload = (
            settings_service.get_effective_settings_view()
            if command.effective
            else settings_service.get_persisted_settings_view()
        )
        stdout_fn(render_settings_output(command, payload))
        return

    if isinstance(command, SettingsSetCommand):
        payload = settings_service.set_persisted_value(command.dotted_path, command.value)
        stdout_fn(render_settings_output(command, payload))
        return

    if isinstance(command, SettingsResetCommand):
        payload = settings_service.reset_persisted_value(command.dotted_path)
        stdout_fn(render_settings_output(command, payload))
        return

    raise TypeError("Unsupported settings command")


def execute_sonos_command(
    command: object,
    sonos_service: SonosService,
    settings_service: Optional[SettingsService] = None,
    household_prompt_fn: Optional[Callable[[list[GroupedSonosHousehold]], Optional[str]]] = None,
    speaker_prompt_fn: Optional[Callable[[list[DiscoveredSonosSpeaker]], Optional[list[str]]]] = None,
    coordinator_prompt_fn: Optional[Callable[[list[DiscoveredSonosSpeaker]], Optional[str]]] = None,
    stdout_fn: Callable[[str], None] = print,
    status_fn: Optional[Callable[[str], None]] = None,
) -> None:
    if isinstance(command, SonosListCommand):
        _emit_status(status_fn, "Discovering Sonos speakers...")
        stdout_fn(
            render_sonos_speakers_output(group_sonos_speakers_by_household(sonos_service.list_network_speakers()))
        )
        return

    if isinstance(command, SonosSelectCommand):
        if settings_service is None:
            raise TypeError("settings_service is required for Sonos select commands")

        requested_household_id = command.household
        if command.uids is None:
            _emit_status(status_fn, "Discovering Sonos speakers...")
            available_households = group_sonos_speakers_by_household(sonos_service.list_network_speakers())
            if not available_households:
                raise RuntimeError("No visible Sonos speakers found.")
            selected_household = _select_available_household(
                available_households,
                requested_household_id=command.household,
                household_prompt_fn=household_prompt_fn,
            )
            if selected_household is None:
                return
            requested_household_id = selected_household.household_id
            available_speakers = selected_household.speakers
            if speaker_prompt_fn is None:
                raise RuntimeError("Interactive Sonos speaker selection is not available in this context.")
            prompt_result = speaker_prompt_fn(available_speakers)
            if prompt_result is None:
                return
            selected_uids = list(prompt_result)
            if not selected_uids:
                raise RuntimeError("At least one Sonos speaker must be selected.")
            if len(selected_uids) == 1:
                coordinator_uid = selected_uids[0]
            else:
                if coordinator_prompt_fn is None:
                    raise RuntimeError("Interactive Sonos coordinator selection is not available in this context.")
                speakers_by_uid = {speaker.uid: speaker for speaker in available_speakers}
                selected_speakers = [speakers_by_uid[uid] for uid in selected_uids if uid in speakers_by_uid]
                coordinator_uid = coordinator_prompt_fn(selected_speakers)
                if coordinator_uid is None:
                    return
        else:
            selected_uids = list(command.uids)
            coordinator_uid = command.coordinator

        try:
            _emit_status(status_fn, "Validating Sonos selection...")
            result = SaveSonosSelection(
                selected_group_repository=SettingsSelectedSonosGroupRepository(settings_service),
                sonos_service=sonos_service,
            ).execute(
                selected_uids,
                coordinator_uid=coordinator_uid,
                requested_household_id=requested_household_id,
            )
        except ValueError as err:
            raise RuntimeError(str(err)) from err
        stdout_fn(render_sonos_selection_saved_output(result))
        return

    if isinstance(command, SonosShowCommand):
        if settings_service is None:
            raise TypeError("settings_service is required for Sonos show commands")

        status = GetSonosSelectionStatus(
            selected_group_repository=SettingsSelectedSonosGroupRepository(settings_service),
            sonos_service=sonos_service,
        ).execute()
        stdout_fn(render_sonos_selection_status_output(status))
        return

    raise TypeError("Unsupported Sonos command")


def _emit_status(status_fn: Optional[Callable[[str], None]], message: str) -> None:
    if status_fn is not None:
        status_fn(message)


def _select_available_household(
    households: list[GroupedSonosHousehold],
    requested_household_id: Optional[str],
    household_prompt_fn: Optional[Callable[[list[GroupedSonosHousehold]], Optional[str]]],
) -> Optional[GroupedSonosHousehold]:
    if requested_household_id is not None:
        return _get_available_household(households, requested_household_id)

    if len(households) == 1:
        return households[0]

    if household_prompt_fn is None:
        raise RuntimeError("Interactive Sonos household selection is not available in this context.")

    selected_household_id = household_prompt_fn(households)
    if selected_household_id is None:
        return None
    return _get_available_household(households, selected_household_id)


def _get_available_household(
    households: list[GroupedSonosHousehold],
    household_id: str,
) -> GroupedSonosHousehold:
    for household in households:
        if household.household_id == household_id:
            return household
    raise RuntimeError(f"No visible Sonos speakers found for household `{household_id}`.")


def execute_server_command(
    verbose: bool,
    command: object,
    services: AdminServices,
    build_api_app: Callable[[str, AdminServices], AppController],
    build_ui_app: Callable[[str, AdminServices], AppController],
    source_command: str,
) -> None:
    runtime_config = services.settings.resolve_admin_runtime(verbose=verbose)

    if isinstance(command, ApiCommand):
        uvicorn = _load_uvicorn("api", "api", source_command)
        api = _build_server_app(
            build_app=build_api_app,
            library_path=runtime_config.library_path,
            services=services,
            command_name="api",
            extra_name="api",
            source_command=source_command,
        )
        uvicorn.run(api.app, host="0.0.0.0", port=runtime_config.api_port)
        return

    if isinstance(command, UiCommand):
        uvicorn = _load_uvicorn("ui", "ui", source_command)
        ui = _build_server_app(
            build_app=build_ui_app,
            library_path=runtime_config.library_path,
            services=services,
            command_name="ui",
            extra_name="ui",
            source_command=source_command,
        )
        uvicorn.run(ui.app, host="0.0.0.0", port=runtime_config.ui_port)
        return

    raise TypeError("Unsupported server command")
