from jukebox.shared.errors import MissingOptionalDependencyError

try:
    from fastapi import FastAPI

    from jukebox.adapters.inbound.admin.api.current_tag_router import build_current_tag_router
    from jukebox.adapters.inbound.admin.api.discs_router import build_discs_router
    from jukebox.adapters.inbound.admin.api.export_router import build_export_router
    from jukebox.adapters.inbound.admin.api.import_router import build_import_router
    from jukebox.adapters.inbound.admin.api.models import (
        CurrentTagDiscOutput,
        CurrentTagStatusOutput,
        DiscInput,
        DiscOutput,
        DiscPatchInput,
        SettingsPatchInput,
        SettingsResetInput,
        SonosSelectionInput,
    )
    from jukebox.adapters.inbound.admin.api.pn532_router import build_pn532_router
    from jukebox.adapters.inbound.admin.api.settings_router import build_settings_router
    from jukebox.adapters.inbound.admin.api.sonos_router import build_sonos_router
except ModuleNotFoundError as e:
    if e.name != "fastapi":
        raise
    raise MissingOptionalDependencyError("The `api_controller` module", "api", "jukebox-admin api") from e
from jukebox.domain.repositories import LibraryRepository
from jukebox.domain.use_cases import (
    AddDisc,
    EditDisc,
    GetCurrentTagStatus,
    GetDisc,
    ImportLibrary,
    ListDiscs,
    PreviewLibraryImport,
    RemoveDisc,
)
from jukebox.settings.service_protocols import SettingsService
from jukebox.sonos.service import SonosService

__all__ = [
    "APIController",
    "CurrentTagDiscOutput",
    "CurrentTagStatusOutput",
    "DiscInput",
    "DiscOutput",
    "DiscPatchInput",
    "SettingsPatchInput",
    "SettingsResetInput",
    "SonosSelectionInput",
]


class APIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_disc: GetDisc,
        get_current_tag_status: GetCurrentTagStatus,
        settings_service: SettingsService,
        sonos_service: SonosService,
        library_path: str,
        settings_path: str,
        preview_library_import: PreviewLibraryImport,
        import_library: ImportLibrary,
        library_repository: LibraryRepository,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_disc = get_disc
        self.get_current_tag_status = get_current_tag_status
        self.settings_service = settings_service
        self.sonos_service = sonos_service
        self.library_path = library_path
        self.settings_path = settings_path
        self.preview_library_import = preview_library_import
        self.import_library = import_library
        self.library_repository = library_repository
        self.app = FastAPI(
            title="Jukebox Admin API",
            description="API for managing Jukebox disc library and settings",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self.register_routes()

    def register_routes(self):
        self.app.include_router(
            build_discs_router(
                add_disc=self.add_disc,
                list_discs=self.list_discs,
                remove_disc=self.remove_disc,
                edit_disc=self.edit_disc,
                get_disc=self.get_disc,
            )
        )
        self.app.include_router(
            build_current_tag_router(
                get_current_tag_status=self.get_current_tag_status,
                add_disc=self.add_disc,
                edit_disc=self.edit_disc,
                get_disc=self.get_disc,
                remove_disc=self.remove_disc,
            )
        )
        self.app.include_router(build_settings_router(self.settings_service))
        self.app.include_router(
            build_sonos_router(settings_service=self.settings_service, sonos_service=self.sonos_service)
        )
        self.app.include_router(build_pn532_router(self.settings_service))
        self.app.include_router(build_export_router(self.library_path, self.settings_path))
        self.app.include_router(
            build_import_router(
                self.library_repository, self.preview_library_import, self.import_library, self.settings_service
            )
        )
