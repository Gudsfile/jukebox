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

        if not (STATIC_DIR / "index.html").is_file():
            LOGGER.warning(
                "Admin UI bundle not found in %s: `/` will return 404. "
                "Build it with `npm run build` in admin-ui/ and copy admin-ui/dist/ there.",
                STATIC_DIR,
            )

        self.app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="admin-ui")
