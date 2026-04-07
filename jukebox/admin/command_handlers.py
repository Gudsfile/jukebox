import sys
from importlib import import_module
from typing import Callable, Optional, Protocol

from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.shared.dependency_messages import optional_extra_dependency_message
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import GetSonosSelectionStatus, PlanSonosSelection, SaveSonosSelection
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
    source_command: str,
    library: Optional[str] = None,
    stdout_fn: Callable[[str], None] = print,
    stderr_fn: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> None:
    if source_command == "discstore" and isinstance(
        command,
        (SettingsShowCommand, SettingsSetCommand, SettingsResetCommand),
    ):
        stderr_fn(build_discstore_settings_deprecation_warning(command, library=library))

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
    speaker_prompt_fn: Optional[Callable[[list[DiscoveredSonosSpeaker]], Optional[list[str]]]] = None,
    coordinator_prompt_fn: Optional[Callable[[list[DiscoveredSonosSpeaker]], Optional[str]]] = None,
    stdout_fn: Callable[[str], None] = print,
) -> None:
    if isinstance(command, SonosListCommand):
        stdout_fn(render_sonos_speakers_output(sonos_service.list_available_speakers()))
        return

    if isinstance(command, SonosSelectCommand):
        if settings_service is None:
            raise TypeError("settings_service is required for Sonos select commands")

        plan = PlanSonosSelection(sonos_service=sonos_service).execute(
            requested_uids=command.uids,
            coordinator_uid=command.coordinator,
        )
        if plan.status in {"invalid_request", "none_available"}:
            raise RuntimeError(str(plan.error_message))

        selected_uids = list(plan.selected_uids)
        coordinator_uid = plan.coordinator_uid
        if plan.status == "needs_choice":
            if speaker_prompt_fn is None:
                raise RuntimeError("Interactive Sonos speaker selection is not available in this context.")
            prompt_result = speaker_prompt_fn(plan.speakers)
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
                speakers_by_uid = {speaker.uid: speaker for speaker in plan.speakers}
                selected_speakers = [speakers_by_uid[uid] for uid in selected_uids if uid in speakers_by_uid]
                coordinator_uid = coordinator_prompt_fn(selected_speakers)
                if coordinator_uid is None:
                    return

            plan = PlanSonosSelection(sonos_service=sonos_service).execute(
                requested_uids=selected_uids,
                coordinator_uid=coordinator_uid,
            )
            if plan.status != "resolved" or plan.coordinator_uid is None:
                raise RuntimeError(str(plan.error_message or "No Sonos speaker selection was made."))
            selected_uids = list(plan.selected_uids)
            coordinator_uid = plan.coordinator_uid

        if not selected_uids or coordinator_uid is None:
            raise RuntimeError("No Sonos speaker selection was made.")

        try:
            result = SaveSonosSelection(
                selected_group_repository=SettingsSelectedSonosGroupRepository(settings_service),
                sonos_service=sonos_service,
            ).execute(selected_uids, coordinator_uid=coordinator_uid)
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
