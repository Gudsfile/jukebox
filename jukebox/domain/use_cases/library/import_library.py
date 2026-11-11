from jukebox.domain.entities import Library, LibraryImportSummary
from jukebox.domain.repositories import LibraryRepository


class PreviewLibraryImport:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, library: Library) -> LibraryImportSummary:
        current = self.repository.list_discs()
        imported = library.discs
        return LibraryImportSummary(
            disc_count=len(imported),
            added=sorted(imported.keys() - current.keys()),
            changed=sorted(
                tag_id for tag_id in imported.keys() & current.keys() if imported[tag_id] != current[tag_id]
            ),
            removed=sorted(current.keys() - imported.keys()),
        )


class ImportLibrary:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, library: Library) -> None:
        self.repository.replace_library(library)
