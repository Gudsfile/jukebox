from pydantic import BaseModel


class LibraryImportSummary(BaseModel):
    """Differences between the current library and an imported one that replaces it."""

    disc_count: int
    added: list[str]
    changed: list[str]
    removed: list[str]
