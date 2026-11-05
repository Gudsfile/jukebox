import logging
import pathlib

from jukebox.shared.errors import MissingOptionalDependencyError

try:
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError as e:
    raise MissingOptionalDependencyError("The `ui_controller` module", "ui", "jukebox-admin ui") from e


from jukebox.adapters.inbound.admin.api_controller import APIController

LOGGER = logging.getLogger("jukebox")


STATIC_DIR = pathlib.Path(__file__).parent / "static"


class UIController(APIController):
    def register_routes(self):
        super().register_routes()

        self.app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="admin-ui")
